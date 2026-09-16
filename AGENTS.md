# AGENTS.md — Harness-Eval Project Directives

## Architecture & Principles
`harness-eval` is an evaluation CLI designed to measure whether modifications to coding-agent harnesses (prompts, rules, skills, MCPs) produce genuine engineering improvements.

## Core Directives
1. **Isolated Execution:** Always isolate test runs in clean temporary directories (`tempfile`). Never run the evaluation in-place on the source benchmark project.
2. **Hidden Acceptance Tests:** Acceptance test files (`test_eval.py`) must be injected post-agent run. The agent must never see or modify the evaluation tests during its run.
3. **Objective Telemetry:** Prefer programmatic assertions (Pytest return codes, Ruff violations, Mypy error counts) over subjective evaluation.
4. **No Fabricated Data:** If token usage or cost is not exposed by an agent runner, explicitly report `Unavailable`. Never invent metrics.
5. **Preserve Raw Records:** Always serialize raw run records to `raw_results.json` alongside human-readable markdown reports.
