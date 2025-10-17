-- MCPeeker ClickHouse Schema
-- Database initialization for detections, feedback, and analytics
-- Reference: specs/001-mcp-detection-platform/data-model.md

-- Create database (will be created automatically by Docker, but explicit for clarity)
CREATE DATABASE IF NOT EXISTS mcpeeker;

USE mcpeeker;

-- ========================================
-- Table: detections
-- ========================================
-- Stores all detection events with correlated evidence from multiple sources

CREATE TABLE IF NOT EXISTS detections (
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

-- Skipping index for per-host queries (FR-013: Filter by host)
ALTER TABLE detections ADD INDEX idx_host_id_hash host_id_hash TYPE bloom_filter GRANULARITY 4;

-- ========================================
-- Materialized View: aggregated_metrics
-- ========================================
-- Pre-aggregated metrics for dashboard performance (SC-007: ≤2s queries)

CREATE MATERIALIZED VIEW IF NOT EXISTS aggregated_metrics
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

-- ========================================
-- Table: feedback_records
-- ========================================
-- Analyst annotations for detection accuracy (FR-023)

CREATE TABLE IF NOT EXISTS feedback_records (
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
    notes String,                               -- Free-text explanation (max 4096 chars)
    tags Array(String),                         -- e.g., ["container_recreation", "zeek_signature_weak"]

    -- Metadata
    submitted_at DateTime64(3) DEFAULT now64(3)

) ENGINE = MergeTree()
PARTITION BY toYYYYMM(submitted_at)
ORDER BY (submitted_at, verdict, detection_id)
TTL submitted_at + INTERVAL 90 DAY;

-- Create indexes for common queries
ALTER TABLE feedback_records ADD INDEX idx_detection_id detection_id TYPE bloom_filter GRANULARITY 4;
ALTER TABLE feedback_records ADD INDEX idx_analyst analyst_user_id TYPE bloom_filter GRANULARITY 4;

-- ========================================
-- Grant privileges
-- ========================================
-- Assuming mcpeeker user was created in Docker environment setup

GRANT SELECT, INSERT, ALTER, CREATE ON mcpeeker.* TO mcpeeker;
