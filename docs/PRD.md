# MCPeeker — Product Requirements Document v5 (Handoff-Ready)

**Status:** Approved for engineering implementation
**Audience:** Security engineering, MLOps, platform, and UI teams

---

## 1. Executive Summary

### Problem

Large organizations increasingly deploy **Model Context Protocol (MCP)** servers for LLMs, tools, and plugins. Developers often spin up *unauthorized* MCP instances (locally or in the cloud) to connect custom tools, test prompts, or bypass gateway restrictions.
This creates blind spots that threaten:

* **Data governance** — potential exposure of internal context to unvetted MCP endpoints.
* **Regulatory compliance** — loss of visibility into AI data movement.
* **Operational integrity** — unmanaged or “pirated” MCPs can misbehave or exfiltrate data.

### Opportunity

**MCPeeker** provides unified visibility into all MCP activity across the enterprise.
It detects, classifies, and correlates signals from:

* **Endpoints** (local config, manifests, processes)
* **Network** (Zeek/Suricata signatures)
* **LLM Gateway** (real-time request inspection + LLM Judge)

### Goal

Enable organizations to **discover and manage every MCP server**—authorized or not—without disrupting developers.

---

## 2. Target Users

| User                        | Description                         | Primary Goals                                 |
| --------------------------- | ----------------------------------- | --------------------------------------------- |
| **Security Engineer (SOC)** | Monitors detections and risk levels | Investigate unauthorized MCPs                 |
| **Platform Engineer**       | Owns AI gateway & infrastructure    | Maintain authorized MCP registry              |
| **Developer**               | Runs local MCPs for testing         | Transparently register/confirm MCP            |
| **MLOps / Research**        | Tunes LLM Judge                     | Improve semantic classification               |
| **Product Manager**         | Oversees visibility program         | Track adoption, false positives, and coverage |

---

## 3. Product Vision

> “One pane of glass to observe, validate, and classify every MCP interaction — from localhost manifests to cloud-deployed tool servers — blending signature-based and semantic analysis.”

---

## 4. Core Objectives

1. **Detect** all MCP servers and clients (known and unknown).
2. **Correlate** endpoint, network, and gateway signals.
3. **Classify** each instance as Authorized / Unauthorized / Unknown.
4. **Enable registration workflows** via a clean UI, not CLI.
5. **Support developer autonomy** — transparency, not enforcement.
6. **Operate securely** — no sensitive data retention, mTLS, hashed identifiers.

---

## 5. Non-Functional Requirements (NFRs)

| Category          | Requirement                                                  |
| ----------------- | ------------------------------------------------------------ |
| **Performance**   | Detection latency ≤ 60 s; Judge latency ≤ 400 ms per request |
| **Scalability**   | 10 k endpoints, 100 M events/month                           |
| **Availability**  | 99.5 % uptime; autoscaling per service                       |
| **Security**      | mTLS, CA rotation every 90 days, no raw prompt storage       |
| **Privacy**       | Endpoint snippets ≤ 1 KB; anonymized host IDs                |
| **Deployability** | Docker + Helm; YAML configs per env                          |
| **Extensibility** | Plugins for new rule types or Judge models                   |
| **Observability** | Prometheus metrics; Grafana dashboards                       |

---

## 6. Key User Flows

### 6.1 Unauthorized MCP Detection

1. **Endpoint scanner** (Go agent) finds `manifest.json` in `/Users/dev/.vscode/`.
2. Sends event → `endpoint.events` subject (NATS).
3. **Signature Engine** matches known MCP patterns (`"jsonrpc": "2.0"`, `/mcp/sse`).
4. **Correlator** checks registry — no entry found.
5. **Judge Service** labels “Likely MCP” (score +5).
6. Score ≥ 9 → Incident created in ClickHouse.
7. UI shows card: *“Unregistered MCP detected on dev-laptop.”*
8. Dev clicks *Confirm ownership* → fills purpose → auto-registers.

---

### 6.2 Authorized MCP Lifecycle

1. Dev registers MCP via UI → adds host, port, purpose, TTL.
2. Registry entry stored in PostgreSQL.
3. Future detections auto-matched → risk score lowered.
4. 90-day expiry reminder sent → renew or archive.

---

### 6.3 SOC Investigation

1. Analyst opens “Findings” dashboard.
2. Filters by score > 10 + unregistered.
3. Opens evidence: endpoint file, Zeek log, Judge label.
4. Marks True Positive → feedback used for Judge re-tuning.

---

## 7. Architecture Overview

```
[Go Scanner]──┐
[Zeek/Suricata]──┼──► Signature Engine → Correlator
[Gateway Tap]───┘                │
                                 ▼
                           [LLM Judge]
                                 ▼
                          [ClickHouse + UI]
                                 │
                             [Registry API]
```

* **Event Bus:** NATS JetStream (reliable queue).
* **Storage:** ClickHouse (analytics) + PostgreSQL (Registry/RBAC).
* **UI:** React SPA served via FastAPI gateway.

---

## 8. Configuration & Extensibility

* **Format:** YAML (validated via JSON Schema).
* **Overrides:** Hydra for Judge experiments.
* **Repo Layout:**

  ```
  configs/
    global.yaml
    pipeline.yaml
    judge.yaml
    scanner_go.yaml
    zeek_suricata.yaml
    registry.yaml
  ```

Example `judge.yaml`:

```yaml
judge:
  mode: hybrid
  online:
    model: local:distilled-mcp
    timeout_ms: 300
  batch:
    poll_interval_s: 300
  sampling:
    default: 0.01
    high_risk: 0.25
```

---

## 9. Components

| Component             | Tech                 | Description                                                  |
| --------------------- | -------------------- | ------------------------------------------------------------ |
| **Go Scanner**        | Go 1.23              | Scans file system, processes, ports; sends `endpoint.events` |
| **Zeek + Suricata**   | C++/Lua              | Network fingerprints (SSE, JSON-RPC, MCP headers)            |
| **Signature Engine**  | Python/Go            | Parses raw events; applies Knostik rules                     |
| **LLM Judge Service** | Python + Hydra       | Semantic classification; online/batch modes                  |
| **Correlator**        | Go                   | Merges signals + scoring                                     |
| **Registry API**      | FastAPI + PostgreSQL | Authorized MCP entries + RBAC                                |
| **UI Portal**         | React + Tailwind     | Dashboards, registry, detections, settings                   |
| **Event Bus**         | NATS JetStream       | Unified event transport                                      |
| **Storage**           | ClickHouse           | Findings & time-series data                                  |

---

## 10. MDM Integration (Phase 2)

* **Purpose:** trigger Go scanner via Intune/Jamf for non-osquery devices.
* **Integration:** MDM executes scanner binary → uploads JSON to collector.
* **Effort:** 6–10 weeks post-MVP.
* **Fallback:** manual enrollment or EDR API hook.

---

## 11. Roles & Ownership

| Domain                  | Owner Role             | Key Deliverable             |
| ----------------------- | ---------------------- | --------------------------- |
| Endpoint Scanner        | Security Engineer (Go) | Agent binary + configs      |
| Network Detection       | SOC/Infra              | Zeek + Suricata deployments |
| Correlator + NATS Infra | Platform Engineer      | Event pipeline SLA          |
| LLM Judge               | MLOps Engineer         | Model + accuracy monitoring |
| UI Portal + Registry    | Frontend + PM          | React app + API             |
| Config Schemas          | DevOps                 | Validation & Helm charts    |

---

## 12. Data Schema Appendix

**endpoint.events**

```json
{
  "host_id": "host-123",
  "timestamp": "2025-10-16T12:00:00Z",
  "evidence": [
    {"type": "file", "path": "~/.vscode/mcp.json", "sha256": "...", "score": 5},
    {"type": "process", "cmd": "python -m mcp_server", "score": 6}
  ],
  "local_score": 11
}
```

**network.events**

```json
{
  "src_ip": "10.1.2.4",
  "dst_ip": "3.120.230.6",
  "method": "POST",
  "path": "/mcp",
  "content": "\"jsonrpc\": \"2.0\"",
  "score": 3
}
```

**mcp.findings**

```json
{
  "id": "uuid",
  "host": "host-123",
  "correlated_score": 12,
  "classification": "unauthorized",
  "judge_label": "Likely_MCP",
  "registry_match": false,
  "timestamp": "2025-10-16T12:00:10Z"
}
```

---

## 13. UI Overview

**Sections**

1. **Dashboard** — Active MCPs, score distribution, trendlines.
2. **Detections Feed** — live stream of new findings.
3. **Registry** — authorized MCP records + auto-suggested entries.
4. **Devices** — endpoint status + scanner health.
5. **Settings** — YAML preview, judge modes, MDM connectors.

**Example Screen Flow**

```
[Dashboard] → click “Unregistered MCP (score 12)” →
[Investigation Panel] → evidence tabs (endpoint/network/judge) →
[Action] Confirm Ownership → auto-register + lower score.
```

---

## 14. Deployment & Rollout Plan

| Phase            | Duration | Deliverables                         |
| ---------------- | -------- | ------------------------------------ |
| **0 Bootstrap**  | 2 wks    | NATS + ClickHouse + repo setup       |
| **1 MVP**        | 6 wks    | Go scanner, Zeek/Suricata, basic UI  |
| **2 Pilot**      | 6 wks    | Judge hybrid mode, Registry workflow |
| **3 v1 Release** | 8 wks    | Full portal, RBAC, MDM PoC, docs     |

---

## 15. Security & Privacy Assurances

* mTLS everywhere.
* Hash host IDs before storage.
* No prompt or sensitive text retention.
* Configs read-only in prod; audited changes.
* Audit trail signed and retained 90 days.

---

## 16. KPIs / Success Metrics

| Metric                   | Target                   |
| ------------------------ | ------------------------ |
| Detection Latency        | ≤ 60 s                   |
| False Positive Rate      | ≤ 10 %                   |
| Endpoint Coverage        | ≥ 80 % after MDM rollout |
| Rule Update Cycle        | ≤ 14 days                |
| UI Uptime                | ≥ 99.5 %                 |
| Community Adoption (OSS) | 1 000 stars / 6 mo       |

---

## 17. Glossary

| Term                   | Definition                                                        |
| ---------------------- | ----------------------------------------------------------------- |
| **MCP**                | Model Context Protocol — standardized interface for LLM tooling.  |
| **LLM Judge**          | Semantic classifier (decides if traffic represents MCP behavior). |
| **Knostik Signatures** | Community JSON patterns identifying MCP protocol artifacts.       |
| **Zeek / Suricata**    | Open-source network IDS engines for signature matching.           |
| **NATS JetStream**     | High-throughput message bus for events.                           |
| **ClickHouse**         | Columnar DB for analytics and time-series storage.                |

---

## 18. Risks & Mitigations

| Risk                                 | Impact | Mitigation                                  |
| ------------------------------------ | ------ | ------------------------------------------- |
| False positives from JSONRPC overlap | Medium | Combine multi-layer signals + Judge score   |
| MDM integration complexity           | High   | Phase 2 rollout with vendor APIs            |
| Judge latency impact on gateway      | Medium | Async batch fallback + timeout guard        |
| Developer privacy concerns           | Medium | Transparency UI + no prompt storage         |
| Adoption fatigue                     | Low    | Opt-in onboarding + auto-suggested registry |

---

## 19. Roadmap Summary

| Release | Focus         | Key Additions                |
| ------- | ------------- | ---------------------------- |
| v0.1    | MVP           | Core pipeline + YAML configs |
| v0.2    | Pilot         | Hybrid Judge + Registry      |
| v0.3    | Enterprise    | MDM connectors + RBAC        |
| v0.4    | OSS Community | Public rulesets + plugin SDK |

---

## 20. Appendix: Example Detection Lifecycle

```
1. Go scanner detects manifest.json on macOS.
2. Zeek sees SSE traffic to port 8080.
3. Gateway Judge labels “Likely MCP”.
4. Correlator combines signals (score 12).
5. UI shows incident card → analyst confirms → registry updated.
```