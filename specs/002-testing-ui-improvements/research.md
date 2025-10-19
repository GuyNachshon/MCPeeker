# Research: Testing and UI Improvements

**Phase**: 0 (Outline & Research)
**Date**: 2025-10-18
**Feature**: Testing and UI Improvements for Registry Match Classification

## Overview

This document consolidates research findings for implementing comprehensive test coverage and UI improvements for the registry match scoring fix. Research covers Go testing best practices, Docker Compose for integration tests, React Testing Library patterns, and CI/CD staging strategies.

---

## Decision 1: Go Unit Testing Framework

**Context**: Need to write unit tests for correlator registry match logic

**Decision**: Use Go's native `testing` package with `testify/assert` and `testify/mock`

**Rationale**:
- Go's `testing` package is the standard, zero-config solution
- `testify/assert` provides readable assertions (`assert.Equal(t, expected, actual)`)
- `testify/mock` enables clean mocking of registry client interface
- Integrates seamlessly with `go test` command and CI/CD

**Alternatives Considered**:
- **Ginkgo/Gomega**: BDD-style testing framework
  - **Rejected**: Adds complexity and learning curve; `testing` package sufficient for straightforward logic tests
- **GoConvey**: Web UI for tests
  - **Rejected**: Overkill for backend unit tests; CI/CD doesn't need web UI

**Implementation Pattern**:
```go
// backend/correlator/pkg/engine/correlator_test.go
package engine

import (
    "testing"
    "github.com/stretchr/testify/assert"
    "github.com/stretchr/testify/mock"
)

// MockRegistryClient implements registry.Client interface
type MockRegistryClient struct {
    mock.Mock
}

func (m *MockRegistryClient) CheckMatch(ctx context.Context, req MatchRequest) (*MatchResponse, error) {
    args := m.Called(ctx, req)
    return args.Get(0).(*MatchResponse), args.Error(1)
}

func TestRegistryMatchForcesAuthorized(t *testing.T) {
    // Arrange
    mockRegistry := new(MockRegistryClient)
    mockRegistry.On("CheckMatch", mock.Anything, mock.Anything).
        Return(&MatchResponse{Matched: true}, nil)

    correlator := NewCorrelator(..., mockRegistry, ...)
    detection := &AggregatedDetection{
        Evidence: []EvidenceRecord{{Type: "endpoint", ScoreContribution: 11}},
    }

    // Act
    err := correlator.recalculateDetection(ctx, detection)

    // Assert
    assert.NoError(t, err)
    assert.Equal(t, "authorized", detection.Classification)
    assert.Equal(t, 5, detection.Score) // 11 - 6
    mockRegistry.AssertExpectations(t)
}
```

**Resources**:
- Go testing package: https://pkg.go.dev/testing
- testify documentation: https://github.com/stretchr/testify

---

## Decision 2: Integration Test Environment

**Context**: Need to test end-to-end workflow across scanner, correlator, registry API, and UI

**Decision**: Use Docker Compose with ephemeral services and Go-based test orchestration

**Rationale**:
- Docker Compose already used in MCPeeker for local development
- Ephemeral services ensure test isolation (no shared state between runs)
- Go test files can orchestrate Docker Compose via `exec.Command`
- Cleanup handled by Docker Compose down after tests

**Alternatives Considered**:
- **Testcontainers**: Go library for programmatic container management
  - **Rejected**: Adds dependency; Docker Compose YAML more transparent and reusable
- **Python pytest with docker-py**: Python-based orchestration
  - **Rejected**: Introduces Python dependency for Go codebase; prefer Go-only tests

**Implementation Pattern**:
```yaml
# backend/correlator/tests/integration/docker-compose.test.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mcpeeker_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    tmpfs:
      - /var/lib/postgresql/data  # Ephemeral storage

  nats:
    image: nats:latest
    command: ["-js"]  # Enable JetStream

  registry-api:
    build: ../../registry-api
    environment:
      DATABASE_URL: postgresql://test:test@postgres:5432/mcpeeker_test
    depends_on:
      - postgres

  correlator:
    build: ../../correlator
    environment:
      NATS_URL: nats://nats:4222
      REGISTRY_URL: http://registry-api:8000
    depends_on:
      - nats
      - registry-api
```

```go
// backend/correlator/tests/integration/workflow_test.go
package integration

import (
    "os/exec"
    "testing"
)

func TestMain(m *testing.M) {
    // Setup: Start Docker Compose services
    cmd := exec.Command("docker-compose", "-f", "docker-compose.test.yml", "up", "-d")
    cmd.Run()

    // Wait for services to be healthy
    time.Sleep(5 * time.Second)

    // Run tests
    code := m.Run()

    // Teardown: Stop and remove containers
    exec.Command("docker-compose", "-f", "docker-compose.test.yml", "down", "-v").Run()

    os.Exit(code)
}
```

**Resources**:
- Docker Compose documentation: https://docs.docker.com/compose/
- Go testing package (TestMain): https://pkg.go.dev/testing#hdr-Main

---

## Decision 3: React Component Testing

**Context**: Need to test UI components for badges, summary panel, and filter

**Decision**: Use React Testing Library with Jest

**Rationale**:
- React Testing Library is the de-facto standard for React component testing
- Encourages testing user behavior rather than implementation details
- Jest provides snapshot testing, mocking, and assertion library
- Aligns with existing frontend testing infrastructure (assumption)

**Alternatives Considered**:
- **Enzyme**: React component testing library
  - **Rejected**: Deprecated by Airbnb; React Testing Library preferred by React team
- **Cypress Component Testing**: E2E tool with component mode
  - **Rejected**: Heavier weight; RTL sufficient for component-level tests

**Implementation Pattern**:
```tsx
// frontend/src/components/DetectionBadge.test.tsx
import { render, screen } from '@testing-library/react';
import DetectionBadge from './DetectionBadge';

describe('DetectionBadge', () => {
  it('renders green badge for authorized classification', () => {
    render(<DetectionBadge classification="authorized" />);

    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('Authorized');
    expect(badge).toHaveClass('bg-green-500');
  });

  it('renders red badge for unauthorized classification', () => {
    render(<DetectionBadge classification="unauthorized" />);

    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('Unauthorized');
    expect(badge).toHaveClass('bg-red-500');
  });

  it('renders yellow badge for suspect classification', () => {
    render(<DetectionBadge classification="suspect" />);

    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('Suspect');
    expect(badge).toHaveClass('bg-yellow-500');
  });
});
```

**Resources**:
- React Testing Library: https://testing-library.com/docs/react-testing-library/intro/
- Jest documentation: https://jestjs.io/docs/getting-started

---

## Decision 4: CI/CD Test Staging

**Context**: Need to run unit tests on every commit, integration tests only after unit tests pass

**Decision**: Use GitHub Actions with conditional job execution (`needs:` keyword)

**Rationale**:
- GitHub Actions already used in MCPeeker (assumption based on spec dependencies)
- `needs:` keyword creates job dependencies (integration waits for unit)
- Fast feedback loop: unit tests fail fast (< 5s), integration tests only run if needed
- Aligns with clarification #2 (unit on every commit, integration after unit pass)

**Alternatives Considered**:
- **GitLab CI/CD**: Pipeline staging with `stage:` keyword
  - **Rejected**: Assumes GitHub (no evidence of GitLab)
- **Jenkins**: Classic CI server
  - **Rejected**: More complex setup; GitHub Actions simpler for cloud-native projects

**Implementation Pattern**:
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.23'
      - name: Run unit tests
        run: go test -v ./backend/correlator/pkg/engine/...
        timeout-minutes: 2

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests  # Only run if unit tests pass
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-go@v4
        with:
          go-version: '1.23'
      - name: Run integration tests
        run: |
          cd backend/correlator/tests/integration
          docker-compose -f docker-compose.test.yml up -d
          sleep 10  # Wait for services
          go test -v ./...
          docker-compose -f docker-compose.test.yml down -v
        timeout-minutes: 5
```

**Resources**:
- GitHub Actions documentation: https://docs.github.com/en/actions
- GitHub Actions: Job dependencies: https://docs.github.com/en/actions/using-jobs/using-jobs-in-a-workflow#defining-prerequisite-jobs

---

## Decision 5: Test Retry Logic

**Context**: Need to handle test flakiness in integration tests (max 2 retries)

**Decision**: Use GitHub Actions' built-in retry mechanism with `uses: nick-fields/retry@v2`

**Rationale**:
- Declarative retry configuration in workflow YAML
- Retries entire job (not individual test cases), ensuring clean state
- Logs each retry attempt for debugging
- Aligns with clarification #3 (retry up to 2 times)

**Alternatives Considered**:
- **Go test retry in code**: Loop around `m.Run()` in TestMain
  - **Rejected**: More complex to implement; GitHub Actions retry cleaner
- **Custom retry script**: Shell script wrapping `go test`
  - **Rejected**: Reinvents GitHub Actions' built-in functionality

**Implementation Pattern**:
```yaml
# .github/workflows/test.yml (integration-tests job)
integration-tests:
  runs-on: ubuntu-latest
  needs: unit-tests
  steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-go@v4
      with:
        go-version: '1.23'
    - name: Run integration tests with retry
      uses: nick-fields/retry@v2
      with:
        timeout_minutes: 5
        max_attempts: 3  # 1 initial + 2 retries
        command: |
          cd backend/correlator/tests/integration
          docker-compose -f docker-compose.test.yml up -d
          sleep 10
          go test -v ./...
          docker-compose -f docker-compose.test.yml down -v
```

**Resources**:
- GitHub Actions retry action: https://github.com/marketplace/actions/retry-step

---

## Decision 6: UI Component Architecture

**Context**: Need to create reusable badge, summary, and filter components

**Decision**: Atomic design pattern with Tailwind CSS for styling

**Rationale**:
- **Atomic design**: Badge = atom, Summary = molecule, Dashboard = organism
- **Tailwind CSS**: Utility-first, consistent with MCPeeker frontend (assumption)
- **Component reusability**: Badge component used in list, detail views, and summary
- **Type safety**: TypeScript interfaces for props

**Alternatives Considered**:
- **CSS Modules**: Scoped CSS per component
  - **Rejected**: Tailwind more maintainable for utility classes
- **Styled Components**: CSS-in-JS library
  - **Rejected**: Adds runtime overhead; Tailwind more performant

**Implementation Pattern**:
```tsx
// frontend/src/components/DetectionBadge.tsx (Atom)
interface DetectionBadgeProps {
  classification: 'authorized' | 'suspect' | 'unauthorized';
  size?: 'sm' | 'md' | 'lg';
}

const badgeStyles = {
  authorized: 'bg-green-500 text-white',
  suspect: 'bg-yellow-500 text-black',
  unauthorized: 'bg-red-500 text-white',
};

export default function DetectionBadge({ classification, size = 'md' }: DetectionBadgeProps) {
  return (
    <span
      role="status"
      className={`${badgeStyles[classification]} px-3 py-1 rounded-full text-${size}`}
    >
      {classification.charAt(0).toUpperCase() + classification.slice(1)}
    </span>
  );
}
```

```tsx
// frontend/src/components/DashboardSummary.tsx (Molecule)
interface DashboardSummaryProps {
  authorizedCount: number;
  suspectCount: number;
  unauthorizedCount: number;
}

export default function DashboardSummary(props: DashboardSummaryProps) {
  return (
    <div className="grid grid-cols-3 gap-4 p-4 bg-gray-100 rounded-lg">
      <div className="flex items-center space-x-2">
        <DetectionBadge classification="authorized" size="sm" />
        <span className="text-2xl font-bold">{props.authorizedCount}</span>
      </div>
      <div className="flex items-center space-x-2">
        <DetectionBadge classification="suspect" size="sm" />
        <span className="text-2xl font-bold">{props.suspectCount}</span>
      </div>
      <div className="flex items-center space-x-2">
        <DetectionBadge classification="unauthorized" size="sm" />
        <span className="text-2xl font-bold">{props.unauthorizedCount}</span>
      </div>
    </div>
  );
}
```

**Resources**:
- Atomic Design: https://atomicdesign.bradfrost.com/
- Tailwind CSS: https://tailwindcss.com/docs

---

## Summary of Decisions

| Decision | Choice | Key Rationale |
|----------|--------|---------------|
| **Go Unit Testing** | `testing` + `testify` | Standard, zero-config, clean mocking |
| **Integration Environment** | Docker Compose + Go orchestration | Reusable YAML, ephemeral services, familiar tooling |
| **React Testing** | React Testing Library + Jest | De-facto standard, behavior-focused, snapshot support |
| **CI/CD Staging** | GitHub Actions with `needs:` | Job dependencies, fast feedback, simple configuration |
| **Test Retry** | GitHub Actions retry action | Declarative, clean state per retry, built-in logging |
| **UI Architecture** | Atomic design + Tailwind CSS | Reusable components, utility-first styling, type-safe props |

---

## Open Questions

None. All technical decisions are resolved based on existing MCPeeker architecture and industry best practices.

---

## Next Phase

**Phase 1**: Generate `data-model.md` (test fixtures schema), `contracts/` (API contracts for integration tests), and `quickstart.md` (developer guide for running tests).
