# Harness Evaluation Report

## Executive Summary
**Verdict:** `POSITIVE WITH COST TRADE-OFF`  
**Conclusion:** Candidate improved correctness and requirements but incurred substantial cost overhead.

### Supporting Evidence
- Correctness improved: pass rate Δ=+41.7%, requirements Δ=+42.9%.
- Token cost increased significantly (+73.8%).

## Controlled Comparison Matrix

| Dimension | Old Harness — `baseline` | New Harness — `candidate` | Delta (Δ) |
|---|---|---|---|
| **Test Pass Rate** | 58.3% | 100.0% | `+41.7%` |
| **Requirement Satisfaction** | 57.1% | 100.0% | `+42.9%` |
| **Ruff Pass Rate** | 100.0% | 0.0% | `-100.0%` |
| **Mypy Pass Rate** | 100.0% | 50.0% | `-50.0%` |
| **Mean Duration** | 0.05s | 0.05s | `+0.00s` |
| **Est. Cost / Run** | 0.0195 | 0.0339 | `+73.8%` |

## Limitations
- Focused benchmark sample for controlled verification.
- Token counts reflect provider exposure; reported as unavailable when unsupported.
- Multiple runs per task are used to quantify and counter agent non-determinism.

## Raw Run Telemetry
Total individual runs recorded: `8`
