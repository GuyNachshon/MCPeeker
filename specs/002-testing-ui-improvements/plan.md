# Implementation Plan: Testing and UI Improvements for Registry Match Classification

**Branch**: `002-testing-ui-improvements` | **Date**: 2025-10-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-testing-ui-improvements/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature adds comprehensive test coverage for the recent registry match scoring fix and improves UI classification visibility for SOC analysts. Primary components include:

1. **Unit Tests** (P1): Test correlator registry match logic verifying forced "authorized" classification, including edge cases (high scores, expired entries, non-matched detections)
2. **Integration Tests** (P1): End-to-end workflow validation from scanner detection → registration → re-detection with UI verification, including registry API failure scenarios
3. **UI Improvements** (P2): Colored classification badges (green/yellow/red), dashboard summary counts, and "Hide authorized MCPs" filter
4. **Optional Configuration** (P3): Scoring weight adjustment documentation

**Technical Approach**: Leverage existing Go testing framework for unit tests, Docker Compose for integration tests, and React component updates for UI improvements. CI/CD pipeline will run unit tests on every PR commit and integration tests after unit tests pass.

## Technical Context

**Language/Version**:
- Go 1.23+ (correlator unit tests)
- Python 3.11+ (integration test orchestration)
- TypeScript/React 18+ (UI components)

**Primary Dependencies**:
- Go: `testing`, `testify/assert`, `testify/mock` (unit tests)
- Docker Compose (integration test environment)
- React Testing Library (UI component tests)
- NATS JetStream (event bus for integration tests)
- PostgreSQL (registry data for integration tests)

**Storage**:
- PostgreSQL (registry entries for integration tests)
- ClickHouse (detection data, used in integration tests)
- In-memory test fixtures for unit tests

**Testing**:
- `go test` (correlator unit tests)
- `pytest` (integration test orchestration if Python-based)
- Docker Compose with ephemeral services (NATS, PostgreSQL, ClickHouse)
- React Testing Library for UI component tests

**Target Platform**:
- Linux servers (CI/CD runners for tests)
- macOS/Linux (local development)
- Docker containers (integration test environment)

**Project Type**: Web application (backend services + frontend React UI)

**Performance Goals**:
- Unit test suite completes in < 5 seconds
- Integration test suite completes in < 30 seconds (SC-002)
- Test flakiness rate < 5% (SC-007)

**Constraints**:
- Unit tests must not require external services (in-memory mocking only)
- Integration tests must cleanup resources after execution
- CI/CD pipeline must stage tests (unit first, then integration)
- Test retry logic: max 2 retries for integration tests

**Scale/Scope**:
- 20-30 unit test cases for correlator (covering FR-001 to FR-004)
- 5-10 integration test scenarios (covering FR-005, FR-006)
- 3-5 UI component tests (badge rendering, filter toggle, summary panel)
- CI/CD configuration updates (2 pipeline stages)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Security-First Detection
**Status**: ✅ **PASS**
- Tests verify forced "authorized" classification for registry matches, preventing false positives (US1 acceptance scenarios)
- Integration tests include registry API failure scenario, ensuring graceful degradation (clarification #1)
- Test coverage ensures scoring logic correctness (SC-001: 100% coverage)

### Principle II: Multi-Layer Correlation
**Status**: ✅ **PASS**
- Integration tests validate multi-layer workflow: scanner → correlator → registry → UI (US2)
- Tests verify scoring combines endpoint + registry signals correctly (FR-001, FR-002)
- Edge case testing includes expired registry entries and API unavailability (FR-003, FR-005)

### Principle III: Privacy by Design
**Status**: ✅ **PASS**
- Test fixtures use anonymized data (no real host IDs or sensitive content)
- Integration tests verify host ID hashing behavior (existing requirement, validated by tests)
- No test data contains PII or sensitive information

### Principle IV: YAML Configuration
**Status**: ✅ **PASS**
- Test configuration uses YAML for Docker Compose services (integration tests)
- Scoring weights configuration (FR-011) validates YAML-based configuration
- No hardcoded test policies

### Principle V: Observability & Transparency
**Status**: ✅ **PASS**
- Tests verify correlator logs warning on registry API failure (FR-005, clarification #1)
- Test naming follows self-documenting convention (SC-006)
- UI tests verify badge visibility and explanation text (FR-010, US3)

### Non-Functional Requirements
**Status**: ✅ **PASS**
- **Performance**: SC-002 requires integration tests < 30s
- **Availability**: Test retry logic (FR-014) ensures CI/CD reliability
- **Deployability**: Tests validate zero-downtime behavior (registry match classification doesn't disrupt existing detections)
- **Observability**: Tests verify logging behavior on failures

### Development & Testing Standards
**Status**: ✅ **PASS**
- **Contract Testing**: Integration tests verify API contract adherence (POST /api/v1/mcps)
- **Integration Testing**: Multi-service tests required (FR-005, FR-006)
- **Security Testing**: Out of scope for this feature (focused on test infrastructure)
- **Performance Testing**: SC-002 sets performance baseline for integration tests

## Project Structure

### Documentation (this feature)

```
specs/002-testing-ui-improvements/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (already created)
├── checklists/
│   └── requirements.md  # Quality checklist (already created)
├── research.md          # Phase 0 output (to be created)
├── data-model.md        # Phase 1 output (to be created)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
backend/
├── correlator/
│   ├── pkg/
│   │   └── engine/
│   │       ├── correlator.go          # Production code (already exists with fix)
│   │       ├── correlator_test.go     # NEW: Unit tests (this feature)
│   │       └── test_helpers.go        # NEW: Test fixtures and mocks
│   └── tests/
│       └── integration/
│           ├── docker-compose.test.yml  # NEW: Test environment
│           ├── workflow_test.go         # NEW: E2E workflow tests
│           └── fixtures/                # NEW: Test data
│
├── registry-api/
│   └── src/
│       └── api/                       # Existing API endpoints (used in integration tests)
│
└── scanner/
    └── pkg/                           # Scanner (used in integration tests)

frontend/
└── src/
    ├── components/
    │   ├── DetectionBadge.tsx         # NEW: Badge component
    │   ├── DetectionBadge.test.tsx    # NEW: Badge tests
    │   ├── DashboardSummary.tsx       # NEW: Summary panel component
    │   ├── DashboardSummary.test.tsx  # NEW: Summary panel tests
    │   └── DetectionFilter.tsx        # NEW: Filter component
    │
    └── pages/
        └── Dashboard.tsx              # MODIFIED: Integrate new components

.github/
└── workflows/
    └── test.yml                       # MODIFIED: Add staged test execution
```

**Structure Decision**: This feature extends the existing MCPeeker web application structure. Backend tests are co-located with the correlator package they test (Go convention). Integration tests use a separate `tests/integration/` directory with Docker Compose orchestration. Frontend component tests follow React Testing Library conventions (co-located with components).

## Complexity Tracking

*No constitutional violations - this section remains empty.*

This feature strictly adheres to all constitutional principles:
- Security-first detection (comprehensive test coverage prevents regressions)
- Multi-layer correlation (tests validate correlation behavior)
- Privacy by design (test data is anonymized)
- YAML configuration (Docker Compose + test config files)
- Observability (tests verify logging and UI transparency)

No additional services, patterns, or architectural changes required beyond existing MCPeeker structure.
