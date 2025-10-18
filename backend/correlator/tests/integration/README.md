# Integration Tests - MCPeeker Correlator

This directory contains end-to-end integration tests for the correlator service that validate the complete detection workflow across all services.

## Architecture

### Test Components

```
┌─────────────────────────────────────────────────────────┐
│                  Integration Test Suite                 │
│  (workflow_test.go)                                     │
└────────┬────────────────────────────────────────────────┘
         │
         ├──► Docker Compose Environment
         │    (docker-compose.test.yml)
         │    │
         │    ├──► PostgreSQL (registry data)
         │    ├──► NATS JetStream (event bus)
         │    ├──► ClickHouse (detection storage)
         │    ├──► Registry API (MCP registration)
         │    └──► Correlator (scoring engine)
         │
         └──► Test Fixtures
              (fixtures/)
              │
              ├──► seed.sql (registry entries)
              └──► detection_events.json (NATS events)
```

## Running Tests

### Quick Start

```bash
# Automated script (recommended)
./run_integration_tests.sh
```

This script:
1. Starts Docker Compose services
2. Waits for services to be ready
3. Seeds test data
4. Runs integration tests
5. Cleans up environment

### Manual Execution

```bash
# 1. Start services
docker-compose -f docker-compose.test.yml up -d

# 2. Wait for services
sleep 15

# 3. Seed database
docker-compose -f docker-compose.test.yml exec -T postgres \
  psql -U test -d mcpeeker_test -f /fixtures/seed.sql

# 4. Run tests
go test -v ./...

# 5. Cleanup
docker-compose -f docker-compose.test.yml down -v
```

### Skip Integration Tests

Set environment variable to skip:

```bash
SKIP_INTEGRATION_TESTS=true go test ./...
```

## Test Scenarios

### T025: Initial Unauthorized Detection

**Purpose**: Verify unregistered MCP is classified as "unauthorized"

**Flow**:
1. Publish detection event to NATS
2. Correlator processes event
3. Verify classification = "unauthorized" with score 11

### T026: MCP Registration

**Purpose**: Verify MCP can be registered via API

**Flow**:
1. POST to `/api/v1/mcps` with MCP details
2. Verify registry entry created
3. Verify status = "approved"

### T027: Re-Detection After Registration

**Purpose**: Verify registered MCP is classified as "authorized"

**Flow**:
1. Detect same MCP after registration
2. Correlator checks registry, finds match
3. Verify classification = "authorized" with reduced score (5)

## Test Data

### Registry Entries (seed.sql)

```sql
-- Entry 1: Approved MCP for testing registry match
id: 550e8400-e29b-41d4-a716-446655440000
composite_id: testhost:3000:manifesthash123:processsig456
status: approved

-- Entry 2: Expired entry for testing expiration
id: 650e8400-e29b-41d4-a716-446655440001
composite_id: testhost:4000:expiredhash789:expiredsig012
status: expired

-- Entry 3: High-score MCP still forced authorized
id: 750e8400-e29b-41d4-a716-446655440002
composite_id: testhost:6000:highscorehash345:highscoresig678
status: approved
```

### Detection Events (detection_events.json)

```json
{
  "name": "initial_unauthorized_detection",
  "expected_classification": "unauthorized",
  "expected_score": 11
}
```

See `fixtures/detection_events.json` for complete event templates.

## Service Ports (Test Environment)

| Service | Host Port | Container Port | Purpose |
|---------|-----------|----------------|---------|
| PostgreSQL | 5433 | 5432 | Registry data |
| NATS | 4223 | 4222 | Event bus |
| ClickHouse | 8124 | 8123 | Detection storage |
| Registry API | 8001 | 8000 | MCP registration |

**Note**: Different ports from production to avoid conflicts.

## Debugging

### View Service Logs

```bash
# All services
docker-compose -f docker-compose.test.yml logs

# Specific service
docker-compose -f docker-compose.test.yml logs correlator
docker-compose -f docker-compose.test.yml logs registry-api
```

### Check Database State

```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.test.yml exec postgres \
  psql -U test -d mcpeeker_test

# Query registry entries
SELECT id, composite_id, status FROM registry_entries;
```

### Inspect NATS Messages

```bash
# Check NATS streams
docker-compose -f docker-compose.test.yml exec nats \
  nats stream ls

# View messages
docker-compose -f docker-compose.test.yml exec nats \
  nats stream view detections.scan
```

## Troubleshooting

### Tests Fail with "Service Not Ready"

**Symptom**: PostgreSQL or NATS connection errors

**Solution**: Increase wait time in `run_integration_tests.sh` or `TestMain`

```bash
# Increase from sleep 15 to sleep 30
sleep 30  # Wait longer for services
```

### Tests Flake Intermittently

**Symptom**: Tests pass sometimes, fail other times

**Current Status**: SC-007 requires < 5% flakiness rate

**Mitigation**: CI/CD pipeline automatically retries up to 3 times

**Debug**:
1. Run tests 20 times: `for i in {1..20}; do ./run_integration_tests.sh || echo "FAIL $i"; done`
2. Calculate flakiness: `failures / 20 < 0.05`

### Docker Compose Won't Start

**Symptom**: Services fail to start

**Check**:
```bash
# Verify Docker is running
docker ps

# Check for port conflicts
lsof -i :5433
lsof -i :4223
lsof -i :8124
lsof -i :8001

# Clean up old containers
docker-compose -f docker-compose.test.yml down -v
```

## Success Criteria

### Performance (SC-002)

Integration tests must complete in < 30 seconds:

```bash
# Time the test run
time ./run_integration_tests.sh

# Should output: real 0m25.000s (or less)
```

### Reliability (SC-007)

Flakiness rate must be < 5%:

```bash
# Run 20 times
for i in {1..20}; do
  ./run_integration_tests.sh > /dev/null 2>&1 && echo "PASS" || echo "FAIL"
done | sort | uniq -c

# Expected: ≤1 FAIL out of 20 (5%)
```

## CI/CD Integration

Integration tests run in GitHub Actions after unit tests pass:

```yaml
# .github/workflows/test.yml
integration-tests:
  needs: unit-tests
  steps:
    - uses: nick-fields/retry@v3
      with:
        max_attempts: 3  # Retry up to 2 times
        command: ./run_integration_tests.sh
```

See `.github/workflows/test.yml` for complete configuration.

## Related Documentation

- **Unit Tests**: `backend/correlator/pkg/engine/correlator_test.go`
- **Component Tests**: `frontend/src/components/*.test.tsx`
- **Test Fixtures**: `fixtures/seed.sql`, `fixtures/detection_events.json`
- **Quickstart Guide**: `specs/002-testing-ui-improvements/quickstart.md`
- **CI/CD Pipeline**: `.github/workflows/test.yml`
