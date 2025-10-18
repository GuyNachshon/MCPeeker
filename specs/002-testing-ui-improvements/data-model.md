# Data Model: Testing and UI Improvements

**Phase**: 1 (Design & Contracts)
**Date**: 2025-10-18
**Feature**: Testing and UI Improvements for Registry Match Classification

## Overview

This document defines test data structures, fixtures, and UI component state models. Since this is a testing feature, the data model focuses on test entities rather than production database schemas.

---

## Test Fixtures

### 1. Mock Detection Data

**Purpose**: Represents detection data used in unit and integration tests

**Structure**:
```go
// Test fixture for AggregatedDetection
type TestDetection struct {
    CompositeID      string
    HostIDHash       string
    Evidence         []TestEvidence
    Score            int
    Classification   string
    RegistryMatched  bool
    RegistryPenalty  int
}

type TestEvidence struct {
    Type              string  // "endpoint", "network", "gateway"
    ScoreContribution int
    Details           map[string]interface{}
}
```

**Example Fixtures**:
```go
// backend/correlator/pkg/engine/test_helpers.go
var (
    // Fixture 1: Detection with registry match (should be "authorized")
    DetectionWithRegistryMatch = &TestDetection{
        CompositeID: "host123:3000:abc123:sig456",
        HostIDHash:  "sha256hash",
        Evidence: []TestEvidence{
            {Type: "endpoint", ScoreContribution: 11},
        },
        RegistryMatched: true,
        RegistryPenalty: -6,
        ExpectedScore:          5,  // 11 - 6
        ExpectedClassification: "authorized",
    }

    // Fixture 2: High-score detection without registry match
    HighScoreUnauthorized = &TestDetection{
        CompositeID: "host456:4000:def789:sig789",
        HostIDHash:  "sha256hash2",
        Evidence: []TestEvidence{
            {Type: "endpoint", ScoreContribution: 13},
            {Type: "network", ScoreContribution: 3},
            {Type: "judge", ScoreContribution: 5},
        },
        RegistryMatched: false,
        ExpectedScore:          21,
        ExpectedClassification: "unauthorized",
    }

    // Fixture 3: Low-score detection (should be "authorized")
    LowScoreAuthorized = &TestDetection{
        CompositeID: "host789:5000:ghi012:sig012",
        HostIDHash:  "sha256hash3",
        Evidence: []TestEvidence{
            {Type: "endpoint", ScoreContribution: 3},
        },
        RegistryMatched: false,
        ExpectedScore:          3,
        ExpectedClassification: "authorized",
    }
)
```

**Validation Rules**:
- `CompositeID` must be non-empty string
- `Evidence` array must contain at least one element for valid test
- `Score` must be >= 0 (negative scores floored to 0)
- `Classification` must be one of: "authorized", "suspect", "unauthorized"

---

### 2. Mock Registry Responses

**Purpose**: Simulates registry API responses for unit tests

**Structure**:
```go
type MockRegistryResponse struct {
    Matched    bool
    EntryID    string  // Optional: UUID of matched entry
    Expired    bool    // For testing expired entries
    Error      error   // For testing error scenarios
}
```

**Example Fixtures**:
```go
var (
    // Registry match: approved MCP
    RegistryMatch = &MockRegistryResponse{
        Matched: true,
        EntryID: "550e8400-e29b-41d4-a716-446655440000",
        Expired: false,
    }

    // No registry match
    RegistryNoMatch = &MockRegistryResponse{
        Matched: false,
    }

    // Expired registry entry
    RegistryExpired = &MockRegistryResponse{
        Matched: false,
        Expired: true,
    }

    // Registry API error
    RegistryError = &MockRegistryResponse{
        Error: errors.New("registry API unavailable"),
    }
)
```

---

### 3. Integration Test Data

**Purpose**: Test data for end-to-end integration tests

**Structure** (SQL seed data):
```sql
-- backend/correlator/tests/integration/fixtures/seed.sql

-- Registry entry (approved MCP)
INSERT INTO registry_entries (id, composite_id, name, vendor, status, approved_at, created_at)
VALUES (
    '550e8400-e29b-41d4-a716-446655440000',
    'testhost:3000:manifesthash123:processig456',
    '@modelcontextprotocol/server-test',
    'test-vendor',
    'approved',
    NOW(),
    NOW()
);

-- Detection event (will be published to NATS in test)
-- Represented as JSON for NATS message
{
  "event_id": "evt123",
  "timestamp": "2025-10-18T10:00:00Z",
  "host_id": "testhost",
  "detection_type": "file",
  "score": 11,
  "evidence": {
    "path": "/test/path/manifest.json",
    "hash": "manifesthash123"
  }
}
```

**Validation Rules**:
- Registry entry `id` must be valid UUID
- `status` must be "approved" for registry match tests
- Detection event JSON must match NATS event schema (see contracts/)

---

## UI Component State Models

### 4. Dashboard Summary State

**Purpose**: State model for DashboardSummary React component

**TypeScript Interface**:
```tsx
// frontend/src/types/dashboard.ts
interface DashboardSummaryState {
  authorizedCount: number;
  suspectCount: number;
  unauthorizedCount: number;
  lastUpdated: Date;
  loading: boolean;
  error: string | null;
}
```

**Initial State**:
```tsx
const initialSummaryState: DashboardSummaryState = {
  authorizedCount: 0,
  suspectCount: 0,
  unauthorizedCount: 0,
  lastUpdated: new Date(),
  loading: true,
  error: null,
};
```

**State Transitions**:
1. **Loading** → `loading: true, error: null`
2. **Success** → `loading: false, counts updated, lastUpdated: new Date()`
3. **Error** → `loading: false, error: <message>`

**Validation Rules**:
- All count fields must be non-negative integers
- `lastUpdated` must be valid Date object
- `error` must be string or null (not undefined)

---

### 5. Detection Badge Props

**Purpose**: Props interface for DetectionBadge component

**TypeScript Interface**:
```tsx
// frontend/src/components/DetectionBadge.tsx
interface DetectionBadgeProps {
  classification: 'authorized' | 'suspect' | 'unauthorized';
  size?: 'sm' | 'md' | 'lg';
  showTooltip?: boolean;
  tooltipText?: string;
}
```

**Default Props**:
```tsx
const defaultProps: Partial<DetectionBadgeProps> = {
  size: 'md',
  showTooltip: false,
};
```

**Validation Rules**:
- `classification` must be one of the three literal types
- `size` if provided, must be 'sm', 'md', or 'lg'
- `tooltipText` only rendered if `showTooltip` is true

---

### 6. Filter State

**Purpose**: State model for detection list filtering

**TypeScript Interface**:
```tsx
// frontend/src/types/filter.ts
interface DetectionFilterState {
  hideAuthorized: boolean;
  searchQuery: string;
  dateRange: {
    start: Date | null;
    end: Date | null;
  };
}
```

**Initial State**:
```tsx
const initialFilterState: DetectionFilterState = {
  hideAuthorized: false,
  searchQuery: '',
  dateRange: {
    start: null,
    end: null,
  },
};
```

**State Transitions**:
1. **Toggle authorized filter** → `hideAuthorized: !hideAuthorized`
2. **Update search** → `searchQuery: <input value>`
3. **Set date range** → `dateRange.start/end: <selected dates>`

**Validation Rules**:
- `hideAuthorized` must be boolean
- `searchQuery` must be string (empty string for no filter)
- `dateRange.start` must be <= `dateRange.end` if both are set

---

## Test Data Relationships

### Unit Tests (In-Memory)

```
TestDetection
    ├─ Evidence (array of TestEvidence)
    └─ Expected outcomes (score, classification)

MockRegistryResponse
    ├─ Matched (boolean)
    └─ Error (optional)
```

**Relationship**: MockRegistryResponse determines if TestDetection gets registry penalty applied

### Integration Tests (Docker Compose)

```
PostgreSQL (registry_entries table)
    └─ Contains approved MCP entry

NATS JetStream
    └─ Receives detection event (JSON)

Correlator Service
    ├─ Consumes NATS event
    ├─ Queries PostgreSQL for registry match
    └─ Produces updated detection

UI (via API)
    └─ Displays detection with badge/summary
```

**Relationship**: Integration tests verify data flows correctly through the entire stack

---

## Fixture Loading Strategy

### Unit Tests

**Approach**: Hard-coded Go structs in `test_helpers.go`

**Example**:
```go
func GetTestDetection(scenario string) *TestDetection {
    switch scenario {
    case "registry_match":
        return DetectionWithRegistryMatch
    case "high_score":
        return HighScoreUnauthorized
    case "low_score":
        return LowScoreAuthorized
    default:
        panic("unknown test scenario")
    }
}
```

### Integration Tests

**Approach**: SQL seed files + JSON event templates

**Loading Sequence**:
1. Docker Compose starts PostgreSQL
2. Test orchestrator runs `seed.sql` via `psql` command
3. Test publishes JSON event to NATS
4. Services process event
5. Test queries API to verify outcome

**Example**:
```go
// backend/correlator/tests/integration/workflow_test.go
func seedDatabase(t *testing.T) {
    cmd := exec.Command("docker-compose", "exec", "-T", "postgres",
        "psql", "-U", "test", "-d", "mcpeeker_test", "-f", "/fixtures/seed.sql")
    err := cmd.Run()
    require.NoError(t, err, "failed to seed database")
}
```

---

## Summary

This feature's data model focuses on test data rather than production schemas:

1. **Unit Test Fixtures**: Go structs for detections, registry responses
2. **Integration Test Data**: SQL seeds + JSON event templates
3. **UI Component Models**: TypeScript interfaces for React state/props

All test data is anonymized (no PII) and uses deterministic values for reproducibility.

---

## Next Artifact

`contracts/` directory with:
- OpenAPI spec for Registry API endpoints (used in integration tests)
- NATS event schema (JSON Schema for detection events)
- UI component prop types (TypeScript type definitions)
