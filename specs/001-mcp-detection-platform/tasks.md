# Tasks: MCP Detection Platform

**Input**: Design documents from `/specs/001-mcp-detection-platform/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/
**Date**: 2025-10-16

**Tests**: The spec does NOT explicitly request tests, so test tasks are NOT included. Focus is on implementation only.

## Format: `- [ ] T### [P?] [US#?] Description with file path`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[US#]**: User story label (US1, US2, US3, US4, US5)
- File paths are absolute from repository root

## Path Conventions
This is a **web application** with:
- `backend/scanner/` - Go endpoint agent
- `backend/signature-engine/` - Python pattern matching
- `backend/correlator/` - Go correlation service
- `backend/judge/` - Python LLM classifier
- `backend/registry-api/` - Python FastAPI service
- `frontend/` - React UI
- `infrastructure/` - Docker, Helm, configs

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md: backend/{scanner,signature-engine,correlator,judge,registry-api}/, frontend/, infrastructure/{docker,helm,configs}/, tests/
- [X] T002 [P] Initialize Go modules in backend/scanner/go.mod with dependencies: NATS client, SHA256, testify
- [X] T003 [P] Initialize Go modules in backend/correlator/go.mod with dependencies: NATS, ClickHouse driver, PostgreSQL driver
- [X] T004 [P] Initialize Python project backend/signature-engine/requirements.txt with dependencies: NATS client, pydantic, PyYAML
- [X] T005 [P] Initialize Python project backend/judge/requirements.txt with dependencies: FastAPI, transformers, ONNX Runtime, uvicorn
- [X] T006 [P] Initialize Python project backend/registry-api/requirements.txt with dependencies: FastAPI, SQLAlchemy, alembic, psycopg2, uvicorn
- [X] T007 [P] Initialize React project in frontend/package.json with dependencies: React 18, Tailwind CSS, Zustand, SWR, TypeScript
- [X] T008 [P] Configure linting: Go (golangci-lint), Python (black, flake8, mypy), TypeScript (ESLint, Prettier)
- [X] T009 [P] Setup Docker Compose file in infrastructure/docker/docker-compose.yml with NATS, ClickHouse, PostgreSQL, Prometheus, Grafana
- [X] T010 [P] Create Helm chart structure in infrastructure/helm/mcpeeker/ with values.yaml and templates/
- [X] T011 [P] Setup GitHub Actions CI workflow in .github/workflows/ci.yml for linting, security scanning (Gosec, Bandit, Trivy)

**Checkpoint**: Project structure ready, dependencies installed, CI configured

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**CRITICAL**: No user story work can begin until this phase is complete

### Database Infrastructure

- [X] T012 Create ClickHouse schema migration in infrastructure/docker/clickhouse/init_tables.sql: detections table, feedback_records table, aggregated_metrics materialized view per data-model.md
- [X] T013 Create PostgreSQL schema migration in backend/registry-api/alembic/versions/001_initial_schema.py: users, registry_entries, notification_preferences, audit_logs tables per data-model.md
- [X] T014 Create JSON Schema files in infrastructure/configs/schemas/: endpoint-event.schema.json, network-event.schema.json, gateway-event.schema.json per contracts/events.yaml
- [X] T015 [P] Create NATS stream configuration YAML in infrastructure/configs/nats-streams.yaml: endpoint.events, network.events, gateway.events with 7-day retention per research.md

### Core Models and Utilities

- [X] T016 [P] Create composite identifier utility in backend/correlator/pkg/identifier/composite.go: generate_composite_id(host, port, manifest_hash, process_signature) per data-model.md
- [X] T017 [P] Create host ID hashing utility in backend/correlator/pkg/identifier/hash.go: hash_host_id(host_id) using SHA256 per FR-008
- [X] T018 [P] Create YAML configuration loader in backend/scanner/pkg/config/loader.go: load global.yaml, scanner.yaml with validation
- [X] T019 [P] Create YAML configuration loader in backend/correlator/pkg/config/loader.go: load global.yaml, correlator.yaml with validation
- [X] T020 [P] Create YAML configuration loader in backend/judge/src/config/loader.py: load global.yaml, judge.yaml using Hydra per plan.md
- [X] T021 [P] Create YAML configuration loader in backend/registry-api/src/config/loader.py: load global.yaml, registry-api.yaml

### Authentication and RBAC

- [X] T022 Create RBAC middleware in backend/registry-api/src/auth/rbac.py: Developer, Analyst, Admin role enforcement per FR-031-035
- [X] T023 Create JWT authentication middleware in backend/registry-api/src/auth/jwt.py: bearer token validation with user_id, email, role claims
- [X] T024 Create user model in backend/registry-api/src/models/user.py: SQLAlchemy model matching data-model.md users table
- [X] T025 Create PostgreSQL row-level security policies in backend/registry-api/alembic/versions/002_rls_policies.py: developer_self_view, analyst_admin_view per data-model.md

### mTLS and Security

- [X] T026 [P] Create mTLS certificate generator script in infrastructure/scripts/generate-certs.sh: root CA, service certificates with 90-day validity per research.md
- [X] T027 [P] Create cert-manager Kubernetes resources in infrastructure/helm/mcpeeker/templates/certificates.yaml: Certificate CRDs for all services
- [X] T028 [P] Create mTLS client utilities in backend/correlator/pkg/mtls/client.go: load certificates, watch for changes, reload without restart
- [X] T029 [P] Create mTLS client utilities in backend/registry-api/src/mtls/client.py: load certificates, watch for changes per research.md

### Observability

- [X] T030 [P] Create Prometheus metrics registry in backend/scanner/pkg/metrics/metrics.go: event_published_total, scan_duration_seconds
- [X] T031 [P] Create Prometheus metrics registry in backend/correlator/pkg/metrics/metrics.go: detection_processed_total, clickhouse_write_latency_seconds
- [X] T032 [P] Create Prometheus metrics registry in backend/judge/src/metrics/metrics.py: inference_latency_seconds, cache_hit_rate
- [X] T033 [P] Create Grafana dashboard JSON in infrastructure/configs/grafana/dashboards/detection-overview.json: score distribution, trendlines, classification breakdown per quickstart.md
- [X] T034 [P] Create Grafana dashboard JSON in infrastructure/configs/grafana/dashboards/pipeline-health.json: service health, NATS rates, ClickHouse latency

**Checkpoint**: Foundation ready - NATS/ClickHouse/PostgreSQL schemas deployed, RBAC configured, mTLS certificates generated, metrics infrastructure ready. User story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Unauthorized MCP Discovery and Registration (Priority: P1) 🎯 MVP

**Goal**: Detect unauthorized MCP instances through file scanning and enable developer self-registration workflow

**Independent Test**: Start local MCP server with manifest file, verify detection appears in UI within 60 seconds, complete registration form to convert status from "unauthorized" to "authorized"

### Scanner Implementation (Endpoint Detection)

- [ ] T035 [P] [US1] Create file scanner in backend/scanner/pkg/filescan/scanner.go: scan filesystem roots for manifest.json patterns, extract host/port, generate SHA256 hash
- [ ] T036 [P] [US1] Create process scanner in backend/scanner/pkg/procscan/scanner.go: scan running processes for MCP server patterns, extract command line, port from arguments
- [ ] T037 [US1] Create NATS publisher in backend/scanner/pkg/reporter/publisher.go: publish endpoint.detection.file events with JSON Schema validation per contracts/events.yaml
- [ ] T038 [US1] Create scanner main entry point in backend/scanner/cmd/scanner/main.go: load config, run 12-hour scan cycle, handle SIGHUP for manual trigger per quickstart.md
- [ ] T039 [US1] Create scanner configuration YAML in infrastructure/configs/scanner.yaml: filesystem_roots, scan_interval, NATS connection per plan.md

### Registry API Implementation (MCP Registration)

- [ ] T040 [P] [US1] Create registry entry model in backend/registry-api/src/models/registry_entry.py: SQLAlchemy model matching data-model.md registry_entries table
- [ ] T041 [P] [US1] Create notification preferences model in backend/registry-api/src/models/notification_preferences.py: SQLAlchemy model per data-model.md
- [ ] T042 [US1] Implement POST /api/v1/mcps endpoint in backend/registry-api/src/api/registry.py: create MCP entry, validate purpose (10-1024 chars), generate composite_id per contracts/registry-api.yaml
- [ ] T043 [US1] Implement GET /api/v1/mcps endpoint in backend/registry-api/src/api/registry.py: list entries with pagination, RBAC filtering (Developer sees own, Analyst/Admin see all)
- [ ] T044 [US1] Implement GET /api/v1/mcps/{id} endpoint in backend/registry-api/src/api/registry.py: retrieve single entry with RBAC enforcement
- [ ] T045 [US1] Implement POST /api/v1/mcps/verify endpoint in backend/registry-api/src/api/registry.py: verify composite_id exists in approved registry per contracts/registry-api.yaml
- [ ] T046 [US1] Add audit logging to registry operations in backend/registry-api/src/services/audit.py: log CREATE/UPDATE/DELETE with signed hash per FR-021

### Frontend Implementation (Detection UI and Registration Form)

- [ ] T047 [P] [US1] Create detection list component in frontend/src/components/detections/DetectionList.tsx: display detections with score, classification, host, port, filter by score threshold
- [ ] T048 [P] [US1] Create detection detail component in frontend/src/components/detections/DetectionDetail.tsx: show evidence tabs (endpoint, network, gateway) per US5
- [ ] T049 [US1] Create registration form component in frontend/src/components/registry/RegistrationForm.tsx: pre-populate host/port, input purpose/team/TTL, submit to POST /api/v1/mcps
- [ ] T050 [US1] Create API client in frontend/src/services/registry-client.ts: SWR hooks for fetching detections, submitting registration
- [ ] T051 [US1] Create detections page in frontend/src/pages/Detections.tsx: list + detail + registration workflow per US1 acceptance scenarios
- [ ] T052 [US1] Create Zustand store in frontend/src/stores/detection-store.ts: manage detection filters, selected detection, registration form state

**Checkpoint**: User Story 1 MVP complete - Endpoint scanner detects manifest files, publishes events, developers can self-register via UI. Test by creating manifest.json and completing registration workflow.

---

## Phase 4: User Story 4 - Multi-Layer Correlation and Scoring (Priority: P1)

**Goal**: Correlate signals from endpoint, network, and gateway sources to produce accurate confidence scores and reduce false positives

**Independent Test**: Simulate events from multiple sources for same target host, verify correlation produces correct combined scores, single-source detections remain "suspect" classification

### Signature Engine Implementation

- [ ] T053 [P] [US4] Create endpoint parser in backend/signature-engine/src/parsers/endpoint_parser.py: parse endpoint.detection events, validate against JSON Schema
- [ ] T054 [P] [US4] Create network parser in backend/signature-engine/src/parsers/network_parser.py: parse network.detection events, validate Zeek/Suricata formats
- [ ] T055 [P] [US4] Create gateway parser in backend/signature-engine/src/parsers/gateway_parser.py: parse gateway.classification events from Judge service
- [ ] T056 [US4] Create Knostik rule engine in backend/signature-engine/src/rules/engine.py: load community signatures from YAML, apply pattern matching per research.md
- [ ] T057 [US4] Create enriched event publisher in backend/signature-engine/src/publisher/nats_publisher.py: republish enriched events to NATS for correlator consumption
- [ ] T058 [US4] Create signature engine main in backend/signature-engine/src/main.py: subscribe to endpoint/network/gateway streams, enrich, republish

### Correlator Implementation (Scoring and Deduplication)

- [ ] T059 [P] [US4] Create deduplication service in backend/correlator/pkg/deduplication/dedup.go: 5-minute time window, composite_id matching per FR-002a
- [ ] T060 [P] [US4] Create scoring algorithm in backend/correlator/pkg/scoring/algorithm.go: weighted sum (endpoint=high, judge=medium, network=support), classification thresholds (≤4=authorized, 5-8=suspect, ≥9=unauthorized) per FR-003/FR-004
- [ ] T061 [US4] Create registry lookup client in backend/correlator/pkg/registry/client.go: call POST /api/v1/mcps/verify, apply -6 penalty if matched per FR-005
- [ ] T062 [US4] Create ClickHouse writer in backend/correlator/pkg/storage/clickhouse.go: insert detections with nested evidence array, enforce 1KB snippet limit per FR-009
- [ ] T063 [US4] Create correlator main entry point in backend/correlator/cmd/correlator/main.go: subscribe to enriched events, deduplicate, score, lookup registry, write to ClickHouse
- [ ] T064 [US4] Create correlator configuration YAML in infrastructure/configs/correlator.yaml: dedup_window_seconds, scoring_weights, ClickHouse connection per plan.md

### Network Monitoring Integration (Zeek/Suricata)

- [ ] T065 [P] [US4] Create Zeek signature file in infrastructure/configs/zeek_suricata.yaml: MCP JSON-RPC handshake patterns, port 3000-3100 monitoring per research.md
- [ ] T066 [P] [US4] Create Suricata rule file in infrastructure/configs/zeek_suricata.yaml: MCP tool registration patterns, content matching for "tools/list"
- [ ] T067 [US4] Create network event adapter in backend/signature-engine/src/adapters/zeek_adapter.py: convert Zeek conn.log to network.detection.zeek NATS events
- [ ] T068 [US4] Create network event adapter in backend/signature-engine/src/adapters/suricata_adapter.py: convert Suricata alerts to network.detection.suricata NATS events

**Checkpoint**: User Story 4 complete - Multi-layer correlation working. Test by sending endpoint+network events for same host, verify combined score ≥9 results in "unauthorized" classification. Single-source events remain "suspect".

---

## Phase 5: User Story 2 - SOC Analyst Investigation (Priority: P2)

**Goal**: Enable security analysts to investigate high-risk detections with full evidence visibility and submit feedback on detection accuracy

**Independent Test**: Create synthetic high-risk detection (score ≥9), filter dashboard for unregistered detections, open investigation panel to view all evidence tabs, submit true positive feedback

### Findings API Implementation

- [ ] T069 [P] [US2] Implement GET /api/v1/findings endpoint in backend/registry-api/src/api/findings.py: query ClickHouse detections with score_min, classification, time_range filters per contracts/findings-api.yaml
- [ ] T070 [P] [US2] Implement GET /api/v1/findings/{id} endpoint in backend/registry-api/src/api/findings.py: retrieve detection with full nested evidence array from ClickHouse
- [ ] T071 [US2] Implement RBAC scoping in backend/registry-api/src/api/findings.py: Developer sees only own endpoints, Analyst/Admin see all per FR-032-034
- [ ] T072 [US2] Create ClickHouse query utilities in backend/registry-api/src/services/clickhouse_client.py: parameterized queries, connection pooling, ≤2s latency per SC-007

### Feedback Implementation

- [ ] T073 [P] [US2] Create feedback model in backend/registry-api/src/models/feedback.py: SQLAlchemy model for temporary PostgreSQL storage before ClickHouse write
- [ ] T074 [US2] Implement POST /api/v1/feedback endpoint in backend/registry-api/src/api/feedback.py: submit verdict (true_positive/false_positive/inconclusive), notes, tags per contracts/registry-api.yaml
- [ ] T075 [US2] Create ClickHouse feedback writer in backend/registry-api/src/services/feedback_writer.py: insert into feedback_records table, enforce 4096 char notes limit per data-model.md
- [ ] T076 [US2] Add feedback display to detection detail in frontend/src/components/detections/FeedbackPanel.tsx: show verdict, analyst, notes, submitted_at

### Frontend Investigation UI

- [ ] T077 [P] [US2] Create evidence tabs component in frontend/src/components/detections/EvidenceTabs.tsx: separate tabs for endpoint/network/gateway evidence with metadata display per US2 acceptance scenarios
- [ ] T078 [P] [US2] Create feedback form component in frontend/src/components/detections/FeedbackForm.tsx: radio buttons for verdict, textarea for notes, tag input
- [ ] T079 [US2] Create dashboard filters in frontend/src/components/dashboard/Filters.tsx: score threshold slider, registry status checkbox, time range picker per FR-013
- [ ] T080 [US2] Update detections page in frontend/src/pages/Detections.tsx: add investigation panel with evidence tabs + feedback form

**Checkpoint**: User Story 2 complete - Analysts can filter for high-risk detections, view all evidence organized by source type, submit feedback. Test by opening detection with score ≥9, reviewing evidence, marking as true positive.

---

## Phase 6: User Story 5 - Observability and Transparency (Priority: P2)

**Goal**: Provide clear explanations for why MCPs were flagged to build developer trust without security jargon

**Independent Test**: Trigger detection and verify UI shows exact file path, snippet preview, score contribution breakdown, plain-language explanation from Judge

### Judge Service Implementation (LLM Classifier)

- [ ] T081 [P] [US5] Create DistilBERT model downloader in backend/judge/scripts/download_model.py: fetch pre-trained mcp-classifier from Hugging Face per research.md
- [ ] T082 [P] [US5] Create ONNX inference engine in backend/judge/src/inference/engine.py: load model, quantize for CPU, <300ms p95 latency per FR-020
- [ ] T083 [P] [US5] Create classification endpoint in backend/judge/src/api/classify.py: POST /classify with request_excerpt input, return label + confidence + explanation
- [ ] T084 [US5] Create Redis cache layer in backend/judge/src/inference/cache.py: cache identical request fingerprints, 10ms lookup per research.md
- [ ] T085 [US5] Create Judge event publisher in backend/judge/src/publisher/nats_publisher.py: publish gateway.classification.judge events with plain-language explanations per contracts/events.yaml
- [ ] T086 [US5] Create Judge main entry point in backend/judge/src/main.py: FastAPI app with async workers, 4x per CPU core, health check endpoint
- [ ] T087 [US5] Create Judge configuration YAML in infrastructure/configs/judge.yaml: model_path, inference_timeout_ms, cache_ttl_seconds per plan.md

### Transparency Features (Frontend)

- [ ] T088 [P] [US5] Create score breakdown component in frontend/src/components/detections/ScoreBreakdown.tsx: show each evidence type's contribution (endpoint=11, network=3, judge=5) per US5 acceptance scenarios
- [ ] T089 [P] [US5] Create explanation panel in frontend/src/components/detections/ExplanationPanel.tsx: display Judge's plain-language reasoning, highlight key patterns
- [ ] T090 [US5] Create help documentation component in frontend/src/components/common/HelpTooltip.tsx: explain scoring thresholds (authorized ≤4, suspect 5-8, unauthorized ≥9) in plain language per US5 acceptance scenario 4
- [ ] T091 [US5] Update evidence display in frontend/src/components/detections/EvidenceTabs.tsx: show file paths (not full contents), snippets with SHA256 hashes, network packet counts without exposing payloads per FR-009

### Judge Availability Handling

- [ ] T092 [US5] Add Judge fallback logic to backend/correlator/pkg/scoring/algorithm.go: continue without Judge input if unavailable, set judge_available=false flag per FR-020a
- [ ] T093 [US5] Create Judge unavailable indicator in frontend/src/components/detections/DetectionBadge.tsx: show "judge_unavailable" badge when FR-020b flag is true
- [ ] T094 [US5] Create retrospective scoring service in backend/correlator/pkg/scoring/retrospective.go: re-score detections marked "judge_unavailable" when Judge recovers per FR-020c

**Checkpoint**: User Story 5 complete - Developers see clear evidence for why their MCP was flagged. Judge service classifies LLM requests <400ms, generates explanations. Test by triggering detection and verifying score breakdown + explanation are visible in UI.

---

## Phase 7: User Story 3 - Platform Engineer Registry Management (Priority: P3)

**Goal**: Enable platform engineers to approve/deny MCP registrations, monitor expirations, and maintain authorized inventory

**Independent Test**: Create pending registry entry as Developer, login as Admin, approve entry, verify it becomes active and future detections are matched

### Registry Management Endpoints

- [ ] T095 [US3] Implement PATCH /api/v1/mcps/{id} endpoint in backend/registry-api/src/api/registry.py: Admin updates approval_status (approve/deny), Developer updates purpose/expires_at per contracts/registry-api.yaml
- [ ] T096 [US3] Implement DELETE /api/v1/mcps/{id} endpoint in backend/registry-api/src/api/registry.py: Admin-only soft delete, mark as deleted in audit log per FR-021
- [ ] T097 [US3] Add approval workflow validation in backend/registry-api/src/services/registry_service.py: require Admin role for approval_status changes, validate expires_at ≤365 days

### Expiration Monitoring

- [ ] T098 [P] [US3] Create expiration checker cron job in backend/registry-api/src/cron/expiration_checker.py: daily check for entries expiring within 14 days, send notifications per FR-025
- [ ] T099 [US3] Create notification service in backend/registry-api/src/notifications/sender.py: support email, webhook (Slack/Teams/PagerDuty), in-app notifications per FR-025a
- [ ] T100 [US3] Implement GET /api/v1/users/me endpoint in backend/registry-api/src/api/users.py: retrieve user profile with notification_preferences per contracts/registry-api.yaml
- [ ] T101 [US3] Implement PATCH /api/v1/users/me endpoint in backend/registry-api/src/api/users.py: update notification preferences (channels, thresholds) per contracts/registry-api.yaml

### Registry Management UI

- [ ] T102 [P] [US3] Create registry list component in frontend/src/components/registry/RegistryList.tsx: display entries with approval status, expiration date, owner, filter by team/status
- [ ] T103 [P] [US3] Create approval action buttons in frontend/src/components/registry/ApprovalButtons.tsx: Admin-only approve/deny buttons with confirmation dialog
- [ ] T104 [US3] Create expiration reminder badge in frontend/src/components/registry/ExpirationBadge.tsx: highlight entries expiring within 14 days in orange
- [ ] T105 [US3] Create registry page in frontend/src/pages/Registry.tsx: list + detail + approval workflow per US3 acceptance scenarios
- [ ] T106 [US3] Create notification settings page in frontend/src/pages/Settings.tsx: configure email/webhook/in-app preferences, set detection_score_threshold per FR-025a

**Checkpoint**: User Story 3 complete - Platform engineers can approve/deny registrations, receive expiration reminders, manage lifecycle. Test by creating pending entry, approving as Admin, verifying renewal workflow.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories, deployment readiness, documentation

### Analytics and Dashboard

- [ ] T107 [P] Implement GET /api/v1/analytics/score-distribution endpoint in backend/registry-api/src/api/analytics.py: query ClickHouse aggregated_metrics for histogram per contracts/findings-api.yaml
- [ ] T108 [P] Implement GET /api/v1/analytics/trendlines endpoint in backend/registry-api/src/api/analytics.py: query aggregated_metrics with hour/day/week granularity, ≤2s response per SC-007
- [ ] T109 [P] Implement GET /api/v1/analytics/summary endpoint in backend/registry-api/src/api/analytics.py: dashboard summary with total detections, active hosts, classification breakdown per contracts/findings-api.yaml
- [ ] T110 [P] Create dashboard page in frontend/src/pages/Dashboard.tsx: score distribution chart, trendlines graph, summary cards per FR-012
- [ ] T111 [P] Create chart components in frontend/src/components/dashboard/ScoreDistributionChart.tsx: use Recharts for histogram visualization
- [ ] T112 [P] Create chart components in frontend/src/components/dashboard/TrendlineChart.tsx: time-series line chart with classification breakdown

### Performance Optimization

- [ ] T113 [P] Add ClickHouse query optimization in backend/registry-api/src/services/clickhouse_client.py: use skipping indexes on host_id_hash, leverage materialized views for aggregations
- [ ] T114 [P] Add connection pooling in backend/correlator/pkg/storage/clickhouse.go: reuse connections, batch inserts for high throughput per SC-008
- [ ] T115 [P] Add Judge model caching in backend/judge/src/inference/cache.py: Redis cache with TTL, fingerprint identical requests to reduce redundant inference
- [ ] T116 [P] Add frontend performance optimization in frontend/src/services/: implement SWR stale-while-revalidate, pagination for large detection lists

### Security Hardening

- [ ] T117 [P] Add input validation middleware in backend/registry-api/src/middleware/validation.py: sanitize all inputs, prevent SQL injection in ClickHouse queries
- [ ] T118 [P] Add rate limiting in backend/registry-api/src/middleware/rate_limit.py: 100 req/min per user, 1000 req/min per IP per best practices
- [ ] T119 [P] Add CORS configuration in backend/registry-api/src/main.py: restrict origins to frontend URL, secure cookies per FR-010
- [ ] T120 [P] Add webhook signature verification in backend/registry-api/src/notifications/webhook.py: HMAC-SHA256 signature for Slack/Teams webhooks per data-model.md

### Deployment and Operations

- [ ] T121 [P] Create Helm values file in infrastructure/helm/mcpeeker/values.yaml: resource limits, replica counts, environment variables per plan.md
- [ ] T122 [P] Create Kubernetes Deployment manifests in infrastructure/helm/mcpeeker/templates/: scanner, correlator, judge, registry-api with mTLS sidecar
- [ ] T123 [P] Create Kubernetes Service manifests in infrastructure/helm/mcpeeker/templates/: ClusterIP for internal services, LoadBalancer for frontend
- [ ] T124 [P] Create Kubernetes Ingress in infrastructure/helm/mcpeeker/templates/ingress.yaml: HTTPS termination, path routing to registry-api and frontend
- [ ] T125 [P] Create Prometheus ServiceMonitor in infrastructure/helm/mcpeeker/templates/servicemonitor.yaml: scrape metrics from all services per FR-014
- [ ] T126 [P] Add health check endpoints: GET /health in all services with ClickHouse/PostgreSQL/NATS connectivity checks per quickstart.md

### Documentation

- [ ] T127 [P] Validate quickstart.md instructions in specs/001-mcp-detection-platform/quickstart.md: run full local setup, verify all steps work
- [ ] T128 [P] Create API documentation in docs/api-reference.md: link to Swagger UI (http://localhost:8000/docs), document authentication flow
- [ ] T129 [P] Create architecture diagram in docs/architecture.md: show data flow from scanner → NATS → correlator → ClickHouse → UI
- [ ] T130 [P] Create deployment guide in docs/deployment.md: Kubernetes prerequisites, Helm install commands, cert-manager setup per research.md
- [ ] T131 [P] Create troubleshooting guide in docs/troubleshooting.md: common issues from quickstart.md troubleshooting section

### Final Integration

- [ ] T132 Create end-to-end integration test in tests/integration/test_e2e_detection_flow.py: scanner publishes event → correlator writes ClickHouse → UI displays detection → developer registers → status changes to authorized
- [ ] T133 Create end-to-end integration test in tests/integration/test_e2e_multi_layer_correlation.py: send endpoint+network+gateway events → verify combined score and classification
- [ ] T134 Run security scans: Gosec on Go code, Bandit on Python code, Trivy on Docker images, verify no HIGH vulnerabilities per plan.md
- [ ] T135 Run performance load test using Vegeta in tests/performance/: 100M events/month sustained load (40 events/sec), verify ≤60s detection latency per FR-011 and SC-008
- [ ] T136 Verify constitution compliance: check all FR requirements, NFRs, success criteria are met per plan.md constitution check section

**Checkpoint**: All features complete, tested, documented, ready for deployment. Platform supports 10k endpoints, 100M events/month, 99.5% uptime per plan.md scale/scope.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - **BLOCKS all user stories**
- **User Stories (Phase 3-7)**:
  - **US1 (Phase 3)**: Depends on Foundational (Phase 2) - scanner + registry API + UI
  - **US4 (Phase 4)**: Depends on Foundational (Phase 2) - signature engine + correlator + network monitoring
  - **US2 (Phase 5)**: Depends on US1 (detection data exists) and US4 (correlation working) - findings API + feedback
  - **US5 (Phase 6)**: Depends on US4 (correlation working) - Judge service adds explanations
  - **US3 (Phase 7)**: Depends on US1 (registry exists) - admin approval workflows
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 + US4 (P1 stories)**: Can start in parallel after Foundational phase - US1 focuses on endpoint detection + registration, US4 focuses on correlation
- **US2 (P2)**: Requires US1 (detection data) and US4 (correlation working) to provide investigation functionality
- **US5 (P2)**: Can start in parallel with US2 after US4 completes - adds Judge service and transparency features
- **US3 (P3)**: Requires US1 (registry exists) to add approval workflows - can be done last

### Within Each User Story

1. Models and schemas first (database tables, API contracts)
2. Core services second (scanner, correlator, judge logic)
3. API endpoints third (REST endpoints, NATS publishers)
4. Frontend components last (UI for user interaction)

### Parallel Opportunities

**Within Setup (Phase 1)**:
- T002-T011 can all run in parallel (different projects, independent initialization)

**Within Foundational (Phase 2)**:
- T016-T021 (utilities), T030-T034 (metrics) can run in parallel
- T026-T029 (mTLS) can run in parallel

**Between User Stories**:
- After Foundational completes:
  - Developer A: US1 (T035-T052) - Endpoint detection + registration
  - Developer B: US4 (T053-T068) - Correlation + scoring
  - Once US1+US4 done:
    - Developer C: US2 (T069-T080) - Investigation
    - Developer D: US5 (T081-T094) - Transparency

**Within Polish (Phase 8)**:
- T107-T112 (analytics), T113-T116 (performance), T117-T120 (security), T121-T126 (deployment), T127-T131 (docs) can all run in parallel

---

## Implementation Strategy

### MVP First (P1 User Stories Only)

1. Complete Phase 1: Setup (T001-T011)
2. Complete Phase 2: Foundational (T012-T034) - **CRITICAL BLOCKER**
3. Complete Phase 3: US1 - Detection + Registration (T035-T052)
4. Complete Phase 4: US4 - Multi-Layer Correlation (T053-T068)
5. **STOP and VALIDATE**: Test US1 + US4 independently
6. Deploy/demo MVP with core detection and correlation working

### Incremental Delivery

1. Setup + Foundational → Foundation ready (infrastructure deployed)
2. Add US1 → Test independently → Developers can see detections and self-register (MVP!)
3. Add US4 → Test independently → Multi-layer correlation reduces false positives
4. Add US2 → Test independently → Analysts can investigate and provide feedback
5. Add US5 → Test independently → Developers understand why their MCP was flagged
6. Add US3 → Test independently → Platform engineers manage registry lifecycle
7. Polish → Production-ready with analytics, performance, security hardening

### Parallel Team Strategy

With 4 developers after Foundational phase completes:

- **Developer A**: US1 (detection + registration) - T035-T052
- **Developer B**: US4 (correlation + scoring) - T053-T068
- **Developer C**: US2 (investigation + feedback) after US1+US4 - T069-T080
- **Developer D**: US5 (Judge + transparency) after US4 - T081-T094

Then all developers collaborate on US3 and Polish phase.

---

## Notes

- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[US#] labels**: Map task to specific user story for traceability
- **Each user story independently testable**: Validate after each phase completion
- **No test tasks**: Spec does not explicitly request tests - focus on implementation
- **File paths**: All paths absolute from repository root per requirements
- **Constitution compliance**: All tasks reference FR/SC requirements from spec.md
- **Avoid**: Vague tasks, same file conflicts, cross-story dependencies that break independence
- **Commit strategy**: Commit after each task or logical group for rollback safety
- **Stop at checkpoints**: Validate each user story works independently before proceeding
