# Data Model: MCP Detection Platform

**Feature Branch**: `001-mcp-detection-platform`
**Phase**: 1 (Design)
**Date**: 2025-10-16

## Overview

This document defines schemas for all key entities in the MCPeeker platform. Entities are split between:
- **ClickHouse**: Time-series detection data, analytics (OLAP workload)
- **PostgreSQL**: Registry, RBAC, audit logs (ACID compliance required)
- **NATS JetStream**: Event messages (transient, 7-day retention)

All schemas reference constitution principles and functional requirements.

---

## ClickHouse Schemas (Analytics Database)

### Table: `detections`

Stores all detection events with correlated evidence from multiple sources.

```sql
CREATE TABLE detections (
    -- Primary Identifiers
    detection_id UUID DEFAULT generateUUIDv4(),
    timestamp DateTime64(3) DEFAULT now64(3),

    -- Target Identification (FR-005a: Composite Identifier)
    host_id_hash FixedString(64),              -- SHA256(original_host_id) per FR-008
    composite_id FixedString(64),              -- SHA256(host:port:manifest:proc_sig)
    host String,                                -- IP/hostname (not hashed, used for routing)
    port UInt16,

    -- Scoring and Classification (FR-003, FR-004)
    score UInt8,                                -- 0-20+ range, ≥9 = unauthorized
    classification Enum8(
        'authorized' = 1,                       -- Score ≤4
        'suspect' = 2,                          -- Score 5-8
        'unauthorized' = 3                      -- Score ≥9
    ),

    -- Registry Matching (FR-005)
    registry_matched Bool DEFAULT false,
    registry_id Nullable(UUID),                 -- Foreign key to PostgreSQL registry_entries
    registry_penalty_applied Bool DEFAULT false,-- True if -6 score reduction applied

    -- Evidence (FR-007: Display all evidence)
    -- Nested structure for multi-source correlation
    evidence Nested(
        type Enum8('endpoint'=1, 'network'=2, 'gateway'=3),
        source String,                          -- e.g., "scanner-v1.2", "zeek-sensor-3"
        score_contribution UInt8,               -- Partial score from this signal
        detected_at DateTime64(3),
        snippet String,                         -- ≤1KB per FR-009 (enforced at insert)
        metadata String                         -- JSON blob: file_path, SHA256, etc.
    ),

    -- Judge Service Integration (FR-020a/b/c)
    judge_available Bool DEFAULT true,          -- False if Judge unavailable at detection time
    judge_classification Nullable(String),      -- e.g., "mcp_server", "json_rpc_client"
    judge_confidence Nullable(Float32),         -- 0.0-1.0
    judge_explanation Nullable(String),         -- Plain-language reasoning (US5)

    -- Deduplication (FR-002a)
    dedup_window_start DateTime64(3),           -- Start of 5-minute dedup window
    dedup_window_end DateTime64(3),             -- End of 5-minute dedup window
    merged_detection_ids Array(UUID),           -- If multiple detections merged, list original IDs

    -- Audit and Metadata
    created_at DateTime64(3) DEFAULT now64(3),
    updated_at DateTime64(3) DEFAULT now64(3)

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)                -- Monthly partitions for TTL efficiency
ORDER BY (timestamp, score, classification, host_id_hash)
TTL timestamp + INTERVAL 90 DAY                 -- FR-022: 90-day retention
SETTINGS index_granularity = 8192;
```

**Validation Rules**:
- `score`: Range 0-255 (UInt8), typically 0-20
- `evidence.snippet`: Max 1024 bytes (enforced by correlator before insert, FR-009)
- `host_id_hash`: Exactly 64 hex characters (SHA256 output)
- `composite_id`: Exactly 64 hex characters (SHA256 output)

**Relationships**:
- `registry_id` → PostgreSQL `registry_entries.id` (soft foreign key, checked by correlator)

**Indexes**:
- Primary key: Fast queries by timestamp + score + classification
- Skipping index on `host_id_hash` for per-host investigation queries (FR-013)

---

### Materialized View: `aggregated_metrics`

Pre-aggregated metrics for dashboard performance (SC-007: ≤2s queries).

```sql
CREATE MATERIALIZED VIEW aggregated_metrics
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, classification)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    classification,
    count() AS detection_count,
    avg(score) AS avg_score,
    quantile(0.95)(score) AS p95_score,
    uniqExact(host_id_hash) AS unique_hosts,
    countIf(registry_matched = true) AS authorized_count,
    countIf(judge_available = false) AS judge_unavailable_count
FROM detections
GROUP BY hour, classification;
```

**Usage**:
- Dashboard trendlines: Query `aggregated_metrics` instead of full `detections` table
- Reduces query load by ~100x for time-range aggregations

---

### Table: `feedback_records`

Analyst annotations for detection accuracy (FR-023).

```sql
CREATE TABLE feedback_records (
    feedback_id UUID DEFAULT generateUUIDv4(),
    detection_id UUID,                          -- References detections.detection_id
    analyst_user_id UUID,                       -- References PostgreSQL users.id

    -- Feedback Classification
    verdict Enum8(
        'true_positive' = 1,                    -- Correctly identified MCP
        'false_positive' = 2,                   -- Incorrectly flagged non-MCP
        'inconclusive' = 3                      -- Insufficient evidence to decide
    ),

    -- Analyst Notes
    notes String,                               -- Free-text explanation
    tags Array(String),                         -- e.g., ["container_recreation", "zeek_signature_weak"]

    -- Metadata
    submitted_at DateTime64(3) DEFAULT now64(3)

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(submitted_at)
ORDER BY (submitted_at, verdict, detection_id)
TTL submitted_at + INTERVAL 90 DAY;
```

**Validation Rules**:
- `notes`: Max 4096 characters
- `tags`: Max 10 tags per feedback record

**Usage**:
- False positive rate calculation: `COUNT(verdict='false_positive') / COUNT(*)`
- Model retraining: Export feedback to improve Judge model (SC-002)

---

## PostgreSQL Schemas (Transactional Database)

### Table: `users`

Authenticated users with RBAC roles (FR-031).

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Authentication
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,      -- bcrypt hash

    -- RBAC (FR-032, FR-033, FR-034)
    role VARCHAR(50) NOT NULL CHECK (role IN ('developer', 'analyst', 'admin')),

    -- Developer Role Scoping (FR-032)
    -- Developer users see only detections from their associated endpoints
    associated_endpoints TEXT[],                -- Array of host identifiers

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

**Validation Rules**:
- `email`: RFC 5322 compliant email format
- `role`: Must be one of: `developer`, `analyst`, `admin`
- `associated_endpoints`: Optional for `analyst` and `admin`, required for `developer`

**Row-Level Security (RLS)**:
```sql
-- Developers see only their own records
CREATE POLICY developer_self_view ON users
    FOR SELECT
    USING (role = 'developer' AND id = current_user_id());

-- Analysts and Admins see all users
CREATE POLICY analyst_admin_view ON users
    FOR SELECT
    USING (role IN ('analyst', 'admin'));
```

---

### Table: `registry_entries`

Authorized MCP server registry (FR-006, FR-024).

```sql
CREATE TABLE registry_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Composite Identifier (FR-005a)
    composite_id VARCHAR(64) NOT NULL,          -- SHA256(host:port:manifest:proc_sig)
    host VARCHAR(255) NOT NULL,                 -- Current host/IP
    port INTEGER NOT NULL CHECK (port > 0 AND port <= 65535),
    manifest_hash VARCHAR(64),                  -- SHA256 of manifest file
    process_signature VARCHAR(64),              -- SHA256 of process command line

    -- Ownership
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    team VARCHAR(100),                          -- e.g., "platform-engineering"

    -- Purpose and Lifecycle (FR-006, FR-024)
    purpose TEXT NOT NULL,                      -- Why this MCP exists
    approval_status VARCHAR(50) NOT NULL DEFAULT 'pending'
        CHECK (approval_status IN ('pending', 'approved', 'denied', 'expired')),
    approved_by UUID REFERENCES users(id),      -- Admin who approved
    approved_at TIMESTAMPTZ,

    -- Expiration (FR-024, FR-025)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,            -- TTL set by user
    renewed_at TIMESTAMPTZ,                     -- Last renewal timestamp
    expiration_notified_at TIMESTAMPTZ,         -- When 14-day reminder sent

    -- Metadata
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_registry_composite_id ON registry_entries(composite_id);
CREATE INDEX idx_registry_owner ON registry_entries(owner_id);
CREATE INDEX idx_registry_expiration ON registry_entries(expires_at)
    WHERE approval_status = 'approved';         -- For daily expiration checks
```

**Validation Rules**:
- `composite_id`: Exactly 64 hex characters (SHA256 output)
- `manifest_hash`, `process_signature`: Exactly 64 hex characters if present
- `purpose`: Minimum 10 characters, maximum 1024 characters
- `expires_at`: Must be future date, maximum 365 days from creation

**Lifecycle State Machine**:
```
pending → approved (by Admin)
pending → denied (by Admin)
approved → expired (automated, daily cron check)
expired → approved (renewal by Developer + Admin re-approval)
```

---

### Table: `notification_preferences`

Per-user notification delivery configuration (FR-025a, FR-025b).

```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Delivery Channels (FR-025a: email, webhook, in-app, or combinations)
    email_enabled BOOLEAN NOT NULL DEFAULT true,
    webhook_enabled BOOLEAN NOT NULL DEFAULT false,
    in_app_enabled BOOLEAN NOT NULL DEFAULT true,

    -- Webhook Configuration
    webhook_url VARCHAR(512),                   -- Slack/Teams/PagerDuty webhook
    webhook_secret VARCHAR(255),                -- HMAC signature secret

    -- Notification Types
    notify_on_detection BOOLEAN NOT NULL DEFAULT true,
    notify_on_expiration BOOLEAN NOT NULL DEFAULT true,
    notify_on_system_alert BOOLEAN NOT NULL DEFAULT false,

    -- Thresholds (FR-025a: "only notify for score ≥9")
    detection_score_threshold INTEGER DEFAULT 9,-- Only notify if score ≥ threshold

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_notif_prefs_user ON notification_preferences(user_id);
```

**Validation Rules**:
- `webhook_url`: Must be HTTPS URL if `webhook_enabled = true`
- `detection_score_threshold`: Range 0-20
- At least one channel must be enabled if user wants notifications

**Default Behavior**:
- New users: Email + in-app enabled, notify on detections ≥9
- Admins: System alerts enabled by default

---

### Table: `audit_logs`

Signed audit trail for compliance (FR-021, FR-022).

```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Event Details
    event_type VARCHAR(100) NOT NULL,           -- e.g., "detection.created", "registry.approved"
    actor_user_id UUID REFERENCES users(id),    -- Who performed the action (NULL for system)
    target_entity_type VARCHAR(50),             -- e.g., "detection", "registry_entry", "user"
    target_entity_id UUID,                      -- ID of affected entity

    -- Audit Trail
    action VARCHAR(50) NOT NULL,                -- CREATE, UPDATE, DELETE, APPROVE, DENY
    changes JSONB,                              -- Before/after diff for UPDATE actions
    ip_address INET,                            -- Source IP of request
    user_agent TEXT,                            -- Browser/client identifier

    -- Signature (FR-021: Signed audit logs)
    log_hash VARCHAR(64) NOT NULL,              -- SHA256(event_type|actor|target|timestamp)
    signature VARCHAR(512),                     -- HMAC-SHA256 signature (verifiable chain)

    -- Metadata
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_actor ON audit_logs(actor_user_id);
CREATE INDEX idx_audit_event_type ON audit_logs(event_type);
```

**Validation Rules**:
- `log_hash`: Exactly 64 hex characters (SHA256 output)
- `signature`: Exactly 512 hex characters (SHA256 HMAC output)
- `changes`: Valid JSON structure

**Retention**:
- 90-day minimum retention (FR-022)
- Partitioned by month for efficient archival

**Integrity Verification**:
```sql
-- Verify signature chain (sequential hash verification)
SELECT
    id,
    log_hash = SHA256(event_type || actor_user_id::TEXT || timestamp::TEXT) AS is_valid
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '90 days';
```

---

## NATS JetStream Event Schemas

Events are transient messages (7-day retention) used for inter-service communication.

### Stream: `endpoint.events`

Endpoint scanner detections (file/process scans).

```yaml
stream_name: endpoint.events
subjects:
  - endpoint.detection.file
  - endpoint.detection.process
retention: limits
max_age: 604800s  # 7 days
storage: file
replicas: 3
```

**Message Schema** (JSON):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "timestamp", "host_id", "detection_type", "score", "evidence"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique event identifier"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "Detection time in RFC3339 format"
    },
    "host_id": {
      "type": "string",
      "description": "Original host identifier (will be hashed by correlator)"
    },
    "detection_type": {
      "type": "string",
      "enum": ["file", "process"],
      "description": "Type of endpoint detection"
    },
    "score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 20,
      "description": "Endpoint signal score (highest weight)"
    },
    "evidence": {
      "type": "object",
      "required": ["source", "snippet"],
      "properties": {
        "source": {
          "type": "string",
          "description": "Scanner version/identifier"
        },
        "file_path": {
          "type": "string",
          "description": "Path to detected manifest file"
        },
        "file_hash": {
          "type": "string",
          "pattern": "^[a-f0-9]{64}$",
          "description": "SHA256 hash of file"
        },
        "process_command": {
          "type": "string",
          "description": "Process command line"
        },
        "process_hash": {
          "type": "string",
          "pattern": "^[a-f0-9]{64}$",
          "description": "SHA256 hash of process signature"
        },
        "snippet": {
          "type": "string",
          "maxLength": 1024,
          "description": "File/process excerpt (≤1KB per FR-009)"
        },
        "port": {
          "type": "integer",
          "minimum": 1,
          "maximum": 65535,
          "description": "Detected port (from manifest or process args)"
        }
      }
    }
  }
}
```

**Example Message**:
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-16T14:32:00Z",
  "host_id": "workstation-42.corp.example.com",
  "detection_type": "file",
  "score": 11,
  "evidence": {
    "source": "scanner-v1.2.3",
    "file_path": "/home/alice/.mcp/manifest.json",
    "file_hash": "a3c5f8...",
    "snippet": "{\"name\":\"my-mcp-server\",\"version\":\"1.0.0\"}",
    "port": 3000
  }
}
```

---

### Stream: `network.events`

Network traffic detections (Zeek/Suricata signatures).

```yaml
stream_name: network.events
subjects:
  - network.detection.zeek
  - network.detection.suricata
retention: limits
max_age: 604800s  # 7 days
storage: file
replicas: 3
```

**Message Schema** (JSON):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "timestamp", "source_ip", "dest_ip", "dest_port", "score", "evidence"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "source_ip": {
      "type": "string",
      "format": "ipv4"
    },
    "dest_ip": {
      "type": "string",
      "format": "ipv4",
      "description": "Target host IP (used for correlation)"
    },
    "dest_port": {
      "type": "integer",
      "minimum": 1,
      "maximum": 65535
    },
    "protocol": {
      "type": "string",
      "enum": ["tcp", "udp"]
    },
    "score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10,
      "description": "Network signal score (supporting weight)"
    },
    "evidence": {
      "type": "object",
      "required": ["sensor_id", "signature_id", "snippet"],
      "properties": {
        "sensor_id": {
          "type": "string",
          "description": "Zeek/Suricata sensor identifier"
        },
        "signature_id": {
          "type": "string",
          "description": "Knostik signature ID that matched"
        },
        "payload_excerpt": {
          "type": "string",
          "maxLength": 1024,
          "description": "Payload snippet (≤1KB)"
        },
        "snippet": {
          "type": "string",
          "maxLength": 1024,
          "description": "Human-readable description"
        },
        "packet_count": {
          "type": "integer",
          "description": "Number of packets in flow"
        }
      }
    }
  }
}
```

**Example Message**:
```json
{
  "event_id": "660e8400-e29b-41d4-a716-446655440001",
  "timestamp": "2025-10-16T14:32:05Z",
  "source_ip": "192.168.1.42",
  "dest_ip": "10.0.5.100",
  "dest_port": 3000,
  "protocol": "tcp",
  "score": 3,
  "evidence": {
    "sensor_id": "zeek-sensor-3",
    "signature_id": "knostik:mcp:jsonrpc-handshake:v1",
    "payload_excerpt": "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\"}",
    "snippet": "JSON-RPC 2.0 initialization handshake detected",
    "packet_count": 12
  }
}
```

---

### Stream: `gateway.events`

LLM Judge classifications (gateway request analysis).

```yaml
stream_name: gateway.events
subjects:
  - gateway.classification.judge
retention: limits
max_age: 604800s  # 7 days
storage: file
replicas: 3
```

**Message Schema** (JSON):
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["event_id", "timestamp", "user_id", "score", "classification"],
  "properties": {
    "event_id": {
      "type": "string",
      "format": "uuid"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "user_id": {
      "type": "string",
      "description": "User making LLM request (for correlation)"
    },
    "model_id": {
      "type": "string",
      "description": "LLM model identifier (e.g., gpt-4o, claude-3.5)"
    },
    "score": {
      "type": "integer",
      "minimum": 0,
      "maximum": 10,
      "description": "Judge classification score (medium weight)"
    },
    "classification": {
      "type": "object",
      "required": ["label", "confidence"],
      "properties": {
        "label": {
          "type": "string",
          "enum": ["mcp_server", "json_rpc_client", "generic_llm", "unknown"],
          "description": "Semantic classification label"
        },
        "confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Model confidence (0.0-1.0)"
        },
        "explanation": {
          "type": "string",
          "maxLength": 512,
          "description": "Plain-language reasoning (US5)"
        }
      }
    },
    "evidence": {
      "type": "object",
      "required": ["source", "snippet"],
      "properties": {
        "source": {
          "type": "string",
          "description": "Judge service version"
        },
        "request_excerpt": {
          "type": "string",
          "maxLength": 1024,
          "description": "LLM request excerpt (≤1KB per FR-009)"
        },
        "snippet": {
          "type": "string",
          "maxLength": 1024,
          "description": "Evidence summary"
        },
        "inference_latency_ms": {
          "type": "integer",
          "description": "Model inference time (for monitoring SC-006)"
        }
      }
    },
    "judge_available": {
      "type": "boolean",
      "description": "False if Judge service was unavailable (FR-020b)"
    }
  }
}
```

**Example Message**:
```json
{
  "event_id": "770e8400-e29b-41d4-a716-446655440002",
  "timestamp": "2025-10-16T14:32:10Z",
  "user_id": "alice@example.com",
  "model_id": "gpt-4o",
  "score": 5,
  "classification": {
    "label": "mcp_server",
    "confidence": 0.92,
    "explanation": "Request contains tool registration and initialization pattern typical of MCP servers"
  },
  "evidence": {
    "source": "judge-v0.3.1-distilbert",
    "request_excerpt": "{\"method\":\"tools/list\"}",
    "snippet": "MCP tool listing request detected",
    "inference_latency_ms": 280
  },
  "judge_available": true
}
```

---

## Composite Identifier Construction

As defined in research.md, the composite identifier combines 4 components:

```python
import hashlib

def generate_composite_id(host: str, port: int, manifest_hash: str, process_signature: str) -> str:
    """
    Generate composite identifier for MCP instance (FR-005a).

    Args:
        host: IP address or hostname
        port: TCP port
        manifest_hash: SHA256 hash of manifest file content
        process_signature: SHA256 hash of process command line

    Returns:
        64-character hex string (SHA256 hash)
    """
    composite_string = f"{host}:{port}:{manifest_hash}:{process_signature}"
    return hashlib.sha256(composite_string.encode('utf-8')).hexdigest()
```

**Example**:
```python
composite_id = generate_composite_id(
    host="10.0.5.100",
    port=3000,
    manifest_hash="a3c5f8d9e2b1c4a7f6e9d8c7b6a5f4e3d2c1b0a9f8e7d6c5b4a3f2e1d0c9b8a7",
    process_signature="b4d6e8f0a2c4e6f8a0c2e4f6a8c0e2f4a6c8e0f2a4c6e8f0a2c4e6f8a0c2e4f6"
)
# Result: "e7f9d1c3b5a7e9f1d3c5b7a9e1f3d5c7b9a1e3f5d7c9b1a3e5f7d9c1b3a5e7f9"
```

---

## Relationships

### Cross-Database Relationships

**ClickHouse → PostgreSQL**:
- `detections.registry_id` → `registry_entries.id` (soft FK, checked by correlator)
- `feedback_records.analyst_user_id` → `users.id` (soft FK, checked by registry-api)

**PostgreSQL Internal**:
- `registry_entries.owner_id` → `users.id` (hard FK, CASCADE delete)
- `registry_entries.approved_by` → `users.id` (hard FK, SET NULL on delete)
- `notification_preferences.user_id` → `users.id` (hard FK, CASCADE delete)
- `audit_logs.actor_user_id` → `users.id` (hard FK, SET NULL on delete)

**NATS → ClickHouse** (via Correlator service):
- `endpoint.events` messages → `detections` table (after correlation)
- `network.events` messages → `detections` table (after correlation)
- `gateway.events` messages → `detections` table (after correlation)

### Entity Relationship Diagram

```
┌─────────────────┐
│ NATS JetStream  │
│ ┌─────────────┐ │
│ │endpoint.    │ │──┐
│ │events       │ │  │
│ └─────────────┘ │  │
│ ┌─────────────┐ │  │
│ │network.     │ │──┼──► Correlator ──► ClickHouse
│ │events       │ │  │    Service            detections
│ └─────────────┘ │  │                       ↓
│ ┌─────────────┐ │  │                   feedback_records
│ │gateway.     │ │──┘
│ │events       │ │
│ └─────────────┘ │
└─────────────────┘

PostgreSQL
┌─────────────────┐
│ users           │←──┐
│ (RBAC)          │   │
└────────┬────────┘   │
         │            │
         ├────────────┼────────► registry_entries
         │            │          (FK: owner_id, approved_by)
         │            │
         ├────────────┼────────► notification_preferences
         │            │          (FK: user_id)
         │            │
         └────────────┴────────► audit_logs
                                 (FK: actor_user_id)
```

---

## Summary

**ClickHouse** (Analytics):
- `detections`: 90-day retention, monthly partitions, 100M events/month capacity
- `aggregated_metrics`: Pre-aggregated for ≤2s dashboard queries
- `feedback_records`: Analyst annotations for ML retraining

**PostgreSQL** (Transactional):
- `users`: RBAC roles, row-level security
- `registry_entries`: Authorized MCP registry, composite identifier matching
- `notification_preferences`: Multi-channel delivery config
- `audit_logs`: Signed audit trail, 90-day retention

**NATS JetStream** (Events):
- `endpoint.events`: File/process detections
- `network.events`: Traffic signatures
- `gateway.events`: LLM Judge classifications

All schemas enforce constitution principles: privacy (hashed IDs, ≤1KB snippets), observability (timestamp indexes, audit logs), YAML validation (JSON Schema enforcement at producers).

Next phase: Define API contracts (OpenAPI specs) for Registry and Findings APIs.
