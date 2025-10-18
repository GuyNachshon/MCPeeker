# Feature Specification: Testing and UI Improvements for Registry Match Classification

**Feature Branch**: `002-testing-ui-improvements`
**Created**: 2025-10-18
**Status**: Draft
**Input**: User description: "Add unit tests for registry match scoring, integration tests for detection workflow, and UI improvements for classification visibility"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Developer Trust in Registry Match Behavior (Priority: P1)

A platform engineer implements the recent registry match scoring fix and needs confidence that approved MCPs are always classified as "authorized" regardless of their detection score. They run the test suite and see comprehensive coverage for registry matching logic, including edge cases like high-score detections and expired registrations. This gives them confidence to deploy the fix to production without fear of regressions.

**Why this priority**: Testing the core scoring logic is critical for system reliability. Without these tests, future code changes could break the registry match behavior, causing approved MCPs to trigger false alerts again. This directly impacts the fix we just implemented.

**Independent Test**: Can be fully tested by running `go test ./backend/correlator/pkg/engine/...` and verifying all registry match test cases pass, including force classification, high scores with registry match, and expired entries.

**Acceptance Scenarios**:

1. **Given** a detection with endpoint evidence (score 11) and registry match, **When** the correlator recalculates the detection, **Then** the classification is forced to "authorized" regardless of the score
2. **Given** a detection with multiple high-score signals (total 21) and registry match, **When** the correlator recalculates the detection, **Then** the classification is still forced to "authorized"
3. **Given** a detection matching an expired registry entry, **When** the correlator checks the registry, **Then** the match returns false and scoring proceeds normally as "unauthorized"
4. **Given** a detection with no registry match, **When** the correlator recalculates the detection, **Then** the classification uses threshold-based logic (authorized ≤4, suspect 5-8, unauthorized ≥9)

---

### User Story 2 - End-to-End Workflow Validation (Priority: P1)

A QA engineer needs to verify that the entire detection → registration → re-detection workflow functions correctly after the scoring fix. They run integration tests that simulate a real-world scenario: scanner finds an MCP, developer registers it, scanner detects it again, and the system correctly shows it as "authorized". The tests cover the full stack (scanner, correlator, registry API, UI) and catch integration issues that unit tests would miss.

**Why this priority**: Integration tests validate that all services work together correctly. The scoring fix touches multiple components (correlator, registry client, UI), and only end-to-end tests can confirm they're properly integrated. This is equally critical as unit tests for production readiness.

**Independent Test**: Can be fully tested by running Docker Compose test environment, deploying a test MCP, registering it via API, triggering another scan, and verifying the UI shows "authorized" status with correct badge styling.

**Acceptance Scenarios**:

1. **Given** a scanner detecting a new MCP manifest file, **When** the detection flows through correlator to UI, **Then** the UI displays it as "unauthorized" with score 11
2. **Given** a developer registering the MCP via API (POST /api/v1/mcps), **When** the registration completes, **Then** a registry entry is created with status "approved"
3. **Given** the scanner detecting the same MCP again after registration, **When** correlator checks registry and finds a match, **Then** the detection is classified as "authorized" with score 5 (11 - 6)
4. **Given** an "authorized" detection displayed in the UI, **When** the user views the detection list, **Then** the MCP shows a green "authorized" badge and does not appear in the high-priority alert queue

---

### User Story 3 - Improved Classification Visibility for SOC Analysts (Priority: P2)

A SOC analyst reviewing the MCPeeker dashboard needs to quickly differentiate between authorized, suspect, and unauthorized MCPs. The updated UI provides prominent visual indicators (colored badges), a dashboard summary showing counts by classification, and filter options to hide authorized MCPs when focusing on threats. This reduces cognitive load and helps analysts triage detections faster.

**Why this priority**: UI improvements enhance usability but don't affect core functionality. The system works without them, but they significantly improve analyst productivity. This can be implemented after core testing (P1) is complete.

**Independent Test**: Can be fully tested by opening the MCPeeker dashboard with sample detections of each classification type, verifying badges are color-coded (green/yellow/red), checking the summary counts match actual detections, and testing the "Hide authorized MCPs" filter.

**Acceptance Scenarios**:

1. **Given** detections with mixed classifications in the database, **When** the analyst opens the dashboard, **Then** a summary panel displays: "X unauthorized, Y suspect, Z authorized" with color-coded counts
2. **Given** a detection list with all three classification types, **When** the list renders, **Then** each detection shows a colored badge: green for "authorized", yellow for "suspect", red for "unauthorized"
3. **Given** the analyst wants to focus on threats, **When** they toggle the "Hide authorized MCPs" filter, **Then** only "suspect" and "unauthorized" detections are displayed
4. **Given** a registry-matched detection with high score (e.g., 15), **When** the analyst views the detection details, **Then** the UI shows both the raw score (15) and the "authorized" classification badge with explanation text

---

### User Story 4 - Optional Weight Adjustment Configuration (Priority: P3)

A platform engineer wants to make the registry penalty more obvious in the scoring calculation. They update the scoring weights configuration to increase the registry penalty from -6 to -12, making it clear that registry match strongly outweighs other signals. However, they realize this is unnecessary because the forced classification already ensures correct behavior. This story documents the consideration but marks it as optional.

**Why this priority**: This is the lowest priority because the forced classification override already solves the problem. Adjusting weights provides transparency in scoring but doesn't change behavior. It's a "nice to have" for documentation purposes.

**Independent Test**: Can be fully tested by updating `ScoringWeights.Registry` to -12 in configuration, running correlator with a registry-matched detection, and verifying the score calculation reflects the new weight (e.g., 11 - 12 = -1 → floored to 0).

**Acceptance Scenarios**:

1. **Given** scoring weights configuration with registry penalty set to -12, **When** a detection matches the registry, **Then** the score calculation shows totalScore + (-12) instead of totalScore + (-6)
2. **Given** a detection with score 11 and registry penalty -12, **When** the score is calculated, **Then** the result is floored to 0 (negative scores not allowed)
3. **Given** documentation explaining scoring weights, **When** platform engineers read it, **Then** they understand that forced classification makes the exact penalty value less critical

---

### Edge Cases

- What happens when a registry entry expires between scans (detected as approved, then expired, then detected again)?
- **Registry API unavailability**: When registry API is unavailable during correlation, correlator logs a warning and treats registry match as false, proceeding with normal scoring (detection classified as unauthorized)
- What if a detection has identical composite ID to a registry entry but different manifest hash (collision scenario)?
- How does UI render when a detection transitions from "unauthorized" to "authorized" in real-time (WebSocket update)?
- What happens when a test tries to mock registry responses with malformed data?

## Requirements *(mandatory)*

### Functional Requirements

**Testing Requirements:**

- **FR-001**: System MUST include unit tests for correlator registry match logic that verify forced "authorized" classification when `registryMatch.Matched == true`
- **FR-002**: System MUST include unit tests verifying that high-score detections (score ≥ 9) with registry matches are still classified as "authorized"
- **FR-003**: System MUST include unit tests verifying that expired registry entries return `Matched: false` and detections are scored normally
- **FR-004**: System MUST include unit tests verifying that non-matched detections use threshold-based classification (≤4 = authorized, 5-8 = suspect, ≥9 = unauthorized)
- **FR-005**: System MUST include integration tests that validate end-to-end detection → registration → re-detection workflow across scanner, correlator, registry API, and UI, including registry API unavailability scenario where correlator logs warning and proceeds with scoring (registry match = false)
- **FR-006**: System MUST include integration tests that verify UI displays correct classification badges for all three states (authorized, suspect, unauthorized)
- **FR-013**: CI/CD pipeline MUST run unit tests on every PR commit and run integration tests after unit tests pass and before merge to main
- **FR-014**: Integration tests MUST support automatic retry up to 2 times in CI for handling test flakiness; tests failing after all retries require investigation

**UI Requirements:**

- **FR-007**: Dashboard MUST display a summary panel showing counts of detections by classification: "X unauthorized, Y suspect, Z authorized"
- **FR-008**: Detection list MUST display a colored badge for each detection indicating classification status (green = authorized, yellow = suspect, red = unauthorized)
- **FR-009**: Dashboard MUST provide a filter toggle "Hide authorized MCPs" that removes authorized detections from the view when enabled
- **FR-010**: Detection detail view MUST show both the raw score and the classification badge with explanation text when classification is forced by registry match

**Configuration Requirements (Optional):**

- **FR-011**: Scoring weights configuration SHOULD allow adjustment of registry penalty value (default: -6, suggested range: -6 to -15)
- **FR-012**: Documentation MUST explain that forced classification makes exact registry penalty value non-critical for behavior

### Key Entities

- **Test Case**: Represents a unit or integration test with inputs, expected outputs, and assertions. Attributes: test name, test type (unit/integration), test data (mock objects, sample detections), assertions (expected classification, score, etc.)
- **Dashboard Summary**: UI component showing aggregate statistics. Attributes: unauthorized count, suspect count, authorized count, last updated timestamp
- **Detection Badge**: Visual indicator of classification status. Attributes: classification type (authorized/suspect/unauthorized), color code (green/yellow/red), tooltip text
- **Filter State**: UI state controlling which detections are visible. Attributes: hide_authorized boolean, search query, date range

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Unit test coverage for correlator registry match logic reaches 100% (all code paths tested: matched, not matched, expired, high score)
- **SC-002**: Integration test suite validates complete workflow in under 30 seconds (from MCP deployment to UI verification)
- **SC-003**: SOC analysts can identify detection classification within 2 seconds of viewing the dashboard (visual badges + summary panel)
- **SC-004**: 95% of analysts successfully use the "Hide authorized MCPs" filter without training or documentation
- **SC-005**: Zero regressions in registry match behavior after future correlator changes (tests catch any breaking changes)
- **SC-006**: Platform engineers can verify correct scoring behavior by reading test names alone (clear, descriptive test naming)
- **SC-007**: Integration test flakiness rate below 5% (95% of test runs pass on first attempt without requiring retries)

## Assumptions

- Go testing framework (`go test`) is already configured for the correlator package
- Integration test environment has Docker Compose setup with all services (scanner, correlator, registry-api, NATS, PostgreSQL)
- UI framework supports dynamic badge rendering and filter state management
- Registry API `/verify` endpoint is already implemented and functional
- Frontend has access to detection classification data via API or WebSocket
- Test data fixtures for sample MCPs and registry entries are available or can be created
- CI/CD pipeline has separate stages for unit tests (run on every commit) and integration tests (run after unit tests pass)

## Out of Scope

- Performance testing or load testing of scoring algorithm
- UI redesign beyond badge colors and filter additions
- Automated remediation or quarantine features for unauthorized MCPs
- Integration with external threat intelligence feeds
- Mobile-responsive UI improvements (focus is desktop dashboard)
- Accessibility improvements (WCAG compliance) for new UI elements
- Multi-language support for UI labels and badges
- Custom scoring weight profiles per organization or team

## Dependencies

- Recent correlator fix that forces "authorized" classification for registry matches (already implemented in `backend/correlator/pkg/engine/correlator.go`)
- Registry API must be running and accessible for integration tests
- Scanner service must support triggering manual scans for integration test scenarios
- Frontend build tooling must support running component tests (if UI tests are included)
- NATS JetStream must be available for integration test event publishing

## Clarifications

### Session 2025-10-18

- Q: How should integration tests handle the scenario when the registry API becomes unavailable during correlation? → A: Test should verify correlator logs a warning and continues with scoring (registry match = false), treating the detection as unauthorized
- Q: When should the new tests run in the CI/CD pipeline? → A: Run unit tests on every PR commit; run integration tests only after unit tests pass and before merge to main
- Q: How should the system handle test flakiness (intermittent failures) in integration tests? → A: Retry failed integration tests up to 2 times automatically in CI; if still failing after retries, mark as failed and require investigation
