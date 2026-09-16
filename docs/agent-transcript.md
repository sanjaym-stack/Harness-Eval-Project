# Engineering Development Process: Agent Session Log

*Template guide for recording the actual agent session during development.*

### 1. Task Prompt Given to Agent
```text
Implement the ComparisonEngine class in src/harness_eval/comparison.py that computes 
deltas between baseline and candidate summaries and applies the four-tier verdict logic.
```

### 2. Agent Implementation Output
The agent generated the initial draft of src/harness_eval/comparison.py.

### 3. Manual Inspection & Discovered Failure
What I checked: Ran pytest tests/test_evaluator_core.py.
Where the agent was wrong: The agent computed cost_delta_percentage as (cand - base) / cand * 100 instead of (cand - base) / base * 100. When baseline cost was 0.10 and candidate cost was 0.20, it calculated +50% instead of +100%. Furthermore, it crashed with a ZeroDivisionError when the baseline cost was $0.00.

### 4. Corrective Prompt Provided to Agent
```text
The cost delta percentage formula is mathematically incorrect and fails when baseline cost is zero.
Fix the denominator to use baseline cost and add a defensive check for base_cost <= 0.
```

### 5. Final Verified Solution
The agent corrected the calculation in _evaluate_verdict and added regression guards for zero-cost baselines.
