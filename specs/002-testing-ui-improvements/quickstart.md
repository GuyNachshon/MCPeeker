# Developer Quickstart: Testing and UI Improvements

**Feature**: `002-testing-ui-improvements`
**Last Updated**: 2025-10-18

This guide helps developers run unit tests, integration tests, and UI component tests for the registry match classification feature.

---

## Prerequisites

**System Requirements**:
- Go 1.23+ (for backend unit tests)
- Docker 24+ and Docker Compose 2+ (for integration tests)
- Node.js 18+ and npm 9+ (for frontend component tests)
- Git (for test isolation)

**Environment Setup**:
```bash
# Verify Go installation
go version  # Expected: go1.23 or higher

# Verify Docker installation
docker --version  # Expected: Docker version 24.0+
docker-compose --version  # Expected: v2.0+

# Verify Node.js installation
node --version  # Expected: v18.0+
npm --version   # Expected: 9.0+
```

**Clone and Navigate**:
```bash
cd /path/to/mcpeeker
git checkout 002-testing-ui-improvements  # Feature branch
```

---

## Running Unit Tests

Unit tests verify correlator registry match logic without external dependencies (in-memory mocking).

### Run All Correlator Unit Tests

```bash
cd backend/correlator
go test -v ./pkg/engine/...
```

**Expected Output**:
```
=== RUN   TestRegistryMatchForcesAuthorized
--- PASS: TestRegistryMatchForcesAuthorized (0.00s)
=== RUN   TestHighScoreWithRegistryMatch
--- PASS: TestHighScoreWithRegistryMatch (0.00s)
=== RUN   TestExpiredRegistryEntry
--- PASS: TestExpiredRegistryEntry (0.00s)
=== RUN   TestNoRegistryMatchUsesThresholds
--- PASS: TestNoRegistryMatchUsesThresholds (0.00s)
PASS
ok      github.com/mcpeeker/backend/correlator/pkg/engine    0.023s
```

**Success Criteria**: All tests pass in < 5 seconds (SC-002)

### Run Specific Test

```bash
cd backend/correlator
go test -v -run TestRegistryMatchForcesAuthorized ./pkg/engine/
```

### Run Tests with Coverage

```bash
cd backend/correlator
go test -v -coverprofile=coverage.out ./pkg/engine/...
go tool cover -html=coverage.out  # Open coverage report in browser
```

**Success Criteria**: 100% coverage for registry match logic (SC-001)

### Debugging Failed Tests

If a test fails:

1. **Check test output** for assertion failures:
   ```
   Error: Expected classification "authorized", got "unauthorized"
   ```

2. **Run with verbose logging**:
   ```bash
   go test -v -run <TestName> ./pkg/engine/
   ```

3. **Inspect test fixtures** in `backend/correlator/pkg/engine/test_helpers.go`

4. **Verify mock setup** in test file (ensure mock expectations match test scenario)

---

## Running Integration Tests

Integration tests validate end-to-end workflow across scanner, correlator, registry API, and UI using Docker Compose.

### Step 1: Start Test Environment

```bash
cd backend/correlator/tests/integration
docker-compose -f docker-compose.test.yml up -d
```

**Services Started**:
- PostgreSQL (registry database)
- NATS JetStream (event bus)
- Registry API (MCP registration endpoints)
- Correlator (scoring engine)

### Step 2: Wait for Services to be Ready

```bash
# Wait for PostgreSQL to be ready
docker-compose -f docker-compose.test.yml exec postgres pg_isready -U test

# Wait for NATS to be ready
docker-compose -f docker-compose.test.yml exec nats nats-server --help > /dev/null 2>&1
```

**Alternative**: Use `sleep 10` as a simple wait strategy:
```bash
sleep 10  # Wait for all services to start
```

### Step 3: Seed Test Data

```bash
cd backend/correlator/tests/integration
docker-compose -f docker-compose.test.yml exec -T postgres \
  psql -U test -d mcpeeker_test -f /fixtures/seed.sql
```

**What this does**: Inserts test registry entries (approved MCPs) into PostgreSQL

### Step 4: Run Integration Tests

```bash
cd backend/correlator/tests/integration
go test -v ./...
```

**Expected Output**:
```
=== RUN   TestDetectionWorkflow
=== RUN   TestDetectionWorkflow/DetectionToRegistration
=== RUN   TestDetectionWorkflow/ReDetectionAfterRegistration
=== RUN   TestDetectionWorkflow/UIDisplaysAuthorizedBadge
--- PASS: TestDetectionWorkflow (5.23s)
=== RUN   TestRegistryAPIUnavailable
--- PASS: TestRegistryAPIUnavailable (1.45s)
PASS
ok      github.com/mcpeeker/backend/correlator/tests/integration    6.702s
```

**Success Criteria**: All tests pass in < 30 seconds (SC-002)

### Step 5: Cleanup Test Environment

```bash
cd backend/correlator/tests/integration
docker-compose -f docker-compose.test.yml down -v
```

**Important**: Use `-v` flag to remove volumes (ensures clean state for next run)

### One-Command Integration Test Run

For convenience, run all steps at once:

```bash
cd backend/correlator/tests/integration
./run_integration_tests.sh  # Wrapper script (to be created)
```

**Script contents** (`run_integration_tests.sh`):
```bash
#!/usr/bin/env bash
set -e

echo "Starting test environment..."
docker-compose -f docker-compose.test.yml up -d

echo "Waiting for services..."
sleep 10

echo "Seeding test data..."
docker-compose -f docker-compose.test.yml exec -T postgres \
  psql -U test -d mcpeeker_test -f /fixtures/seed.sql

echo "Running integration tests..."
go test -v ./...

echo "Cleaning up..."
docker-compose -f docker-compose.test.yml down -v

echo "Integration tests complete!"
```

### Debugging Failed Integration Tests

If an integration test fails:

1. **Check service logs**:
   ```bash
   docker-compose -f docker-compose.test.yml logs correlator
   docker-compose -f docker-compose.test.yml logs registry-api
   docker-compose -f docker-compose.test.yml logs nats
   ```

2. **Verify database state**:
   ```bash
   docker-compose -f docker-compose.test.yml exec postgres \
     psql -U test -d mcpeeker_test -c "SELECT * FROM registry_entries;"
   ```

3. **Check NATS messages**:
   ```bash
   docker-compose -f docker-compose.test.yml exec nats \
     nats stream ls
   ```

4. **Re-run with verbose output**:
   ```bash
   go test -v -run <TestName> ./...
   ```

5. **Retry test** (handle flakiness):
   - Integration tests may occasionally fail due to timing issues
   - CI/CD pipeline retries up to 2 times automatically (FR-014)
   - For local failures, re-run after cleanup:
     ```bash
     docker-compose -f docker-compose.test.yml down -v
     ./run_integration_tests.sh
     ```

---

## Running UI Component Tests

UI component tests verify badge rendering, filter behavior, and dashboard summary using React Testing Library.

### Step 1: Install Frontend Dependencies

```bash
cd frontend
npm install
```

### Step 2: Run All Component Tests

```bash
cd frontend
npm test
```

**Expected Output**:
```
PASS  src/components/DetectionBadge.test.tsx
  DetectionBadge
    ✓ renders green badge for authorized classification (23 ms)
    ✓ renders red badge for unauthorized classification (8 ms)
    ✓ renders yellow badge for suspect classification (7 ms)

PASS  src/components/DashboardSummary.test.tsx
  DashboardSummary
    ✓ displays correct counts for each classification (15 ms)
    ✓ shows loading state when data is fetching (12 ms)
    ✓ displays error message when fetch fails (10 ms)

PASS  src/components/DetectionFilter.test.tsx
  DetectionFilter
    ✓ toggles hide authorized filter (18 ms)
    ✓ updates search query (14 ms)

Test Suites: 3 passed, 3 total
Tests:       8 passed, 8 total
Snapshots:   0 total
Time:        2.345 s
```

### Step 3: Run Tests in Watch Mode

```bash
cd frontend
npm test -- --watch
```

**Use case**: During development, tests re-run automatically when files change

### Step 4: Run Tests with Coverage

```bash
cd frontend
npm test -- --coverage
```

**Expected Coverage**:
- Statements: > 80%
- Branches: > 75%
- Functions: > 80%
- Lines: > 80%

### Debugging Failed Component Tests

If a component test fails:

1. **Check test output** for assertion details:
   ```
   Expected element to have class "bg-green-500", but found "bg-red-500"
   ```

2. **Use React Testing Library debug**:
   ```tsx
   import { render, screen } from '@testing-library/react';

   it('renders badge', () => {
     render(<DetectionBadge classification="authorized" />);
     screen.debug();  // Prints rendered HTML to console
   });
   ```

3. **Verify component props** match test expectations

4. **Check Tailwind CSS classes** are correctly applied

---

## CI/CD Pipeline

The CI/CD pipeline runs tests automatically on every pull request.

### GitHub Actions Workflow

**File**: `.github/workflows/test.yml`

**Stages**:

1. **Unit Tests** (runs on every commit):
   - Triggers: Pull request to `main`
   - Timeout: 2 minutes
   - Failure: Blocks merge, integration tests not run

2. **Integration Tests** (runs after unit tests pass):
   - Triggers: After unit tests succeed
   - Timeout: 5 minutes
   - Retry: Up to 2 retries on failure (handles flakiness)
   - Failure: Blocks merge

3. **Component Tests** (runs in parallel with integration):
   - Triggers: After unit tests succeed
   - Timeout: 3 minutes
   - Failure: Blocks merge

**View Pipeline Status**:
```bash
# From command line
gh pr checks  # Requires GitHub CLI

# Or visit GitHub PR page in browser
```

### Running Tests Locally Before Push

**Recommended workflow**:

```bash
# 1. Run unit tests (fast feedback)
cd backend/correlator
go test -v ./pkg/engine/...

# 2. Run component tests (fast)
cd ../../frontend
npm test

# 3. Run integration tests (slow, only if unit tests pass)
cd ../backend/correlator/tests/integration
./run_integration_tests.sh
```

**Time estimate**:
- Unit tests: < 5 seconds
- Component tests: < 10 seconds
- Integration tests: < 30 seconds
- **Total**: < 1 minute

---

## Test Data Fixtures

### Unit Test Fixtures

**Location**: `backend/correlator/pkg/engine/test_helpers.go`

**Available Fixtures**:

```go
// Import in test files
import "github.com/mcpeeker/backend/correlator/pkg/engine"

func TestExample(t *testing.T) {
    // Get pre-defined test detection
    detection := GetTestDetection("registry_match")
    // detection.RegistryMatched == true
    // detection.ExpectedClassification == "authorized"
}
```

**Fixture Scenarios**:
- `"registry_match"` - Detection with registry match (should be authorized)
- `"high_score"` - High score without registry match (unauthorized)
- `"low_score"` - Low score without registry match (authorized)
- `"expired_entry"` - Detection matching expired registry entry

### Integration Test Fixtures

**Location**: `backend/correlator/tests/integration/fixtures/`

**Files**:
- `seed.sql` - PostgreSQL registry entries
- `detection_events.json` - NATS event templates
- `expected_responses.json` - Expected API responses

**Usage in Tests**:
```go
func TestExample(t *testing.T) {
    // Load JSON fixture
    events := loadFixture("detection_events.json")

    // Publish to NATS
    publishEvent(events[0])

    // Verify outcome
    detection := fetchDetection(events[0].CompositeID)
    assert.Equal(t, "authorized", detection.Classification)
}
```

### UI Component Test Fixtures

**Location**: `frontend/src/test-utils/fixtures.ts`

**Example**:
```tsx
import { mockDetection, mockSummary } from '@/test-utils/fixtures';

it('renders summary', () => {
  const summary = mockSummary({
    authorizedCount: 10,
    suspectCount: 5,
    unauthorizedCount: 2,
  });

  render(<DashboardSummary {...summary} />);
  expect(screen.getByText('10')).toBeInTheDocument();
});
```

---

## Troubleshooting

### Common Issues

**Issue**: Unit tests fail with "cannot find package"
- **Solution**: Run `go mod tidy` in `backend/correlator/` directory

**Issue**: Integration tests timeout
- **Solution**: Increase wait time in test setup (edit `docker-compose.test.yml`)

**Issue**: Docker Compose services fail to start
- **Solution**: Check port conflicts (`docker ps`), stop conflicting services

**Issue**: Component tests fail with "Cannot find module"
- **Solution**: Run `npm install` in `frontend/` directory

**Issue**: Tests pass locally but fail in CI
- **Solution**:
  1. Check CI logs for specific error
  2. Verify CI environment matches local (Go version, Node version)
  3. Ensure test cleanup runs properly (check for leftover state)

### Test Flakiness

If integration tests fail intermittently (< 5% of runs, per SC-007):

1. **In CI/CD**: Tests automatically retry up to 2 times (FR-014)
2. **Locally**: Re-run after full cleanup:
   ```bash
   docker-compose -f docker-compose.test.yml down -v
   ./run_integration_tests.sh
   ```
3. **Persistent flakiness**: Increase wait times or add retry logic in test code

### Getting Help

- **Spec documentation**: `specs/002-testing-ui-improvements/spec.md`
- **Architecture decisions**: `specs/002-testing-ui-improvements/research.md`
- **Data models**: `specs/002-testing-ui-improvements/data-model.md`
- **Contracts**: `specs/002-testing-ui-improvements/contracts/`

---

## Next Steps

After running tests successfully:

1. **Review test coverage**: Ensure 100% coverage for registry match logic (SC-001)
2. **Check UI components**: Verify badge colors and filter behavior (FR-008, FR-009)
3. **Run full CI/CD pipeline**: Push to PR and verify all stages pass
4. **Implement feature**: Use `/speckit.tasks` to generate implementation tasks

**Command to generate implementation tasks**:
```bash
/speckit.tasks
```

This will create a `tasks.md` file with step-by-step implementation instructions based on this specification.
