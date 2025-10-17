# Research: MCP Detection Platform

**Feature Branch**: `001-mcp-detection-platform`
**Phase**: 0 (Research)
**Date**: 2025-10-16

## Overview

This document captures technology research and architectural decisions for the MCPeeker MCP Detection Platform. All decisions reference constitution principles (Privacy by Design, Multi-Layer Correlation, YAML Configuration, Observability) and are formatted as: Decision → Rationale → Alternatives Considered.

## 1. NATS JetStream Event-Driven Architecture

### Decision

Use NATS JetStream as the event bus for all inter-service communication with the following configuration:
- Stream per event type: `endpoint.events`, `network.events`, `gateway.events`
- At-least-once delivery semantics (not exactly-once)
- Consumer groups for scalability: multiple correlator instances subscribe to same stream
- Stream retention: 7 days (supports retrospective analysis and Judge service recovery per FR-020c)
- Message acknowledgment timeout: 30 seconds (allows for ClickHouse write retries)

### Rationale

**Constitution Alignment**:
- **Multi-Layer Correlation**: Separate streams per signal type enable independent scaling of endpoint, network, and gateway detection layers while maintaining correlation flexibility
- **Observability**: NATS JetStream provides built-in monitoring metrics (message rates, consumer lag, ack rates) exportable to Prometheus
- **Privacy**: Events remain in memory/disk temporarily (7-day retention), then auto-purge; no long-term sensitive data accumulation

**Technical Benefits**:
- **At-least-once delivery** is sufficient for detection use case: duplicate detections are handled by correlator's 5-minute deduplication window (FR-002a)
- **Performance**: NATS achieves 11M msg/sec throughput (far exceeds 100M events/month = 40 msg/sec sustained requirement per FR-027)
- **Fault tolerance**: Clustered JetStream provides high availability without external coordination (Zookeeper, etc.)
- **Simplicity**: Lightweight compared to Kafka; aligns with YAML Configuration principle (streams defined via YAML)

**Scale Validation**:
- 100M events/month = ~40 events/sec average, bursts to 1M/day = ~12 events/sec
- NATS handles this with <1ms latency per message, supporting 60s end-to-end pipeline goal (FR-011)

### Alternatives Considered

1. **Apache Kafka**
   - *Pros*: Industry standard, exactly-once semantics, massive ecosystem
   - *Cons*: Operational complexity (Zookeeper dependency, JVM tuning), overkill for 40 msg/sec sustained load, violates simplicity goal
   - *Rejection*: Infrastructure overhead not justified for scale requirements

2. **RabbitMQ**
   - *Pros*: Mature AMQP implementation, good routing flexibility
   - *Cons*: Lower throughput than NATS (~50k msg/sec vs 11M msg/sec), more complex clustering
   - *Rejection*: Performance ceiling too low for future growth; NATS simpler for this use case

3. **Redis Streams**
   - *Pros*: Simple, fast, already familiar to many teams
   - *Cons*: Not designed for durable event streaming, clustering more complex, no native Kubernetes operator
   - *Rejection*: Durability guarantees insufficient for 7-day retention and Judge recovery scenarios

### Implementation References

- NATS JetStream Configuration: https://docs.nats.io/nats-concepts/jetstream
- Event schema validation: JSON Schema enforcement at producer (scanner, signature engine, Judge)
- Consumer pattern: Push-based for correlator (low latency), pull-based for batch analytics (ClickHouse ETL)

---

## 2. ClickHouse Schema Design for Time-Series Detection Data

### Decision

Use ClickHouse as the primary analytics database with the following schema design:

**Table: `detections`** (MergeTree engine)
```sql
CREATE TABLE detections (
    detection_id UUID,
    timestamp DateTime64(3),
    host_id_hash String,           -- SHA256(host_id) per FR-008
    composite_id String,            -- host:port:manifest_hash:proc_sig
    score UInt8,
    classification Enum8('authorized'=1, 'suspect'=2, 'unauthorized'=3),
    registry_matched Bool,
    evidence Nested(
        type Enum8('endpoint'=1, 'network'=2, 'gateway'=3),
        source String,
        score_contribution UInt8,
        snippet String              -- ≤1KB per FR-009
    ),
    judge_available Bool,           -- FR-020b flag
    created_at DateTime64(3)
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)    -- Monthly partitions
ORDER BY (timestamp, score, host_id_hash)
TTL timestamp + INTERVAL 90 DAY;    -- Auto-delete after 90 days (audit log retention)
```

**Table: `aggregated_metrics`** (AggregatingMergeTree)
```sql
CREATE MATERIALIZED VIEW aggregated_metrics
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, classification)
AS SELECT
    toStartOfHour(timestamp) AS timestamp,
    classification,
    count() AS detection_count,
    avg(score) AS avg_score,
    uniqExact(host_id_hash) AS unique_hosts
FROM detections
GROUP BY timestamp, classification;
```

### Rationale

**Constitution Alignment**:
- **Privacy by Design**: `host_id_hash` enforces FR-008; `snippet` field limited to 1KB per FR-009; 90-day TTL auto-purges old data
- **Observability**: Materialized view enables real-time dashboard queries (≤2s per SC-007) without full table scans

**Performance**:
- **MergeTree engine**: Optimized for time-series inserts (100M events/month = 3.3M writes/day)
- **Partitioning by month**: Enables fast range queries (FR-013 time range filtering) and efficient TTL enforcement
- **Primary key**: `(timestamp, score, host_id_hash)` optimizes common queries: recent detections, high-risk filtering, per-host investigation
- **Nested columns**: Evidence array stored efficiently; avoids JOIN overhead for multi-source correlation display

**Scale Validation**:
- ClickHouse handles 100M+ rows with sub-second query latency for properly keyed queries
- Columnar storage compresses evidence snippets aggressively (~10x compression for JSON text)
- Materialized view pre-aggregates dashboard metrics, reducing query load by ~100x

### Alternatives Considered

1. **PostgreSQL with TimescaleDB**
   - *Pros*: Familiar SQL, strong ACID guarantees, easier to operate
   - *Cons*: Row-based storage inefficient for 100M events/month analytics; slower aggregation queries
   - *Rejection*: Query performance doesn't meet ≤2s dashboard requirement for large time ranges

2. **Elasticsearch**
   - *Pros*: Full-text search, good for log aggregation, built-in dashboards (Kibana)
   - *Cons*: Higher memory overhead, JSON document overhead vs columnar storage, weaker schema enforcement
   - *Rejection*: Operational complexity and cost higher than ClickHouse for structured analytics

3. **Apache Druid**
   - *Pros*: Designed for OLAP, fast aggregations
   - *Cons*: More complex ingestion pipeline (Kafka dependency), smaller ecosystem than ClickHouse
   - *Rejection*: ClickHouse simpler to operate and sufficient for requirements

### Implementation References

- Schema validation: JSON Schema enforcement before ClickHouse insert (correlator service)
- Migration strategy: Use ClickHouse schema migrations (golang-migrate/migrate)
- Monitoring: Export ClickHouse metrics to Prometheus (query latency, insert rate, partition size)

---

## 3. mTLS Certificate Management and Rotation

### Decision

Implement mutual TLS (mTLS) for all inter-service communication using cert-manager with the following design:

**Certificate Authority**:
- **Root CA**: Self-signed, 10-year validity, stored in Kubernetes Secret with strict RBAC
- **Intermediate CAs**: Separate CAs for each service tier (detection layer, API layer, storage layer)
- **Leaf certificates**: 90-day validity, auto-renewed at 60 days (30-day buffer per constitution NFR)

**Certificate Issuance**:
- cert-manager `Issuer` per namespace (staging, production)
- `Certificate` resources for each service with DNS SANs (`scanner.mcpeeker.svc.cluster.local`)
- Automatic renewal via cert-manager controller

**Rotation Strategy**:
- **Planned rotation**: cert-manager renews certificates 30 days before expiry
- **Emergency rotation**: Manual `Certificate` deletion triggers immediate reissue
- **Zero-downtime**: Services watch certificate files, reload on change without restart

### Rationale

**Constitution Alignment**:
- **Privacy by Design**: mTLS enforces FR-010 (mandatory inter-service encryption); prevents MITM attacks
- **Security NFR**: 90-day rotation satisfies constitution requirement; automated rotation reduces human error

**Operational Benefits**:
- **cert-manager**: Cloud-native standard for Kubernetes certificate lifecycle
- **Observability**: cert-manager exports Prometheus metrics for certificate expiry, renewal failures
- **Zero-downtime**: Services use file watchers (fsnotify in Go, watchdog in Python) to reload certificates without restarting connections

**Threat Model**:
- Compromised leaf certificate: Limited blast radius (90-day validity, single service scope)
- Intermediate CA compromise: Rotate intermediate CA, reissue all leaf certificates (emergency procedure)
- Root CA compromise: Full redeployment (nuclear option, prevented by strict Kubernetes RBAC)

### Alternatives Considered

1. **HashiCorp Vault PKI**
   - *Pros*: Dynamic secrets, short-lived certificates (1-hour validity possible)
   - *Cons*: Additional infrastructure dependency, Vault HA complexity, tighter coupling
   - *Rejection*: cert-manager sufficient for Kubernetes-native deployment; Vault overhead not justified

2. **Manual certificate management**
   - *Pros*: Full control, no external dependencies
   - *Cons*: Human error risk (missed renewals), no automation for 90-day rotation
   - *Rejection*: Violates operational simplicity and security best practices

3. **Service mesh (Istio/Linkerd) automatic mTLS**
   - *Pros*: Transparent mTLS, no application code changes
   - *Cons*: Service mesh overhead (sidecar resource consumption), additional operational complexity
   - *Rejection*: Overhead not justified for 5 core services; cert-manager simpler for this scale

### Implementation References

- cert-manager installation: Helm chart with CRD controller
- Certificate monitoring: Prometheus alerts for certificates expiring <14 days
- Rotation testing: Chaos engineering tests forcing certificate rotation under load

---

## 4. Composite Identifier Strategy for Distributed System Entity Tracking

### Decision

Identify MCP instances across IP changes, container recreations, and network reconfigurations using a **composite identifier**:

```
composite_id = SHA256(host + ":" + port + ":" + manifest_hash + ":" + process_signature)
```

**Components**:
1. **host**: IP address or hostname (ephemeral, used for routing but not sole identifier)
2. **port**: TCP port (stable unless reconfigured)
3. **manifest_hash**: SHA256 of MCP manifest file content (stable, uniquely identifies MCP server implementation)
4. **process_signature**: SHA256 of process command line + binary path (stable, identifies process instantiation)

**Matching Logic**:
- **Strong match**: All 4 components match → Same MCP instance
- **Manifest match**: manifest_hash + process_signature match, host/port differ → Same MCP, network reconfiguration
- **Weak match**: Only host + port match → Different MCP, shared endpoint (conflict detection)

### Rationale

**Constitution Alignment**:
- **Multi-Layer Correlation**: Composite ID enables accurate correlation across endpoint (manifest hash), network (host/port), and gateway (process signature) signals
- **Privacy by Design**: composite_id itself is hashed before storage (FR-008); original components not retained in ClickHouse

**Functional Requirements**:
- **FR-005a**: Handles IP address changes (container recreations, DHCP reassignment) by prioritizing manifest_hash over host
- **FR-002a**: Enables 5-minute deduplication window matching across scanner runs
- **Registry matching**: Authorized MCP registry entries use composite_id for lookups (FR-005)

**Edge Case Handling**:
- **Container recreation**: New host IP, same manifest_hash + process_signature → Recognized as same MCP
- **Port change**: User reconfigures MCP from port 3000 to 3001 → Treated as new instance until registry updated
- **Multiple MCPs per host**: Different manifest files → Different composite_ids, correctly identified as separate instances

### Alternatives Considered

1. **Host + Port only**
   - *Pros*: Simple, matches network traffic identifiers
   - *Cons*: Fails on IP changes (container recreations, DHCP), high false negatives
   - *Rejection*: Violates FR-005a requirement for container environment support

2. **Manifest hash only**
   - *Pros*: Stable across network changes
   - *Cons*: Cannot distinguish multiple instances of same MCP server on different hosts
   - *Rejection*: Insufficient granularity for multi-instance deployments

3. **UUID embedded in manifest**
   - *Pros*: Guaranteed uniqueness, developer-controlled
   - *Cons*: Requires manifest modification (not backward compatible with existing MCP servers), adoption barrier
   - *Rejection*: External dependency on MCP server implementers; not feasible for shadow IT detection

4. **Process PID**
   - *Pros*: OS-level unique identifier
   - *Cons*: Ephemeral (changes on every process restart), not stable across reboots
   - *Rejection*: Violates stability requirement for registry matching

### Implementation References

- Hashing: Use SHA256 for all components (FIPS 140-2 compliant)
- Matching algorithm: Implement in correlator service with configurable match strength thresholds
- Registry storage: Store composite_id in PostgreSQL `registry_entries` table with index for fast lookups

---

## 5. LLM Model Distillation for <400ms Inference Latency

### Decision

Use **knowledge distillation** to create a fast MCP classifier from a larger teacher model:

**Teacher Model**: GPT-4o or Claude 3.5 Sonnet (high accuracy, slow inference ~2-5s)
- Train on labeled dataset: 10,000+ LLM gateway requests (MCP vs non-MCP JSON-RPC)
- Generate soft labels (probability distributions) for student training

**Student Model**: DistilBERT-based sequence classifier (fast inference <400ms)
- Architecture: 6-layer transformer, 66M parameters (vs 340M for BERT-base)
- Input: LLM request/response JSON excerpt (≤512 tokens)
- Output: Binary classification (is_mcp: 0.0-1.0 confidence) + explanation embeddings

**Inference Stack**:
- Framework: ONNX Runtime (CPU inference, no GPU dependency)
- Serving: FastAPI with async workers, 4x worker processes per CPU core
- Caching: Redis for identical request fingerprints (reduces redundant inference)

**Latency Budget**:
- Model inference: ≤300ms (p95)
- API overhead: ≤50ms (serialization, network)
- Cache lookup: ≤10ms (Redis in-memory)
- **Total**: ≤360ms (p95), target ≤400ms per FR-020

### Rationale

**Constitution Alignment**:
- **Multi-Layer Correlation**: Judge service provides semantic classification (medium weight) complementing endpoint (high weight) and network (supporting) signals
- **Observability**: Student model generates explanation embeddings visualized in UI; Prometheus metrics track inference latency, cache hit rate, accuracy

**Performance**:
- DistilBERT achieves 97% of BERT-base accuracy with 60% fewer parameters and 2x faster inference
- ONNX Runtime optimized for CPU inference (quantization, graph optimization)
- Asynchronous serving prevents blocking on slow requests (99th percentile may exceed 400ms, but p95 meets SLA)

**Accuracy vs Speed Trade-off**:
- Teacher model (GPT-4o): 95% accuracy, 2-5s latency → Too slow for real-time (violates FR-020)
- Student model (DistilBERT): 92% accuracy, <300ms latency → Acceptable for medium-weight signal (not sole decision factor)
- Combined with endpoint + network: Multi-layer correlation compensates for 3% accuracy loss

### Alternatives Considered

1. **Direct GPT-4o API calls**
   - *Pros*: Highest accuracy (~95%), no model training required
   - *Cons*: 2-5s latency violates FR-020, API cost at scale ($10/1M tokens), external dependency
   - *Rejection*: Latency unacceptable for real-time pipeline

2. **Lightweight classifiers (XGBoost, Random Forest)**
   - *Pros*: <10ms inference, simple to deploy
   - *Cons*: Requires manual feature engineering (loses semantic understanding), lower accuracy (~85%)
   - *Rejection*: Accuracy gap too large; loses "semantic classification" value proposition (US5)

3. **Quantized BERT-base (INT8)**
   - *Pros*: Better accuracy than DistilBERT (~94% vs 92%)
   - *Cons*: Slower inference (500-600ms), larger memory footprint (340M params)
   - *Rejection*: Latency violates FR-020 even with quantization

4. **Streaming LLM (Groq, Together.ai)**
   - *Pros*: Fast token generation (100-200ms first token)
   - *Cons*: External API dependency, streaming overhead for binary classification, cost at scale
   - *Rejection*: External dependency violates self-hosted requirement; streaming unnecessary for simple classification

### Implementation References

- Training: Use Hugging Face Transformers for distillation (DistillationTrainer)
- Dataset: Curate 10k+ labeled LLM requests from synthetic MCP traffic + generic JSON-RPC corpora
- Evaluation: Track accuracy, precision, recall, F1 against holdout test set; A/B test against teacher model
- Monitoring: Log inference latency (p50, p95, p99), cache hit rate, per-request token count

---

## 6. Additional Research Topics

### 6.1 ClickHouse Replication for High Availability

**Decision**: Use ClickHouse ReplicatedMergeTree with ZooKeeper for HA
- 3-node ClickHouse cluster with 2x replication factor
- ZooKeeper quorum (3 nodes) for coordination
- Async replication (eventual consistency acceptable for analytics)

**Rationale**: 99.5% uptime SLA (FR-028) requires database redundancy; ReplicatedMergeTree standard pattern for ClickHouse HA

### 6.2 PostgreSQL Schema for Registry and RBAC

**Decision**: Use PostgreSQL 15+ with row-level security (RLS) for RBAC enforcement
- Tables: `users`, `registry_entries`, `notification_preferences`, `audit_logs`
- RLS policies: Developers see only their own detections, Analysts see all, Admins unrestricted
- Foreign key constraints: `registry_entries.owner_id → users.id`

**Rationale**: PostgreSQL ACID compliance required for registry integrity; RLS enforces FR-032/FR-033/FR-034 at database level (defense-in-depth)

### 6.3 YAML Configuration Schema Validation

**Decision**: Use JSON Schema Draft 2020-12 for YAML validation
- Schema files: `configs/schemas/scanner.schema.json`, `judge.schema.json`, etc.
- Validation: Pre-deployment validation via `ajv` (Node.js) or `jsonschema` (Python)
- CI enforcement: GitHub Actions validate YAML on every commit

**Rationale**: FR-016 mandates schema validation; JSON Schema provides machine-readable contracts for YAML configs (aligns with Constitution Principle IV)

---

## Summary

All research decisions prioritize constitution principles:
- **Privacy**: Hashed identifiers, minimal retention, mTLS everywhere
- **Multi-Layer Correlation**: Composite identifiers, NATS streams per signal type
- **YAML Configuration**: Schema-validated configs, declarative detection rules
- **Observability**: Prometheus metrics throughout, ClickHouse materialized views for dashboards
- **Performance**: ClickHouse for 100M events/month, DistilBERT for <400ms inference, NATS for low-latency messaging

Next phase: Define data models and API contracts based on these architectural decisions.
