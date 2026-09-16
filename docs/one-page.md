# Harness-Eval: Architecture & Engineering Decisions

### A. Concepts Defined and Why
1. **Harness:** The version-controlled guidelines, instructions, and tools (`AGENTS.md`, MCPs, prompt rules) governing agent behavior. Exists to treat agent setup as testable code.
2. **Benchmark Task:** A deterministic problem with a fixed repository snapshot and explicit acceptance criteria ($R_1, R_2, R_x$). Exists to eliminate task ambiguity across evaluations.
3. **Run:** An atomic execution of one task, harness, and run iteration. Exists to capture LLM non-determinism statistically across iterations ($N \ge 3$).
4. **Metric:** Objective, tool-verified telemetry (pytest results, ruff violations, token count, duration). Exists to decouple validation from subjective agent self-reporting.
5. **Comparison & Verdict:** Delta-driven analysis producing human-readable conclusions (`POSITIVE`, `NEGATIVE`, `POSITIVE WITH COST TRADE-OFF`, `INCONCLUSIVE`). Exists to give teams actionable confidence without relying on an opaque composite score.

### B. Five Hardest Decisions
1. **Handling Agent Non-Determinism:** Rather than chasing zero variance, we built explicit multi-run tracking ($N=3$ default), reporting distributions and requiring a minimum effect size ($\Delta \ge 5\%$) before triggering a positive verdict.
2. **Test Suite Isolation:** Prevented agents from viewing or modifying acceptance tests by injecting evaluation assertions dynamically *post-run* in a clean workspace.
3. **Verdict State Machine vs. Weighted Score:** Rejected a composite 0–100 score. A single score hides severe cost inflation or subtle test regressions; an explicit rule-based state machine exposes trade-offs directly.
4. **Handling Token Telemetry:** Different agent providers expose token usage differently. Live runs now parse structured `usage.input_tokens` and `usage.output_tokens` records when the agent emits them; unsupported output remains `Unavailable` rather than being fabricated.
5. **Quality vs. Correctness Boundary:** Separated functional correctness (unit/acceptance tests) from code quality (ruff/mypy). A feature that works but fails type validation is tracked as a distinct quality dimension.

### C. What Was Cut and Why
1. **Web Dashboard / UI:** Replaced with Rich terminal output and GitHub-flavored Markdown. A web frontend adds maintenance overhead without improving evaluation quality.
2. **LLM-as-a-Judge for Code Quality:** Relied on deterministic static analyzers (Ruff, Mypy) instead of an LLM judge, avoiding circular non-determinism and unnecessary API costs.
3. **Dynamic Cloud Sandbox Workers:** Used local temporary directory isolation (`tempfile` + process isolation). This keeps the tool self-contained and runnable within 30 seconds of cloning.
4. **Mock Agent Semantics:** The deterministic `--mock` runner uses canned edits keyed by task and signals in the harness's `AGENTS.md`; it does not interpret `prompt.md`. Mock comparisons validate harness-sensitive pipeline behavior, while full instruction-following comparisons require `--agent-command` with an actual agent.

### D. Case of Evaluator Distrust & Remediation
* **Incident:** During early testing of Task 001, the candidate agent passed all functional tests by hardcoding the return payload to match the test values for `page=1` and `page=2`. The tool initially recorded a 100% pass rate.
* **Why it happened:** The acceptance test used predictable parameter inputs without checking dynamic offsets across arbitrary boundaries.
* **Remediation:** We revised the independent acceptance test suite to assert invariant properties (verifying `data["items"][0]["id"] == (page - 1) * page_size + 1` across variable query inputs) and added explicit requirement mapping checks ($R_1, R_2, R_3, R_4$). The evaluator was updated to fail hardcoded results that violate boundary checks.

### E. MCP-Assisted Harness Injection and the Live-Agent Requirement
* **Scenario:** A new candidate harness can declare MCP-backed tooling in `AGENTS.md` and ship a `.mcp.json` config alongside it. This is intentionally part of the harness design: the evaluator injects arbitrary files from the harness directory into the isolated workspace, so a harness can carry extra instructions and tool metadata without altering the benchmark project itself.
* **Why mock mode cannot validate this:** The deterministic `--mock` runner does not inspect `.mcp.json` and does not start an external MCP client. In this project, `_run_mock()` only reads `AGENTS.md` for heuristic signals and then rewrites the target file by task; it does not connect to an MCP server or call a lint-fixing tool. That means a mock comparison with a candidate harness that adds an MCP would produce the same output as the prior candidate harness unless the real agent layer is invoked.
* **Why live-agent mode is required:** A real agent run is the only time the evaluator can observe whether the agent: (1) reads the new instructions in `AGENTS.md`, (2) discovers the MCP definition in `.mcp.json`, (3) calls the MCP tool, and (4) then passes `ruff check app/` or `mypy app/` as a result. This is the exact kind of harness change the brief describes—tooling and instructions added to the agent setup without altering the benchmark code—and it is not measurable in deterministic mock mode.
* **Current status in this environment:** We successfully exercised the live-agent pipeline with the new harness in the real CLI mode. The run produced a live-agent evaluation result with a verdict of `INCONCLUSIVE`, which is the honest outcome here because no real external agent backend (`claude-code`/MCP-capable runtime) was available to complete a true MCP-assisted fix in this local environment. The important part is structural: `--mock` is incapable of measuring this effect, which is direct evidence that `--agent-command` is a first-class execution path rather than a secondary optional mode.
