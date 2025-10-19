# MCPeeker Scoring Examples - Visual Guide

## Scoring Weights Reference

```
┌─────────────────────────────────────────────────────┐
│  Detection Layer          Weight    Reliability     │
├─────────────────────────────────────────────────────┤
│  📁 Endpoint (file/proc)    +11     ████████ High   │
│  🤖 Judge (LLM)             +0-5    ██████ Medium   │
│  🌐 Network (IDS)           +3      ████ Lower      │
│  ✅ Registry (whitelist)    -6      ████████ Trust  │
└─────────────────────────────────────────────────────┘

Classification Thresholds:
  0────4────5────────8────9──────────→
  └─────┘   └─────────┘   └──────────→
  AUTHORIZED  SUSPECT    UNAUTHORIZED
  (Green ✅)  (Yellow ⚠️)  (Red 🚨)
```

## Example 1: Official Anthropic Filesystem Server

```
📋 Detection Details:
  Host: devmachine-001
  Time: 2025-01-15 14:23:10 UTC

📁 Endpoint Evidence:
  ✓ File: ~/.config/claude-desktop/mcp-servers/filesystem/manifest.json
  ✓ Content: {
      "name": "@modelcontextprotocol/server-filesystem",
      "vendor": "anthropic",
      "version": "0.1.0",
      "tools": ["read_file", "write_file", "list_directory"]
    }
  ✓ Process: node /usr/local/lib/node_modules/@modelcontextprotocol/server-filesystem/index.js
  ✓ Port: 3000
  Score contribution: +11

🌐 Network Evidence:
  ✓ Traffic on localhost:3000
  ✓ JSON-RPC pattern: {"jsonrpc":"2.0","method":"initialize"}
  Score contribution: +3

🤖 Judge Analysis:
  ✓ Classification: AUTHORIZED
  ✓ Confidence: 95%
  ✓ Reasoning: "Official Anthropic MCP server, standard installation path,
                legitimate filesystem operations tools"
  ✓ Detected MCP: @modelcontextprotocol/server-filesystem (v0.1.0)
  ✓ Risk factors: None
  Score contribution: +0 (authorized = no points)

✅ Registry Check:
  ✓ MATCHED in registry
  ✓ Registered by: devops@company.com
  ✓ Justification: "Standard developer tooling for AI-assisted coding"
  ✓ Status: APPROVED
  Score contribution: -6

📊 Final Score Calculation:
  ┌──────────────┬─────────┐
  │ Layer        │ Points  │
  ├──────────────┼─────────┤
  │ Endpoint     │ +11     │
  │ Network      │ +3      │
  │ Judge        │ +0      │
  │ Registry     │ -6      │
  ├──────────────┼─────────┤
  │ TOTAL        │ 8       │
  └──────────────┴─────────┘

  Classification: SUSPECT (score 8, threshold ≤8)
  
  ⚠️ Note: Even though in registry, score is 8 (borderline).
           To fully authorize, registry penalty should be -11
           or increase to "highly trusted" status.

🎯 Recommended Action: ALLOW (in registry)
   Analyst Action: None required
```

---

## Example 2: Malicious Data Exfiltration MCP

```
📋 Detection Details:
  Host: webserver-prod-07
  Time: 2025-01-15 03:47:22 UTC  ⚠️ (off-hours)

📁 Endpoint Evidence:
  ✓ File: /tmp/.hidden/.sys/mcp_bridge.json
  ✓ Content: {
      "name": "system-bridge",
      "version": "1.0.0",
      "tools": ["execute_command", "read_file", "upload_data"]
    }
  ✓ Process: /tmp/.x11/./sbr --port 9999 --bind 0.0.0.0
  ✓ Binary hash: <unknown - deleted after execution>
  ✓ Running as: root  ⚠️
  Score contribution: +11

🌐 Network Evidence:
  ✓ Traffic on 0.0.0.0:9999  ⚠️ (not localhost!)
  ✓ External connection to 185.234.x.x:443
  ✓ Encrypted payload, but JSON-RPC structure detected
  ✓ Data exfiltration patterns (large outbound transfers)
  Score contribution: +3

🤖 Judge Analysis:
  ✓ Classification: UNAUTHORIZED
  ✓ Confidence: 98%
  ✓ Reasoning: "Extremely suspicious - hidden path, obfuscated process name,
                running as root, listening on all interfaces, external connections,
                tools include dangerous 'execute_command', off-hours execution"
  ✓ Detected MCP: Unknown/Custom
  ✓ Risk factors:
    - Hidden installation path (/tmp/.hidden)
    - High-privilege port (9999)
    - Root execution
    - External network binding
    - Command execution capability
    - Off-hours activity
  Score contribution: +5 (unauthorized = max points)

✅ Registry Check:
  ✗ NOT in registry
  Score contribution: +0

📊 Final Score Calculation:
  ┌──────────────┬─────────┐
  │ Layer        │ Points  │
  ├──────────────┼─────────┤
  │ Endpoint     │ +11     │
  │ Network      │ +3      │
  │ Judge        │ +5      │
  │ Registry     │ +0      │
  ├──────────────┼─────────┤
  │ TOTAL        │ 19      │
  └──────────────┴─────────┘

  Classification: UNAUTHORIZED 🚨 (score 19, threshold ≥9)

🎯 Recommended Action: BLOCK + INVESTIGATE
   Priority: CRITICAL
   Analyst Action: Immediate incident response
   
   Suggested Steps:
   1. Isolate host from network
   2. Kill process (PID from detection)
   3. Preserve /tmp/.hidden/ for forensics
   4. Check other hosts for IoC
   5. Review firewall logs for 185.234.x.x
```

---

## Example 3: Developer's Custom MCP Server

```
📋 Detection Details:
  Host: dev-laptop-alice
  Time: 2025-01-15 16:42:55 UTC

📁 Endpoint Evidence:
  ✓ File: /Users/alice/projects/my-postgres-mcp/manifest.json
  ✓ Content: {
      "name": "custom-postgres-helper",
      "version": "0.0.1",
      "description": "Internal MCP for querying analytics DB",
      "tools": ["query_db", "get_schema"]
    }
  ✓ Process: python3 server.py --mcp --db prod-analytics
  ✓ Port: 3042
  Score contribution: +11

🤖 Judge Analysis:
  ✓ Classification: SUSPECT
  ✓ Confidence: 75%
  ✓ Reasoning: "Custom development MCP server, accessing production database,
                legitimate development path but needs approval for prod access"
  ✓ Detected MCP: custom-postgres-helper (custom)
  ✓ Risk factors:
    - Production database access
    - Unregistered/unknown server
    - Custom code (not official)
  Score contribution: +3 (suspect = medium points)

✅ Registry Check:
  ✗ NOT in registry
  Score contribution: +0

📊 Final Score Calculation:
  ┌──────────────┬─────────┐
  │ Layer        │ Points  │
  ├──────────────┼─────────┤
  │ Endpoint     │ +11     │
  │ Judge        │ +3      │
  ├──────────────┼─────────┤
  │ TOTAL        │ 14      │
  └──────────────┴─────────┘

  Classification: UNAUTHORIZED (score 14, threshold ≥9)

🎯 Recommended Action: INVESTIGATE
   Priority: MEDIUM
   Analyst Action: Contact developer for registration
   
   Next Steps:
   1. Reach out to Alice (developer)
   2. Request business justification
   3. Review database access patterns
   4. If legitimate, add to registry with approval workflow
   5. Re-scan after registration (score will drop to ~8)
```

---

## Example 4: MCP Server After Registration

**Same as Example 3, but after Alice registers it:**

```
📊 Final Score Calculation (AFTER Registration):
  ┌──────────────┬─────────┐
  │ Layer        │ Points  │
  ├──────────────┼─────────┤
  │ Endpoint     │ +11     │
  │ Judge        │ +3      │
  │ Registry     │ -6  ⬅── NEW!
  ├──────────────┼─────────┤
  │ TOTAL        │ 8       │
  └──────────────┴─────────┘

  Classification: SUSPECT (score 8, threshold ≤8)

  Registry Entry:
    Registered by: alice@company.com
    Approved by: security-team@company.com
    Justification: "Analytics MCP for BI dashboards, read-only access"
    Expiration: 2025-07-15 (6 months)
    Auto-approve similar: Yes

🎯 Recommended Action: ALLOW
   Analyst Action: None (automatically approved)
```

---

## Score Evolution Over Time

```
Timeline: Detection → Registration → Approval

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  T+0min: Initial Detection                             │
│  Score: 14 → UNAUTHORIZED                              │
│  ├─ Endpoint: +11                                      │
│  ├─ Judge: +3                                          │
│  └─ Registry: +0 (not registered)                      │
│                                                         │
│  ↓ Developer submits registration request              │
│                                                         │
│  T+15min: Pending Approval                             │
│  Score: 14 → UNAUTHORIZED (unchanged)                  │
│  Registry Status: PENDING                              │
│                                                         │
│  ↓ Security team approves                              │
│                                                         │
│  T+2h: Approved                                        │
│  Score: 8 → SUSPECT                                    │
│  ├─ Endpoint: +11                                      │
│  ├─ Judge: +3                                          │
│  └─ Registry: -6 (approved!)                           │
│                                                         │
│  ↓ Correlator re-scans (12h later)                     │
│                                                         │
│  T+12h: Re-evaluated                                   │
│  Score: 8 → SUSPECT (stable)                           │
│  Alerts: None (below UNAUTHORIZED threshold)           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## What-If Scenarios

### Scenario A: What if we didn't have scoring?

```
WITHOUT SCORING:
  Detection 1: Anthropic filesystem server → ALERT
  Detection 2: Malicious exfiltration tool → ALERT
  Detection 3: Developer's custom server → ALERT
  
  Analyst sees: 3 identical alerts
  Problem: Can't prioritize, wastes time on false positives

WITH SCORING:
  Detection 1: Score 8 (SUSPECT) → Auto-allowed (in registry)
  Detection 2: Score 19 (UNAUTHORIZED) → CRITICAL ALERT
  Detection 3: Score 14 (UNAUTHORIZED) → Investigate
  
  Analyst sees: 1 critical, 1 medium, 0 noise
  Result: Catches real threat, ignores known-good
```

### Scenario B: What if we only used endpoint detection?

```
ENDPOINT ONLY (no network, no judge, no registry):
  Score = 11 for EVERYTHING
  Problem: All detections look the same
  
  Malicious server: 11 points
  Official Anthropic: 11 points
  Dev server: 11 points
  
  Can't distinguish threat from legitimate!

MULTI-LAYER WITH SCORING:
  Malicious: 19 points (endpoint + network + judge = very suspicious)
  Anthropic: 8 points (endpoint + network + judge - registry = borderline)
  Dev server: 14 points (endpoint + judge = needs review)
  
  Clear differentiation!
```

### Scenario C: Registry impact

```
Server Type: Custom Analytics MCP

WITHOUT REGISTRY:
  Endpoint: +11
  Judge: +3
  Total: 14 → UNAUTHORIZED
  Result: Alert every 12 hours, forever

WITH REGISTRY:
  First detection:
    Endpoint: +11
    Judge: +3
    Total: 14 → UNAUTHORIZED → Developer registers
  
  After approval:
    Endpoint: +11
    Judge: +3
    Registry: -6
    Total: 8 → SUSPECT → No more alerts
  
  Benefit: One-time registration, permanent whitelist
```

---

## Edge Cases

### Edge Case 1: Judge Offline

```
When Judge service is unavailable:

Detection:
  Endpoint: +11
  Network: +3
  Judge: (unavailable, defaults to 0)
  Registry: +0
  Total: 14 → UNAUTHORIZED

Impact: More conservative classification (better safe than sorry)
```

### Edge Case 2: Only Network Detection

```
Scenario: Process exits before file scan, only network saw it

Detection:
  Network: +3
  Total: 3 → AUTHORIZED

Impact: Low score, likely missed
Solution: Correlator waits 5 minutes for additional evidence
```

### Edge Case 3: Conflicting Evidence

```
Scenario: Judge says AUTHORIZED but no registry match

Detection:
  Endpoint: +11
  Judge: +0 (says authorized)
  Registry: +0 (not in registry)
  Total: 11 → UNAUTHORIZED

Analyst sees:
  "Judge classified as AUTHORIZED but not in registry"
  Recommended action: Add to registry
```

---

## Tuning Guide

### Too Many False Positives?

**Symptom**: Legitimate dev servers constantly trigger alerts

**Fix 1**: Lower endpoint weight
```yaml
scoring:
  weights:
    endpoint: 9  # Was 11
```
Effect: Authorized + Registry = 9 - 6 = 3 (authorized)

**Fix 2**: Increase authorized threshold
```yaml
scoring:
  thresholds:
    authorized_max: 6  # Was 4
```
Effect: More detections auto-classified as authorized

**Fix 3**: Stronger registry penalty
```yaml
scoring:
  weights:
    registry: -8  # Was -6
```
Effect: Registered servers drop from 8 → 6 (authorized)

### Too Many False Negatives?

**Symptom**: Real threats not being caught

**Fix 1**: Increase network weight
```yaml
scoring:
  weights:
    network: 5  # Was 3
```
Effect: External connections weighted more heavily

**Fix 2**: Lower unauthorized threshold
```yaml
scoring:
  thresholds:
    suspect_max: 6  # Was 8
```
Effect: More detections classified as unauthorized

**Fix 3**: Increase judge weight for unauthorized
```python
# In classifier.py
if classification == "unauthorized":
    return 7  # Was 5
```
Effect: Judge has more influence on final score


---

## Registry Penalty Weight Adjustment Examples (T051-T052)

### Example: Registry Penalty -6 to -12 Adjustment

**Scenario:** Platform engineer wants to make registry match more obvious in scoring.

**Before (Default -6):**
```yaml
scoring:
  weights:
    endpoint: 11
    registry: -6  # Current default
```

**Detection Calculation:**
```
Endpoint signal:     +11
Registry penalty:    -6
Total Score:         5
Classification:      authorized (forced by registry match)
```

**After (Adjusted to -12):**
```yaml
scoring:
  weights:
    endpoint: 11
    registry: -12  # Increased penalty
```

**Detection Calculation:**
```
Endpoint signal:     +11
Registry penalty:    -12
Total Score:         -1 → 0 (floored)
Classification:      authorized (forced by registry match)
```

**Key Insight:** The classification is identical ("authorized") in both cases because registry match **always forces authorized**, regardless of the final score. The penalty value only affects score transparency.

---

### Example: Score Flooring Behavior (Negative Scores → 0)

**Scenario:** Registry penalty exceeds detection score.

**Test Case 1: Small Penalty**
```
Endpoint signal:     +5
Registry penalty:    -6
Calculated Score:    -1
Final Score:         0 (floored)
Classification:      authorized (forced)
```

**Test Case 2: Large Penalty**
```
Endpoint signal:     +5
Registry penalty:    -12
Calculated Score:    -7
Final Score:         0 (floored)
Classification:      authorized (forced)
```

**Test Case 3: Very Large Penalty**
```
Endpoint signal:     +3
Registry penalty:    -15
Calculated Score:    -12
Final Score:         0 (floored)
Classification:      authorized (forced)
```

**Rule:** MCPeeker never displays negative scores. Any score calculation that results in a negative value is automatically floored to 0. This prevents confusing negative risk scores in the UI.

---

### Comparison Table: Registry Penalty Values

| Penalty | Score Impact (Endpoint +11) | Score Impact (Multi-signal +21) | Classification | Use Case |
|---------|----------------------------|----------------------------------|----------------|----------|
| **-6** | 11 - 6 = 5 | 21 - 6 = 15 | authorized (forced) | Default, balanced |
| **-8** | 11 - 8 = 3 | 21 - 8 = 13 | authorized (forced) | Slightly stronger |
| **-10** | 11 - 10 = 1 | 21 - 10 = 11 | authorized (forced) | Strong penalty |
| **-12** | 11 - 12 = 0 | 21 - 12 = 9 | authorized (forced) | Maximum clarity |
| **-15** | 11 - 15 = 0 | 21 - 15 = 6 | authorized (forced) | Extreme (unnecessary) |

**Observation:** All penalty values result in "authorized" classification due to forced override. Choose based on desired score visualization, not classification behavior.

---

### When to Adjust Registry Penalty

**Adjust to -12 if:**
- You want audit logs to show stronger registry impact
- Compliance requires obvious score differentiation
- You're demonstrating registry value to stakeholders

**Keep at -6 (default) if:**
- Current scoring is working well
- You prefer moderate score adjustments
- No specific audit requirements

**Never adjust beyond -15:**
- Forced classification makes it unnecessary
- Extremely negative penalties add no value
- Can confuse stakeholders seeing scores near 0

**Remember:** The registry match **forced classification override** (added in recent fix) already ensures approved MCPs are always classified as "authorized", making the exact penalty value a preference rather than a requirement.

