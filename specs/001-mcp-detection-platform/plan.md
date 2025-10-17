# Implementation Plan: MCP Detection Platform

**Branch**: `001-mcp-detection-platform` | **Date**: 2025-10-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mcp-detection-platform/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

MCPeeker is an enterprise security platform for detecting and managing unauthorized Model Context Protocol (MCP) server instances across organizations. The system combines multi-layer detection (endpoint file/process scanning, network traffic monitoring, LLM gateway analysis) with correlation scoring to identify shadow IT MCP deployments while minimizing false positives. Core capabilities include automatic detection within 60 seconds, developer self-registration workflows, SOC investigation tools, and RBAC-based access control. The platform must handle 10,000 endpoints, 100M events/month, maintain 99.5% uptime, and ensure privacy-by-design principles (hashed host IDs, minimal data retention, mTLS everywhere).

## Technical Context

**Language/Version**:
- Go 1.23+ (endpoint scanner, correlator, high-performance services)
- Python 3.11+ (LLM Judge service, signature engine, ML components)
- TypeScript/React 18+ (UI portal)

**Primary Dependencies**:
- **Backend**: FastAPI (Registry API), NATS JetStream (event bus), ClickHouse (analytics/time-series), PostgreSQL (registry/RBAC), Prometheus (metrics), Grafana (dashboards)
- **Detection**: Zeek + Suricata (network monitoring), Knostik signature library (community MCP patterns)
- **Frontend**: React 18, Tailwind CSS, Zustand (state), SWR (data fetching)
- **Infrastructure**: Docker, Helm, mTLS (mutual TLS), JSON Schema validation

**Storage**:
- ClickHouse (findings, detections, time-series analytics) - columnar OLAP database
- PostgreSQL (registry entries, users, RBAC, audit logs) - relational ACID compliance
- NATS JetStream (event queue with persistence and at-least-once delivery)

**Testing**:
- Go: `go test` with table-driven tests, testify/assert
- Python: `pytest` with fixtures, mock, hypothesis for property-based testing
- Integration: Docker Compose with ephemeral NATS/ClickHouse/Postgres
- Contract: JSON Schema validation for event formats and API contracts
- Security: Gosec (Go), Bandit (Python), Trivy (container scanning)
- Performance: Vegeta (load testing), targeting 100M events/month sustained

**Target Platform**:
- Linux servers (primary deployment: Kubernetes via Helm)
- Supports macOS, Windows endpoints for scanner agent deployment
- Cloud-agnostic (AWS/GCP/Azure compatible via standard Kubernetes)

**Project Type**: Web application (backend services + frontend portal + distributed agents)

**Performance Goals**:
- Detection latency: ≤60s end-to-end (signal ingestion → UI display)
- LLM Judge: ≤400ms p95 per classification
- Dashboard queries: ≤2s for 90% of requests
- Event throughput: 40 events/sec sustained (100M/month)
- Concurrent endpoints: 10,000 without degradation

**Constraints**:
- 99.5% uptime SLA for detection pipeline and UI
- File content snippets: ≤1KB (privacy constraint)
- Audit log retention: minimum 90 days
- Zero-downtime upgrades required
- mTLS mandatory for all inter-service communication
- Host identifiers must be hashed before storage
- No raw LLM prompts or sensitive file contents retained

**Scale/Scope**:
- 10,000 concurrent endpoints generating events
- 100 million events per month (approximately 40/sec sustained, bursts to 1M/day)
- 3 user roles (Developer, Analyst, Admin) with RBAC
- 5 core services (Scanner, Signature Engine, Correlator, Judge, Registry API)
- 3 detection layers (endpoint, network, gateway)
- Multi-tenant capable (single deployment, future: org-level isolation)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Security-First Detection
**Status**: ✅ **PASS**
- Multi-layer correlation explicitly required (FR-002, FR-003) to minimize false positives
- Score threshold (≥9) prevents premature escalation from single signals (US4)
- Composite identifier (host + port + manifest hash + process signature) prevents misidentification across IP changes

### Principle II: Multi-Layer Correlation
**Status**: ✅ **PASS**
- FR-002: Correlates endpoint, network, and gateway signals
- FR-003: Weighted scoring (endpoint=highest, judge=medium, network=supporting)
- FR-004: Single-source detections remain "suspect" (score <9) until corroborated
- Scoring algorithm documented in clarifications (5-minute deduplication window)

### Principle III: Privacy by Design (NON-NEGOTIABLE)
**Status**: ✅ **PASS**
- FR-008: Host identifiers hashed before ClickHouse storage
- FR-009: File content snippets ≤1KB (no full file retention)
- FR-010: mTLS enforced for all inter-service communication
- FR-021/FR-022: Signed audit logs, 90-day retention minimum
- No raw LLM prompts stored (Judge service constraint)

### Principle IV: YAML Configuration
**Status**: ✅ **PASS**
- FR-015: Declarative YAML for rules, thresholds, component behavior
- FR-016: JSON Schema validation before deployment
- Referenced in assumptions: "Detection signatures maintained through configuration (not code changes)"
- Hydra mentioned for Judge experimental tuning (acceptable override per constitution)

### Principle V: Observability & Transparency
**Status**: ✅ **PASS**
- FR-007: Display all evidence (file paths, network indicators, semantic classifications)
- FR-014: Prometheus metrics for detection latency, false positive rates, Judge accuracy
- FR-025b: In-app notification center for transparency
- US5: Developer-facing explanatory text, plain-language scoring thresholds
- SC-015: ≥95% of key operations instrumented

### NFR Compliance Check

| NFR Category      | Constitution Requirement                          | Spec Compliance                                    | Status |
| ----------------- | ------------------------------------------------- | -------------------------------------------------- | ------ |
| Performance       | Detection latency ≤60s; Judge ≤400ms              | FR-011 (60s), FR-020 (400ms), SC-001, SC-006       | ✅ PASS |
| Scalability       | 10k endpoints; 100M events/month                  | FR-026, FR-027, SC-005, SC-008                     | ✅ PASS |
| Availability      | 99.5% uptime; autoscaling                         | FR-028, FR-029, SC-004                             | ✅ PASS |
| Security          | mTLS; CA rotation 90 days; no raw prompt storage  | FR-010 (mTLS), FR-009 (no raw data)                | ✅ PASS |
| Privacy           | Host ID hashing; snippets ≤1KB                    | FR-008 (hashing), FR-009 (1KB limit)               | ✅ PASS |
| Deployability     | Docker + Helm; YAML configs; zero-downtime        | FR-015 (YAML), FR-029 (zero-downtime), assumptions | ✅ PASS |
| Extensibility     | Plugin SDK; Judge model swappable                 | FR-030 (plugins), clarifications (configurable)    | ✅ PASS |
| Observability     | Prometheus metrics; Grafana dashboards            | FR-014 (Prometheus), SC-015 (≥95% instrumentation) | ✅ PASS |

### Testing Standards Compliance

| Standard                    | Constitution Requirement                                      | Spec Compliance                            | Status |
| --------------------------- | ------------------------------------------------------------- | ------------------------------------------ | ------ |
| Contract Testing (Phase 2+) | API schema adherence, error codes, backward compatibility    | FR-016 (JSON Schema validation)            | ✅ PASS |
| Integration Testing         | End-to-end flows, scoring accuracy, registry matching         | US4 acceptance scenarios, assumptions      | ✅ PASS |
| Security Testing            | Gosec/Bandit, Trivy scans, mTLS validation, audit log checks  | Technical context (tooling), FR-010/FR-021 | ✅ PASS |
| Performance Testing         | 10k endpoints, 1M events/day burst, 100 req/s Judge, ≤2s dash | SC-005, SC-006, SC-007, SC-008             | ✅ PASS |

**GATE RESULT**: ✅ **ALL CHECKS PASS** - Proceed to Phase 0 Research

No violations requiring justification in Complexity Tracking section.

## Project Structure

### Documentation (this feature)

```
specs/001-mcp-detection-platform/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output (technology decisions, best practices)
├── data-model.md        # Phase 1 output (entity schemas, relationships)
├── quickstart.md        # Phase 1 output (local development setup)
├── contracts/           # Phase 1 output (OpenAPI specs, event schemas)
│   ├── events.yaml      # NATS event schemas (endpoint, network, gateway)
│   ├── registry-api.yaml # Registry API OpenAPI 3.0 spec
│   └── findings-api.yaml # Findings API OpenAPI 3.0 spec
├── checklists/          # Quality validation (generated by /speckit.specify)
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks - NOT created by /speckit.plan)
```

### Source Code (repository root)

This is a **web application** with distributed backend services, frontend portal, and endpoint agents.

```
backend/
├── scanner/             # Go endpoint agent
│   ├── cmd/
│   │   └── scanner/     # Main entry point
│   ├── pkg/
│   │   ├── filescan/    # Manifest detection
│   │   ├── procscan/    # Process detection
│   │   └── reporter/    # NATS event publisher
│   └── tests/
│       ├── integration/
│       └── unit/
├── signature-engine/    # Python/Go pattern matching service
│   ├── src/
│   │   ├── parsers/     # Event parsing (endpoint, network, gateway)
│   │   ├── rules/       # Knostik rule engine
│   │   └── publisher/   # Enriched event output
│   └── tests/
├── correlator/          # Go correlation and scoring service
│   ├── cmd/
│   │   └── correlator/
│   ├── pkg/
│   │   ├── deduplication/ # 5-minute time-window deduplication
│   │   ├── scoring/     # Weighted algorithm (endpoint=high, judge=med, network=support)
│   │   ├── registry/    # Registry lookup client
│   │   └── storage/     # ClickHouse writer
│   └── tests/
├── judge/               # Python LLM Judge service
│   ├── src/
│   │   ├── models/      # Distilled MCP classifier
│   │   ├── inference/   # Online (<400ms) and batch modes
│   │   └── api/         # FastAPI endpoints
│   ├── configs/         # Hydra configuration
│   └── tests/
└── registry-api/        # Python FastAPI registry and RBAC service
    ├── src/
    │   ├── models/      # SQLAlchemy models (User, RegistryEntry, NotificationPrefs)
    │   ├── api/         # REST endpoints
    │   ├── auth/        # RBAC middleware (Developer, Analyst, Admin)
    │   └── notifications/ # Email, webhook, in-app delivery
    └── tests/

frontend/
├── src/
│   ├── components/
│   │   ├── dashboard/   # Dashboard widgets (score distribution, trendlines)
│   │   ├── detections/  # Detection feed, investigation panel
│   │   ├── registry/    # Registry management UI
│   │   └── common/      # Shared UI components
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Detections.tsx
│   │   ├── Registry.tsx
│   │   └── Settings.tsx
│   ├── services/        # API clients (SWR hooks)
│   └── stores/          # Zustand state management
└── tests/

infrastructure/
├── docker/              # Dockerfiles per service
├── helm/                # Kubernetes Helm charts
│   ├── mcpeeker/        # Umbrella chart
│   │   ├── templates/
│   │   └── values.yaml
│   └── dependencies/    # NATS, ClickHouse, Postgres subcharts
├── configs/             # YAML configuration templates
│   ├── global.yaml
│   ├── scanner.yaml
│   ├── judge.yaml
│   └── zeek_suricata.yaml
└── scripts/             # Deployment and setup scripts

tests/
├── contract/            # JSON Schema validation tests
├── integration/         # Docker Compose end-to-end tests
└── performance/         # Vegeta load test scenarios
```

**Structure Decision**: Web application architecture selected due to:
1. Frontend portal requirement (React SPA for dashboard, detections, registry management - US1, US2, US3, US5)
2. Multiple backend services with distinct responsibilities (scanner, correlator, judge, registry)
3. Distributed deployment model (endpoint agents on 10k+ hosts, centralized services in Kubernetes)
4. Separation of concerns: detection (Go for performance), ML inference (Python for ecosystem), API layer (FastAPI for rapid development), UI (React for modern SPA)

## Complexity Tracking

*No violations detected. All constitution checks passed. This section intentionally left blank.*
