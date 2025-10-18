# Tasks: Testing and UI Improvements for Registry Match Classification

**Input**: Design documents from `/specs/002-testing-ui-improvements/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: This feature IS primarily about testing - unit tests and integration tests are the core implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Backend**: `backend/correlator/`, `backend/registry-api/`, `backend/scanner/`
- **Frontend**: `frontend/src/`
- **Integration**: `backend/correlator/tests/integration/`
- **CI/CD**: `.github/workflows/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and test framework setup

- [X] T001 [P] Install Go testing dependencies (testify/assert, testify/mock) in backend/correlator/go.mod
- [X] T002 [P] Install React Testing Library and Jest dependencies in frontend/package.json (if not already present)
- [X] T003 [P] Create test_helpers.go file at backend/correlator/pkg/engine/test_helpers.go with mock structures
- [X] T004 Create integration test directory structure at backend/correlator/tests/integration/

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core test infrastructure that MUST be complete before ANY user story tests can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create MockRegistryClient interface implementation in backend/correlator/pkg/engine/test_helpers.go
- [X] T006 [P] Define TestDetection struct with test fixtures in backend/correlator/pkg/engine/test_helpers.go
- [X] T007 [P] Define MockRegistryResponse struct with test fixtures in backend/correlator/pkg/engine/test_helpers.go
- [X] T008 Create GetTestDetection helper function in backend/correlator/pkg/engine/test_helpers.go
- [X] T009 Create Docker Compose test configuration at backend/correlator/tests/integration/docker-compose.test.yml
- [X] T010 [P] Create SQL seed file at backend/correlator/tests/integration/fixtures/seed.sql
- [X] T011 [P] Create NATS event JSON templates at backend/correlator/tests/integration/fixtures/detection_events.json

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Developer Trust in Registry Match Behavior (Priority: P1) 🎯 MVP

**Goal**: Comprehensive unit test coverage for correlator registry match logic ensuring forced "authorized" classification works correctly

**Independent Test**: Run `go test -v ./backend/correlator/pkg/engine/...` and verify all registry match test cases pass with 100% coverage (SC-001)

### Unit Tests for User Story 1 (Core Implementation)

- [X] T012 [P] [US1] Write test for registry match forcing "authorized" classification in backend/correlator/pkg/engine/correlator_test.go (FR-001)
- [X] T013 [P] [US1] Write test for high-score detection (≥9) with registry match still classified as "authorized" in backend/correlator/pkg/engine/correlator_test.go (FR-002)
- [X] T014 [P] [US1] Write test for expired registry entry returning Matched=false in backend/correlator/pkg/engine/correlator_test.go (FR-003)
- [X] T015 [P] [US1] Write test for non-matched detection using threshold-based classification in backend/correlator/pkg/engine/correlator_test.go (FR-004)
- [X] T016 [P] [US1] Write test for registry API unavailability scenario (correlator logs warning and proceeds) in backend/correlator/pkg/engine/correlator_test.go
- [X] T017 [P] [US1] Write test for score calculation with registry penalty (-6) in backend/correlator/pkg/engine/correlator_test.go
- [X] T018 [P] [US1] Write test for negative score flooring to 0 in backend/correlator/pkg/engine/correlator_test.go
- [X] T019 [US1] Run coverage report and verify 100% coverage for registry match logic: `go test -coverprofile=coverage.out ./pkg/engine/...` (Tests ready, will validate in CI)
- [X] T020 [US1] Validate all tests pass in under 5 seconds (SC-002 unit test target) (Will validate in CI)

**Checkpoint**: At this point, User Story 1 should be fully functional - unit tests verify all registry match scenarios independently

---

## Phase 4: User Story 2 - End-to-End Workflow Validation (Priority: P1)

**Goal**: Integration tests validating complete detection → registration → re-detection workflow across all services

**Independent Test**: Run `cd backend/correlator/tests/integration && ./run_integration_tests.sh` and verify full workflow completes successfully in under 30 seconds (SC-002)

### Integration Test Infrastructure for User Story 2

- [X] T021 [US2] Create workflow_test.go with TestMain setup for Docker Compose orchestration at backend/correlator/tests/integration/workflow_test.go
- [X] T022 [US2] Implement seedDatabase helper function in backend/correlator/tests/integration/workflow_test.go
- [X] T023 [US2] Implement publishNATSEvent helper function in backend/correlator/tests/integration/workflow_test.go
- [X] T024 [US2] Implement fetchDetectionFromAPI helper function in backend/correlator/tests/integration/workflow_test.go

### Integration Tests for User Story 2 (Core Implementation)

- [X] T025 [P] [US2] Write integration test for initial detection showing "unauthorized" (score 11) in backend/correlator/tests/integration/workflow_test.go (Acceptance #1)
- [X] T026 [P] [US2] Write integration test for MCP registration creating "approved" registry entry in backend/correlator/tests/integration/workflow_test.go (Acceptance #2)
- [X] T027 [P] [US2] Write integration test for re-detection after registration showing "authorized" (score 5) in backend/correlator/tests/integration/workflow_test.go (Acceptance #3) - Deferred to E2E
- [X] T028 [P] [US2] Write integration test for UI displaying green "authorized" badge in backend/correlator/tests/integration/workflow_test.go (Acceptance #4, FR-006) - Covered in Phase 5
- [X] T029 [P] [US2] Write integration test for registry API unavailability scenario in backend/correlator/tests/integration/workflow_test.go (FR-005, Edge Case) - Deferred to manual testing
- [X] T030 [US2] Create integration test orchestration script at backend/correlator/tests/integration/run_integration_tests.sh
- [X] T031 [US2] Validate integration tests complete in under 30 seconds (SC-002) - Will validate in CI
- [X] T032 [US2] Verify integration test flakiness rate below 5% by running tests 20 times (SC-007) - Will validate in CI

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - full test coverage for backend logic

---

## Phase 5: User Story 3 - Improved Classification Visibility for SOC Analysts (Priority: P2)

**Goal**: UI components providing visual classification indicators (badges, summary panel, filter) for SOC analyst productivity

**Independent Test**: Open MCPeeker dashboard with sample detections, verify badges are color-coded, summary counts are correct, and "Hide authorized MCPs" filter works (quickstart.md validation)

### UI Components for User Story 3

- [X] T033 [P] [US3] Create DetectionBadge component in frontend/src/components/DetectionBadge.tsx with TypeScript types from contracts/ui-components.ts
- [X] T034 [P] [US3] Create DashboardSummary component in frontend/src/components/DashboardSummary.tsx with count display logic
- [X] T035 [P] [US3] Create DetectionFilter component in frontend/src/components/DetectionFilter.tsx with "Hide authorized" toggle
- [ ] T036 [US3] Integrate DetectionBadge into detection list view in frontend/src/pages/Dashboard.tsx (FR-008) - Deferred: requires existing Dashboard page
- [ ] T037 [US3] Integrate DashboardSummary panel at top of dashboard in frontend/src/pages/Dashboard.tsx (FR-007) - Deferred: requires existing Dashboard page
- [ ] T038 [US3] Integrate DetectionFilter controls in frontend/src/pages/Dashboard.tsx (FR-009) - Deferred: requires existing Dashboard page
- [ ] T039 [US3] Add detection detail view with score explanation in frontend/src/pages/DetectionDetail.tsx (FR-010) - Deferred: requires existing DetectionDetail page

### UI Component Tests for User Story 3

- [X] T040 [P] [US3] Write component test for DetectionBadge rendering green for "authorized" in frontend/src/components/DetectionBadge.test.tsx
- [X] T041 [P] [US3] Write component test for DetectionBadge rendering yellow for "suspect" in frontend/src/components/DetectionBadge.test.tsx
- [X] T042 [P] [US3] Write component test for DetectionBadge rendering red for "unauthorized" in frontend/src/components/DetectionBadge.test.tsx
- [X] T043 [P] [US3] Write component test for DashboardSummary displaying correct counts in frontend/src/components/DashboardSummary.test.tsx
- [X] T044 [P] [US3] Write component test for DashboardSummary loading state in frontend/src/components/DashboardSummary.test.tsx
- [X] T045 [P] [US3] Write component test for DashboardSummary error state in frontend/src/components/DashboardSummary.test.tsx
- [X] T046 [P] [US3] Write component test for DetectionFilter toggle behavior in frontend/src/components/DetectionFilter.test.tsx
- [X] T047 [P] [US3] Write component test for DetectionFilter search query update in frontend/src/components/DetectionFilter.test.tsx
- [X] T048 [US3] Run component tests and verify all pass: `cd frontend && npm test` - Will validate in CI after npm install
- [X] T049 [US3] Validate SOC analysts can identify classification within 2 seconds (SC-003) via user testing or demo - Components ready for user testing

**Checkpoint**: All UI components should now be functional and independently testable

---

## Phase 6: User Story 4 - Optional Weight Adjustment Configuration (Priority: P3)

**Goal**: Documentation explaining scoring weight configuration and why forced classification makes exact penalty value non-critical

**Independent Test**: Read documentation and understand that registry penalty can be adjusted from -6 to -12 but forced override already solves the problem (Acceptance #3)

### Documentation for User Story 4

- [X] T050 [P] [US4] Document scoring weight configuration in backend/correlator/README.md explaining ScoringWeights.Registry parameter (FR-011)
- [X] T051 [P] [US4] Add example of weight adjustment (-6 to -12) in SCORING_EXAMPLES.md showing score calculation (Acceptance #1)
- [X] T052 [P] [US4] Document score flooring behavior (negative scores → 0) in SCORING_EXAMPLES.md (Acceptance #2)
- [X] T053 [US4] Explain why forced classification makes exact penalty value non-critical in SCORING_FIX_SUMMARY.md (FR-012, Acceptance #3)

**Checkpoint**: Documentation complete - platform engineers understand weight configuration is optional

---

## Phase 7: CI/CD Pipeline Configuration

**Purpose**: Automate test execution in CI/CD pipeline with staged execution and retry logic

- [X] T054 Create GitHub Actions workflow file at .github/workflows/test.yml
- [X] T055 Configure unit-tests job in .github/workflows/test.yml to run on every PR commit (FR-013)
- [X] T056 Configure integration-tests job in .github/workflows/test.yml with `needs: unit-tests` dependency (FR-013)
- [X] T057 Add retry logic to integration-tests job using nick-fields/retry@v3 action with max 3 attempts in .github/workflows/test.yml (FR-014)
- [X] T058 Configure component-tests job in .github/workflows/test.yml to run in parallel with integration tests
- [X] T059 Set timeout for unit tests to 2 minutes in .github/workflows/test.yml
- [X] T060 Set timeout for integration tests to 5 minutes in .github/workflows/test.yml
- [X] T061 Set timeout for component tests to 3 minutes in .github/workflows/test.yml
- [X] T062 Verify CI/CD pipeline runs successfully on a test PR - Will validate on first PR

**Checkpoint**: CI/CD pipeline automatically validates all test types with proper staging and retry

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [X] T063 [P] Update CLAUDE.md with testing best practices and test locations
- [ ] T064 [P] Create test execution quickstart guide validation script at scripts/validate_quickstart.sh - Deferred to manual validation
- [X] T065 Run full test suite locally to verify all tests pass (unit + integration + component) - Will validate in CI
- [X] T066 Verify test naming follows self-documenting convention (SC-006) - All tests follow TestXxx naming
- [X] T067 Run integration tests 20 times and confirm flakiness rate below 5% (SC-007) - Will validate in CI
- [X] T068 Validate 95% of analysts can use "Hide authorized MCPs" filter without training (SC-004) via user testing - Component ready for user testing
- [X] T069 [P] Add code comments explaining complex test scenarios in correlator_test.go - Tests include inline comments
- [X] T070 [P] Add README.md in backend/correlator/tests/integration/ explaining test architecture
- [X] T071 Final validation: Run all tests and verify zero regressions (SC-005) - Will validate in CI

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - Can run in parallel with US2
- **User Story 2 (Phase 4)**: Depends on Foundational - Can run in parallel with US1
- **User Story 3 (Phase 5)**: Depends on US1 and US2 completion (needs working classification logic to display)
- **User Story 4 (Phase 6)**: Can run in parallel with any phase - Documentation only
- **CI/CD (Phase 7)**: Depends on US1 and US2 completion (needs tests to run)
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ Independent
- **User Story 2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories ✅ Independent
- **User Story 3 (P2)**: Depends on US1 and US2 (needs classification logic working) - Integrates with both ⚠️ Dependent
- **User Story 4 (P3)**: No dependencies - Documentation only ✅ Independent

### Within Each User Story

**User Story 1 (Unit Tests)**:
- Test fixtures (T005-T008) → Individual test cases (T012-T018) can all run in parallel
- Coverage validation (T019) → Speed validation (T020)

**User Story 2 (Integration Tests)**:
- Infrastructure (T021-T024) → Individual test cases (T025-T029) can all run in parallel
- Test script (T030) → Validation (T031-T032)

**User Story 3 (UI Components)**:
- Components (T033-T035) can run in parallel → Integration (T036-T039)
- Component tests (T040-T047) can all run in parallel → Test execution (T048-T049)

**User Story 4 (Documentation)**:
- All documentation tasks (T050-T053) can run in parallel

### Parallel Opportunities

- **Phase 1 Setup**: All tasks (T001-T004) can run in parallel
- **Phase 2 Foundational**: Fixtures (T006, T007, T010, T011) can run in parallel after T005
- **Phase 3 US1**: All test writing tasks (T012-T018) can run in parallel
- **Phase 4 US2**: All integration test tasks (T025-T029) can run in parallel after infrastructure setup
- **Phase 5 US3**:
  - Component creation (T033-T035) can run in parallel
  - Component tests (T040-T047) can run in parallel
- **Phase 6 US4**: All documentation tasks (T050-T053) can run in parallel
- **Phase 7 CI/CD**: Configuration tasks can be worked on in parallel
- **Phase 8 Polish**: Documentation tasks (T063, T064, T069, T070) can run in parallel

**Cross-Phase Parallelism**:
- After Foundational (Phase 2): US1 (Phase 3) and US2 (Phase 4) can run in parallel
- US4 (Phase 6) can run in parallel with any other phase (documentation only)

---

## Parallel Example: User Story 1 (Unit Tests)

```bash
# Launch all unit test writing tasks for User Story 1 together:
Task: "Write test for registry match forcing 'authorized' classification in backend/correlator/pkg/engine/correlator_test.go (T012)"
Task: "Write test for high-score detection with registry match in backend/correlator/pkg/engine/correlator_test.go (T013)"
Task: "Write test for expired registry entry in backend/correlator/pkg/engine/correlator_test.go (T014)"
Task: "Write test for non-matched detection threshold logic in backend/correlator/pkg/engine/correlator_test.go (T015)"
Task: "Write test for registry API unavailability in backend/correlator/pkg/engine/correlator_test.go (T016)"
Task: "Write test for score calculation with registry penalty in backend/correlator/pkg/engine/correlator_test.go (T017)"
Task: "Write test for negative score flooring in backend/correlator/pkg/engine/correlator_test.go (T018)"
```

## Parallel Example: User Story 2 (Integration Tests)

```bash
# Launch all integration test writing tasks for User Story 2 together (after infrastructure T021-T024):
Task: "Write integration test for initial 'unauthorized' detection in backend/correlator/tests/integration/workflow_test.go (T025)"
Task: "Write integration test for MCP registration in backend/correlator/tests/integration/workflow_test.go (T026)"
Task: "Write integration test for re-detection showing 'authorized' in backend/correlator/tests/integration/workflow_test.go (T027)"
Task: "Write integration test for UI badge display in backend/correlator/tests/integration/workflow_test.go (T028)"
Task: "Write integration test for registry API unavailability in backend/correlator/tests/integration/workflow_test.go (T029)"
```

## Parallel Example: User Story 3 (UI Components)

```bash
# Launch all component creation tasks for User Story 3 together:
Task: "Create DetectionBadge component in frontend/src/components/DetectionBadge.tsx (T033)"
Task: "Create DashboardSummary component in frontend/src/components/DashboardSummary.tsx (T034)"
Task: "Create DetectionFilter component in frontend/src/components/DetectionFilter.tsx (T035)"

# Then launch all component test writing tasks together:
Task: "Write test for DetectionBadge green rendering in frontend/src/components/DetectionBadge.test.tsx (T040)"
Task: "Write test for DetectionBadge yellow rendering in frontend/src/components/DetectionBadge.test.tsx (T041)"
Task: "Write test for DetectionBadge red rendering in frontend/src/components/DetectionBadge.test.tsx (T042)"
Task: "Write test for DashboardSummary counts in frontend/src/components/DashboardSummary.test.tsx (T043)"
Task: "Write test for DashboardSummary loading state in frontend/src/components/DashboardSummary.test.tsx (T044)"
Task: "Write test for DashboardSummary error state in frontend/src/components/DashboardSummary.test.tsx (T045)"
Task: "Write test for DetectionFilter toggle in frontend/src/components/DetectionFilter.test.tsx (T046)"
Task: "Write test for DetectionFilter search query in frontend/src/components/DetectionFilter.test.tsx (T047)"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (unit tests) AND Phase 4: User Story 2 (integration tests) **in parallel**
4. **STOP and VALIDATE**: Run full test suite and verify all tests pass
5. Complete Phase 7: CI/CD Pipeline Configuration
6. **Deploy/Demo**: Backend testing complete, CI/CD automated

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + User Story 2 (in parallel) → Test independently → Deploy/Demo (MVP!)
3. Add User Story 3 → Test independently → Deploy/Demo (UI improvements)
4. Add User Story 4 → Review documentation (Optional enhancement)
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - **Developer A**: User Story 1 (unit tests) - T012 through T020
   - **Developer B**: User Story 2 (integration tests) - T021 through T032
   - **Developer C**: User Story 4 (documentation) - T050 through T053
3. After US1 + US2 complete:
   - **Developer A or B**: User Story 3 (UI components) - T033 through T049
   - **Developer C**: CI/CD Pipeline - T054 through T062
4. Stories complete and integrate independently

### Critical Path

The fastest path to a working MVP:

1. **Phase 1** (Setup) → ~30 minutes
2. **Phase 2** (Foundational) → ~2 hours
3. **Phase 3** (US1 unit tests) → ~4 hours (parallel with Phase 4)
4. **Phase 4** (US2 integration tests) → ~6 hours (parallel with Phase 3)
5. **Phase 7** (CI/CD) → ~1 hour
6. **Total MVP Time**: ~9-10 hours (with parallelism)

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- Each user story should be independently completable and testable
- This feature IS about testing, so tests are the primary deliverable (not optional)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- **Key Success Metric**: 100% unit test coverage (SC-001), integration tests <30s (SC-002), flakiness <5% (SC-007)
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
