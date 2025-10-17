# Feature Specification: MCP Detection Platform

**Feature Branch**: `001-mcp-detection-platform`
**Created**: 2025-10-16
**Status**: Draft
**Input**: User description: "main based this on @docs/ and you @.specify/ etc"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unauthorized MCP Discovery and Registration (Priority: P1)

A developer runs a local MCP server for testing. The system automatically detects this unauthorized instance through file scanning, network monitoring, or gateway analysis. The developer receives a notification showing exactly what triggered the detection (manifest file, network traffic pattern, or LLM judge classification). They can immediately confirm ownership and register the MCP with a purpose statement, converting it from "unauthorized" to "authorized" status within minutes.

**Why this priority**: This is the core value proposition - detecting shadow IT MCP instances while maintaining developer productivity. Without this, the entire platform has no purpose.

**Independent Test**: Can be fully tested by starting a local MCP server, waiting for detection notification, and completing the registration workflow. Success means the detection appears in the UI and the developer can self-register without administrator intervention.

**Acceptance Scenarios**:

1. **Given** a developer starts a local MCP server with a manifest file, **When** the endpoint scanner runs its 12-hour cycle, **Then** the system detects the manifest file, scores it appropriately, and creates a detection record within 60 seconds
2. **Given** an unauthorized MCP detection appears in the UI, **When** the developer clicks "Confirm Ownership", **Then** a registration form appears pre-populated with detected host/port information
3. **Given** a developer submits the registration form with purpose and TTL, **When** the form is submitted, **Then** the MCP record is created in the registry and future detections are automatically matched as "authorized"
4. **Given** an authorized MCP in the registry, **When** the same MCP is detected again, **Then** the risk score is reduced by 6 points and classification shows "authorized"

---

### User Story 2 - SOC Analyst Investigation of High-Risk Detections (Priority: P2)

A security analyst monitors the detection dashboard and sees a high-risk MCP (score ≥9) flagged as unauthorized. They open the investigation panel to view all evidence: endpoint file snippets, network traffic indicators, and LLM judge classifications. After reviewing the context, they determine if this is a legitimate developer tool or a potential security risk. They mark the finding as true positive or false positive, and this feedback is used to improve detection accuracy.

**Why this priority**: Security teams need investigative tools to differentiate between legitimate developer MCPs and actual threats. This enables the "human-in-the-loop" workflow that builds organizational trust.

**Independent Test**: Can be tested by creating synthetic detections with various evidence types, filtering the dashboard for high-risk items, and completing the investigation workflow with feedback submission. Success means all evidence is viewable and feedback is recorded.

**Acceptance Scenarios**:

1. **Given** multiple detections exist in the system, **When** the analyst filters for score > 9 and unregistered status, **Then** only matching detections appear in the feed
2. **Given** a detection record, **When** the analyst opens the investigation panel, **Then** all evidence is displayed in organized tabs: endpoint evidence, network evidence, and judge classification
3. **Given** evidence from multiple sources (endpoint + network + judge), **When** the analyst reviews each tab, **Then** they can see the original file paths, network packet indicators, and semantic classification reasoning
4. **Given** an investigation is complete, **When** the analyst marks it as true positive or false positive, **Then** the feedback is recorded and aggregated for detection model improvement

---

### User Story 3 - Platform Engineer Registry Management (Priority: P3)

A platform engineer manages the authorized MCP registry to maintain an up-to-date inventory of approved tools. They review pending registrations from developers, approve or deny them based on organizational policy, and monitor expiration dates. When MCPs reach their TTL, they receive reminders to renew or archive the entries. They can also manually add pre-approved MCPs before developers deploy them.

**Why this priority**: Registry management provides governance and lifecycle tracking, but the system can function with automatic developer registration (P1) and manual investigation (P2) without dedicated admin workflows.

**Independent Test**: Can be tested by creating registry entries, setting expiration dates, and verifying approval workflows function correctly. Success means engineers can CRUD registry entries and receive expiration notifications.

**Acceptance Scenarios**:

1. **Given** a new MCP registration from a developer, **When** the platform engineer reviews it, **Then** they can see the submitter, purpose, host/port, and proposed TTL
2. **Given** a pending registry entry, **When** the engineer approves it, **Then** the entry becomes active and future detections are matched against it
3. **Given** an authorized MCP approaching expiration (within 14 days), **When** the system runs its daily check, **Then** a notification is sent to the owner and platform team
4. **Given** an expired MCP registry entry, **When** it is detected again, **Then** the system treats it as unauthorized until renewed

---

### User Story 4 - Multi-Layer Correlation and Scoring (Priority: P1)

The system continuously ingests events from three independent sources: endpoint file/process scans, network traffic monitoring (Zeek/Suricata), and LLM gateway request analysis. When multiple signals correlate to the same host or MCP instance, the scoring algorithm combines them to produce a confidence level. Single-source detections remain in "suspect" classification while multi-source detections escalate to "unauthorized" if score ≥9. This reduces false positives from JSON-RPC protocols that resemble MCP but aren't.

**Why this priority**: Multi-layer correlation is the technical foundation that makes detection accurate. Without it, false positive rates are unacceptable for enterprise deployment.

**Independent Test**: Can be tested by simulating events from different sources for the same target and verifying the correlation logic produces correct scores and classifications. Success means single-source detections don't escalate while correlated detections do.

**Acceptance Scenarios**:

1. **Given** an endpoint scanner detects a manifest file (score 5), **When** no other signals are present, **Then** the finding remains in "suspect" classification (score < 9)
2. **Given** endpoint evidence (score 11) and network traffic (score 3), **When** both correlate to the same host, **Then** the combined score is 14 and classification is "unauthorized"
3. **Given** a detection with score 12 and no registry match, **When** the LLM judge adds a classification with score 5, **Then** the total score increases to 17
4. **Given** a detection matching an authorized registry entry, **When** the correlator applies the registry penalty, **Then** the score is reduced by 6 points

---

### User Story 5 - Observability and Transparency for Developers (Priority: P2)

Developers need to understand why their MCP was flagged to build trust in the system. Every detection shows clear evidence: which files triggered it, what network patterns were observed, and how the LLM judge classified the behavior. The UI includes explanatory text avoiding security jargon. Developers can see their own detections without requiring SOC intervention, and the one-click registration workflow doesn't block their work.

**Why this priority**: Transparency prevents developer backlash and "shadow IT" evasion. This is critical for adoption but can be implemented after core detection (P1) is working.

**Independent Test**: Can be tested by triggering a detection and verifying the UI displays all evidence with clear explanations. Success means a non-security developer can understand why their tool was flagged without help.

**Acceptance Scenarios**:

1. **Given** a detection with endpoint evidence, **When** a developer views it, **Then** the UI shows the exact file path, snippet (≤1KB), and SHA256 hash without exposing full file contents
2. **Given** a detection triggered by multiple signal types, **When** the developer views the evidence panel, **Then** each signal type is clearly labeled with its contribution to the total score
3. **Given** a detection with LLM judge classification, **When** the developer views the explanation, **Then** the UI shows the semantic reasoning (e.g., "Contains tool registration and initialization pattern") in plain language
4. **Given** a developer wants to understand the scoring algorithm, **When** they view the help documentation, **Then** thresholds are clearly explained: Authorized (≤4), Suspect (5-8), Unauthorized (≥9)

---

## Clarifications

### Session 2025-10-16

- Q: How should the system identify "the same MCP instance" across IP address changes and container recreations for correlation and registry matching? → A: Combination of host + port + manifest hash + process signature (strongest identification)
- Q: How should the system deliver detection notifications and expiration reminders to users? → A: Configurable per-user preference (email, webhook, in-app, or combinations)
- Q: What authentication and authorization model should control access to detections and registry operations? → A: RBAC with three roles (Developer: view own detections + register; Analyst: view all + investigate; Admin: full access)
- Q: How should the detection pipeline handle LLM Judge service failures? → A: Continue without Judge input, score using endpoint+network only, mark as "judge_unavailable" for retrospective scoring
- Q: How should the system deduplicate detections when multiple scanners report the same instance within seconds? → A: Time-based deduplication window (configurable, default 5 minutes) using composite identifier matching

---

### Edge Cases

- When an MCP server changes IP addresses but keeps the same manifest file, the system identifies it as the same instance using the composite identifier (manifest SHA256 hash + process signature) and updates the host/port in the registry entry
- Containerized MCPs that recreate with new host IDs are tracked by their manifest hash and process signature, allowing continuity across container restarts
- What if a legitimate application uses JSON-RPC 2.0 but isn't an MCP server?
- How are detections handled when the endpoint scanner and network monitor disagree on host identity?
- When the LLM Judge service is unavailable, the detection pipeline continues using only endpoint and network signals for scoring, marks detections with a "judge_unavailable" flag, and retrospectively re-scores them when the Judge service recovers
- How does the system handle bulk MCP deployments (10+ instances) from infrastructure automation?
- What if a developer registers an MCP but then the endpoint scanner detects a different instance with the same purpose on a different port?
- Detections from multiple scanners reporting the same MCP instance are deduplicated using a time-based window (configurable, default 5 minutes). The system uses composite identifier matching to merge signals into a single detection record, combining evidence from all sources
- What happens when a Developer user is promoted to Analyst role - do they retain access to their previously registered MCPs?
- How does the system determine which endpoints belong to a Developer user for scoping their detection visibility?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect MCP servers through at least one of three mechanisms: endpoint file/process scanning, network traffic analysis, or LLM gateway monitoring
- **FR-002**: System MUST correlate signals from multiple detection sources (endpoint, network, gateway) to the same target host or MCP instance
- **FR-002a**: System MUST deduplicate detection records using a configurable time-based window (default 5 minutes) when multiple scanners report the same MCP instance based on composite identifier matching
- **FR-002b**: System MUST merge evidence from all detection sources into a single detection record during the deduplication window, preserving complete signal history
- **FR-003**: System MUST score detections using a weighted algorithm: endpoint events carry the highest weight, judge classifications medium, and network signatures provide supporting evidence
- **FR-004**: System MUST classify detections into three categories based on score: Authorized (≤4), Suspect (5-8), Unauthorized (≥9)
- **FR-005**: System MUST check all detections against an authorized MCP registry and reduce scores by 6 points for matched entries
- **FR-005a**: System MUST identify MCP instances using a composite identifier combining host, port, manifest file SHA256 hash, and process signature to handle IP changes and container recreations
- **FR-006**: Users MUST be able to register unauthorized MCPs by providing host, port, owner, team, purpose, and expiration date
- **FR-007**: System MUST display all evidence for each detection including file paths, network indicators, and semantic classifications
- **FR-008**: System MUST anonymize host identifiers by hashing them before storage in the analytics database
- **FR-009**: System MUST retain only minimal file content snippets (≤1KB) required for classification, not full file contents
- **FR-010**: System MUST enforce mutual TLS for all inter-service communication between components
- **FR-011**: System MUST complete end-to-end detection pipeline (from signal ingestion to UI display) within 60 seconds
- **FR-012**: System MUST provide a dashboard showing active MCPs, score distribution, and detection trendlines
- **FR-013**: System MUST allow filtering detections by score threshold, registry status, and time range
- **FR-014**: System MUST expose Prometheus metrics for detection latency, false positive rates, and LLM judge accuracy
- **FR-015**: System MUST support declarative YAML configuration for detection rules, scoring thresholds, and component behavior
- **FR-016**: System MUST validate all YAML configuration files against JSON schemas before deployment
- **FR-017**: System MUST run endpoint file scans on a configurable interval (default: every 12 hours)
- **FR-018**: System MUST scan configurable filesystem roots (e.g., /home, /Users, /workspace) for MCP manifest patterns
- **FR-019**: System MUST run network monitoring continuously via Zeek and Suricata for MCP protocol signatures
- **FR-020**: System MUST classify LLM gateway requests using a Judge service with configurable timeout (≤400ms)
- **FR-020a**: System MUST continue detection pipeline operations when Judge service is unavailable, scoring detections using only endpoint and network signals
- **FR-020b**: System MUST flag detections processed without Judge input with a "judge_unavailable" indicator visible in the UI
- **FR-020c**: System MUST automatically re-score detections marked "judge_unavailable" when Judge service recovers, updating classifications and scores accordingly
- **FR-021**: System MUST maintain signed audit logs for all detections, registry changes, and administrative actions
- **FR-022**: System MUST retain audit logs for minimum 90 days
- **FR-023**: Users MUST be able to mark detections as true positive or false positive for feedback loop
- **FR-024**: System MUST support MCP registry entry expiration with configurable TTL
- **FR-025**: System MUST send notifications when registry entries approach expiration (14 days before)
- **FR-025a**: System MUST allow users to configure notification delivery preferences including email, webhook endpoints (Slack/Teams/PagerDuty), in-app notifications, or any combination thereof
- **FR-025b**: System MUST provide a notification center in the UI showing recent alerts for users who enable in-app notifications
- **FR-026**: System MUST handle 10,000 concurrent endpoints generating events
- **FR-027**: System MUST process 100 million events per month without degradation
- **FR-028**: System MUST provide 99.5% uptime for the UI portal and detection pipeline
- **FR-029**: System MUST support zero-downtime upgrades for all services
- **FR-030**: System MUST allow plugin extensions for custom detection rules and Judge model replacements
- **FR-031**: System MUST implement role-based access control (RBAC) with three roles: Developer, Analyst, and Admin
- **FR-032**: Developer role MUST allow users to view detections associated with their own endpoints, register MCPs, and configure personal notification preferences
- **FR-033**: Analyst role MUST allow users to view all detections, filter and search across the entire detection feed, mark findings as true/false positives, and access all investigation evidence
- **FR-034**: Admin role MUST allow users to perform all operations including registry approval/denial, user role management, system configuration changes, and audit log access
- **FR-035**: System MUST prevent unauthorized access by enforcing role permissions on all API endpoints and UI views

### Key Entities
            
- **MCP Detection**: Represents a single detection event with correlated evidence from multiple sources, assigned score, classification (authorized/suspect/unauthorized), timestamp, host identifier, and registry match status
- **Evidence**: Individual signals contributing to a detection - can be endpoint (file/process), network (traffic pattern), or gateway (LLM classification). Contains type, source, raw data snippet, and score contribution
- **Registry Entry**: Authorized MCP record with composite identifier (host, port, manifest SHA256 hash, process signature), owner, team, purpose, approval status, creation date, expiration date, and renewal history
- **Endpoint Event**: File system or process detection from the Go scanner including host ID, file paths, SHA256 hashes, process commands, and local score
- **Network Event**: Traffic signature match from Zeek/Suricata including source/destination IPs, port, protocol indicators, payload excerpt, and sensor ID
- **Gateway Event**: LLM request classification from the Judge service including user ID, model ID, request excerpt, classification label, confidence score, and explanation
- **Feedback Record**: Analyst annotation of a detection as true positive or false positive, used for model tuning and accuracy metrics
- **User**: Authenticated user account with assigned role (Developer, Analyst, or Admin), associated endpoints (for Developer role scope), email address, and notification preferences
- **User Notification Preferences**: User configuration for notification delivery including enabled channels (email, webhook URLs, in-app), notification types subscribed to (detections, expirations, system alerts), and delivery thresholds (e.g., only notify for score ≥9)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System detects unauthorized MCP instances within 60 seconds of signal ingestion across all three detection layers (endpoint, network, gateway)
- **SC-002**: False positive rate for multi-layer correlated detections is ≤10% as measured by analyst feedback over 30-day windows
- **SC-003**: Developers can complete the self-registration workflow (from detection notification to authorized status) in under 3 minutes
- **SC-004**: System maintains 99.5% uptime for the detection pipeline and UI portal over 30-day periods
- **SC-005**: Platform supports 10,000 concurrent endpoints generating events without detection latency exceeding 60 seconds
- **SC-006**: LLM Judge service classifies gateway requests within 400ms at the 95th percentile
- **SC-007**: Dashboard queries for detection feeds and analytics complete within 2 seconds for 90% of requests
- **SC-008**: System successfully processes 100 million events per month (approximately 40 events/second sustained)
- **SC-009**: 80% of endpoints are covered by scanning within 90 days of platform deployment
- **SC-010**: Detection rule updates are deployed to production within 14 days of community signature releases
- **SC-011**: Single-source detections (only endpoint OR network OR judge) correctly remain in "suspect" classification 95% of the time
- **SC-012**: Multi-source detections (2+ signal types) achieve ≥90% accuracy in distinguishing MCP from generic JSON-RPC traffic
- **SC-013**: Developers report ≥70% satisfaction with detection transparency and registration workflow in user surveys
- **SC-014**: Security analysts can investigate and triage a detection (view evidence + submit feedback) in under 5 minutes
- **SC-015**: System exposes complete Prometheus metrics coverage with ≥95% of key operations instrumented (detection counts, latency percentiles, error rates, judge accuracy)

## Assumptions

- Organizations deploying this system have existing network monitoring infrastructure (Zeek/Suricata) or are willing to deploy it
- Endpoints run operating systems compatible with the Go scanner (Linux, macOS, Windows)
- LLM gateway integration is optional - system can function with endpoint + network detection only
- Users have basic understanding of MCP protocol concepts (what a manifest file is, what JSON-RPC means)
- Registry approval workflows are manual initially; automation can be added in future phases
- Detection signatures are maintained by the community and updated through configuration (not code changes)
- Anonymized detection data (hashed host IDs, evidence snippets) is acceptable for analytics storage
- Mutual TLS certificate infrastructure either exists or will be provisioned as part of deployment
- ClickHouse and PostgreSQL infrastructure is available or will be deployed alongside the platform
- NATS JetStream provides at-least-once delivery guarantees sufficient for detection events (exactly-once not required)
