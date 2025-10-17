<!--
Sync Impact Report
==================
Version Change: none → 1.0.0
Rationale: Initial constitution ratification for MCPeeker project

Modified Principles:
- NEW: Security-First Detection (enterprise security focus)
- NEW: Multi-Layer Correlation (endpoint, network, gateway signals)
- NEW: Privacy by Design (no sensitive data retention)
- NEW: YAML Configuration (operational simplicity)
- NEW: Observability & Transparency (developer trust)

Added Sections:
- Core Principles (5 principles)
- Non-Functional Requirements (NFRs matching PRD)
- Development & Testing Standards (matching technical spec)
- Governance (amendment process)

Removed Sections: None (initial creation)

Templates Requiring Updates:
✅ plan-template.md - Constitution Check section already present, generic enough
✅ spec-template.md - Requirements and success criteria align with constitution
✅ tasks-template.md - Test-first guidance aligns with security testing principle
⚠️ Note: Templates are generic and flexible enough to accommodate MCPeeker principles

Follow-up TODOs: None - all fields completed
-->

# MCPeeker Constitution

## Core Principles

### I. Security-First Detection

Every detection mechanism (endpoint scanner, network IDS, LLM Judge) MUST operate
under the principle of minimized false positives while maximizing coverage.
Detection MUST NOT disrupt developer workflows but MUST surface unauthorized
MCP instances with actionable evidence. All signals are presumed innocent until
correlation reaches threshold score (≥9).

**Rationale**: Enterprise adoption depends on trust. High false-positive rates
erode confidence and create alert fatigue. Multi-layer correlation ensures
accuracy before escalation.

### II. Multi-Layer Correlation

MCP detection MUST combine at least two signal types: endpoint (file/process),
network (Zeek/Suricata), or gateway (LLM Judge). Single-source detections remain
in "suspect" classification until corroborated. Scoring algorithm weights
endpoint=highest, judge=medium, network=supporting.

**Rationale**: MCP shares patterns with legitimate JSON-RPC protocols.
Single-layer detection yields excessive false positives. Correlation provides
confidence and context for incident response.

### III. Privacy by Design (NON-NEGOTIABLE)

The system MUST NOT retain raw LLM prompts, user conversations, or sensitive
file contents beyond minimal snippets (≤1KB) required for classification.
All host identifiers MUST be hashed before storage. mTLS MUST be enforced for
all inter-service communication. Audit logs MUST be signed and retained for
90 days minimum.

**Rationale**: Privacy violations destroy enterprise trust and violate
regulatory compliance (GDPR, CCPA, SOC 2). Security tools must model the
behavior they enforce.

### IV. YAML Configuration

All component behavior, detection rules, thresholds, and integrations MUST be
declarative via YAML configuration files validated against JSON Schema.
Runtime overrides via Hydra are permitted for experimental Judge tuning only.
No hardcoded policies in application code.

**Rationale**: YAML provides transparency, version control, and change auditing.
Security policies must be reviewable by non-engineers and deployable via GitOps.

### V. Observability & Transparency

Every detection event MUST be explainable: which signals triggered, scores
assigned, and evidence collected. UI MUST display raw evidence (anonymized)
for analyst review. Prometheus metrics MUST expose false-positive rates,
detection latency, and Judge accuracy. Developers MUST see why their MCP was
flagged and have one-click registration workflow.

**Rationale**: Blackbox detection systems fail in enterprise environments.
Transparency builds trust with developers and enables continuous improvement
of detection rules and Judge models.

## Non-Functional Requirements (NFRs)

These requirements are derived from the MCPeeker PRD and are binding for all
implementation decisions:

| Category          | Requirement                                                                 |
| ----------------- | --------------------------------------------------------------------------- |
| **Performance**   | Detection pipeline latency ≤60s end-to-end; LLM Judge latency ≤400ms       |
| **Scalability**   | Support 10,000 endpoints; 100M events/month; ClickHouse optimized for OLAP |
| **Availability**  | 99.5% uptime SLA; autoscaling per service; NATS JetStream fault tolerance  |
| **Security**      | mTLS everywhere; CA rotation every 90 days; no raw prompt storage          |
| **Privacy**       | Host ID hashing; endpoint snippets ≤1KB; anonymized storage                |
| **Deployability** | Docker + Helm; YAML configs per environment; zero-downtime upgrades        |
| **Extensibility** | Plugin SDK for custom rules; Judge model swappable via config              |
| **Observability** | Prometheus metrics; Grafana dashboards; OpenTelemetry tracing (optional)   |

## Development & Testing Standards

### Contract Testing (MANDATORY for Phase 2+)

All service APIs (Registry, Findings, Config) MUST have contract tests verifying:
- Request/response schema adherence (JSON Schema validation)
- Error codes and messages match specification
- Backward compatibility on MINOR version bumps

Contract tests MUST run in CI before deployment.

### Integration Testing (MANDATORY for Multi-Layer Features)

Any feature involving 2+ services (e.g., Scanner → Signature Engine → Correlator)
MUST have integration tests covering:
- End-to-end event flow from source to ClickHouse
- Scoring algorithm accuracy against known-good test cases
- Registry matching behavior for authorized vs. unauthorized MCPs

Integration tests MUST run in Docker Compose with ephemeral NATS/ClickHouse/Postgres.

### Security Testing (MANDATORY for All Releases)

Before production deployment:
- Run Gosec (Go) / Bandit (Python) static analysis
- Verify no secrets in container images (via Trivy scan)
- Validate mTLS certificate rotation works
- Test audit log integrity (signature verification)

### Performance Testing (MANDATORY for Major Releases)

Before MAJOR version releases, run load tests simulating:
- 10,000 concurrent endpoints scanning every 12 hours
- 1M events/day ingestion burst
- Judge service handling 100 req/s
- ClickHouse query latency for dashboard ≤2s

## Governance

### Amendment Process

1. Proposed changes MUST be documented in a Git branch with rationale
2. Constitution version MUST be bumped per semantic versioning:
   - **MAJOR**: Principle removal, redefinition, or incompatible NFR change
   - **MINOR**: New principle/section added or materially expanded guidance
   - **PATCH**: Clarifications, wording, typo fixes, non-semantic refinements
3. All dependent templates (plan, spec, tasks, commands) MUST be reviewed for consistency
4. Amendment MUST be approved by project maintainers before merge

### Compliance Review

All pull requests MUST verify compliance with:
- Privacy by Design: No sensitive data retention
- Multi-Layer Correlation: New detections combine ≥2 signal types
- YAML Configuration: No hardcoded policies
- Observability: New features include Prometheus metrics

Complex features requiring pattern violations (e.g., Repository pattern,
additional services beyond architecture diagram) MUST be justified in
`plan.md` Complexity Tracking section.

### Migration Policy

When constitutional principles change:
1. Existing code has 90 days to comply (grace period for MAJOR changes)
2. New code MUST comply immediately
3. Migration guide MUST be provided in `docs/migrations/`

**Version**: 1.0.0 | **Ratified**: 2025-10-16 | **Last Amended**: 2025-10-16