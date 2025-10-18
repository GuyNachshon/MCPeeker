# MCPeeker Correlator

The correlator service aggregates detection signals from multiple sources and applies weighted scoring to classify MCP installations.

## Scoring Configuration

### Scoring Weights

The correlator uses configurable weights for each detection signal type. These weights determine how much each signal contributes to the total risk score.

**Default Weights:**

```go
ScoringWeights{
    Endpoint: 11,   // File-based detections (manifest.json, server executables)
    Judge:    5,    // Gateway/Judge service confirmations
    Network:  3,    // Network activity detections
    Registry: -6,   // Penalty applied when MCP is found in authorized registry
}
```

### Registry Penalty Parameter

**Parameter:** `ScoringWeights.Registry`
**Default Value:** `-6`
**Suggested Range:** `-6` to `-15`
**Type:** Integer (negative value)

The Registry weight is a **penalty** (negative value) applied when an MCP matches an entry in the authorized registry. This penalty reduces the detection score, typically lowering the risk classification.

**Example Calculation:**
```
Initial Detection:
  Endpoint signal:    +11
  Total Score:        11
  Classification:     unauthorized (score ≥ 9)

After Registry Match:
  Endpoint signal:    +11
  Registry penalty:   -6
  Total Score:        5
  Classification:     authorized (forced by registry match)
```

### Configuration File

Update the registry penalty in your configuration:

```yaml
# config.yaml
scoring:
  weights:
    endpoint: 11
    judge: 5
    network: 3
    registry: -6    # Adjust this value if needed (-6 to -15)

classification:
  thresholds:
    authorized: 4    # score ≤ 4
    suspect: 8       # 5 ≤ score ≤ 8
    unauthorized: 9  # score ≥ 9
```

### Important Notes

1. **Forced Classification Override:**
   When an MCP matches the registry, the classification is **always forced to "authorized"** regardless of the final score. This ensures that approved MCPs never trigger false alerts.

2. **Penalty Value Impact:**
   Because of the forced classification, the exact registry penalty value is **non-critical** for behavior. Whether the penalty is `-6` or `-12`, registry-matched MCPs will always be classified as "authorized".

3. **Score Transparency:**
   The penalty value affects the **displayed score**, which can be useful for:
   - Audit trails showing score calculations
   - Understanding relative risk even for authorized MCPs
   - Debugging detection logic

4. **Recommended Values:**
   - **Conservative:** `-6` (current default) - Reduces score moderately
   - **Aggressive:** `-12` - Makes registry match more obvious in scoring
   - **Maximum:** `-15` - Strongest penalty, but not necessary given forced classification

### When to Adjust

Consider adjusting the registry penalty if:
- You want score calculations to more clearly show registry match impact
- Audit requirements need stronger penalty visualization
- You're tuning the scoring system for a specific environment

**However**, since forced classification already ensures correct behavior, adjusting this value is **optional** and primarily affects score transparency rather than classification outcomes.

## Testing

See the comprehensive test suite in `pkg/engine/correlator_test.go` for examples of how scoring and classification work with various configurations.

Run tests:
```bash
go test -v ./pkg/engine/...
```

Run with coverage:
```bash
go test -coverprofile=coverage.out ./pkg/engine/...
go tool cover -html=coverage.out
```
