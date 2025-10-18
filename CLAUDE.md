# MCPeeker Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-10-18

## Active Technologies
- Go 1.23+ (backend/correlator, backend/scanner, backend/registry-api)
- Python 3.11+ (backend/judge)
- TypeScript/React 18+ (frontend)
- Docker & Docker Compose (services orchestration)
- NATS JetStream (event bus)
- PostgreSQL 15 (registry data)
- ClickHouse (detection storage)

## Project Structure
```
backend/
├── correlator/           # Detection correlation engine
│   ├── pkg/engine/      # Core correlation logic
│   │   ├── correlator.go
│   │   ├── correlator_test.go  # Unit tests
│   │   └── test_helpers.go     # Test fixtures & mocks
│   └── tests/integration/      # Integration tests
│       ├── docker-compose.test.yml
│       ├── workflow_test.go
│       ├── run_integration_tests.sh
│       └── fixtures/
├── judge/                # LLM-based classification
├── registry-api/         # MCP registry service
└── scanner/             # Host scanning agent

frontend/
├── src/
│   ├── components/      # React components
│   │   ├── DetectionBadge.tsx
│   │   ├── DashboardSummary.tsx
│   │   └── DetectionFilter.tsx
│   └── test/           # Test setup
└── vitest.config.ts    # Test configuration

.github/workflows/
└── test.yml            # CI/CD pipeline
```

## Testing Best Practices

### Unit Tests (Go)

**Location**: `backend/correlator/pkg/engine/correlator_test.go`

**Framework**: Go `testing` package + `testify/assert` + `testify/mock`

**Running Tests**:
```bash
# Run all unit tests
cd backend/correlator
go test -v ./pkg/engine/...

# Run with coverage
go test -coverprofile=coverage.out ./pkg/engine/...
go tool cover -html=coverage.out

# Run specific test
go test -v -run TestRegistryMatchForcesAuthorized ./pkg/engine/
```

**Test Naming Convention**:
- Use descriptive names: `TestRegistryMatchForcesAuthorized`
- Table-driven tests for multiple cases: `TestNonMatchedDetectionUsesThresholds`
- Include requirement reference in comments: `// T012: Test for FR-001`

**Success Criteria**:
- 100% coverage for registry match logic (SC-001)
- All tests pass in < 5 seconds (SC-002)

### Integration Tests (Go + Docker Compose)

**Location**: `backend/correlator/tests/integration/`

**Framework**: Go `testing` + Docker Compose + NATS + PostgreSQL

**Running Tests**:
```bash
# Automated script (recommended)
cd backend/correlator/tests/integration
./run_integration_tests.sh

# Manual execution
docker-compose -f docker-compose.test.yml up -d
sleep 10
go test -v ./...
docker-compose -f docker-compose.test.yml down -v
```

**Success Criteria**:
- Full workflow completes in < 30 seconds (SC-002)
- Flakiness rate < 5% (SC-007)

### Component Tests (React)

**Location**: `frontend/src/components/*.test.tsx`

**Framework**: Vitest + React Testing Library + jsdom

**Running Tests**:
```bash
# Run all component tests
cd frontend
npm test

# Run in watch mode
npm test -- --watch

# Run with coverage
npm test -- --coverage
```

**Test Patterns**:
- Test user-visible behavior, not implementation
- Use `screen.getByRole()` for accessibility
- Test all three badge colors: green, yellow, red
- Test loading and error states for async components

### CI/CD Pipeline

**File**: `.github/workflows/test.yml`

**Execution Order**:
1. Unit tests (run first, 2-minute timeout)
2. Integration tests (after unit tests pass, 5-minute timeout, 3 retry attempts)
3. Component tests (parallel with integration, 3-minute timeout)

**Local Validation Before Push**:
```bash
# 1. Run unit tests (fast)
cd backend/correlator && go test -v ./pkg/engine/...

# 2. Run component tests (fast)
cd frontend && npm test

# 3. Run integration tests (slow, only if unit tests pass)
cd backend/correlator/tests/integration && ./run_integration_tests.sh
```

## Code Style

### Go
- Follow standard Go conventions (`go fmt`, `go vet`)
- Use testify for assertions: `assert.Equal(t, expected, actual)`
- Mock external dependencies (registry client, NATS, databases)
- Table-driven tests for multiple scenarios

### TypeScript/React
- Use TypeScript strict mode
- Follow Tailwind CSS utility-first approach
- Export interfaces for component props
- Test components with RTL patterns

## Commands

### Development
```bash
# Start all services
docker-compose up -d

# Run correlator locally
cd backend/correlator
go run cmd/correlator/main.go

# Run frontend dev server
cd frontend
npm run dev
```

### Testing
```bash
# Unit tests
go test -v ./pkg/engine/...

# Integration tests
./backend/correlator/tests/integration/run_integration_tests.sh

# Component tests
cd frontend && npm test
```

### CI/CD
```bash
# Simulate CI pipeline locally
# 1. Unit tests
cd backend/correlator && go test -timeout 2m ./pkg/engine/...

# 2. Integration tests (with retry)
cd tests/integration && ./run_integration_tests.sh

# 3. Component tests
cd frontend && npm test -- --run
```

## Recent Changes
- 002-testing-ui-improvements: Added comprehensive test infrastructure, UI components, CI/CD pipeline

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
