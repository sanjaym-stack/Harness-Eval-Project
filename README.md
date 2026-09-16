# Harness Eval

`harness-eval` is a CLI for measuring whether changes to a coding-agent harness
produce better engineering outcomes. It compares a baseline harness with a
candidate harness against the same isolated benchmark tasks.

The evaluator records acceptance-test results, Ruff and Mypy results, runtime,
token usage, estimated cost, and a machine-readable raw run record.

## Requirements

- Python 3.10 or newer
- An agent command that accepts a workspace path when running live evaluations

## Installation

Create and activate a virtual environment, then install the project:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

On macOS or Linux, activate the environment with:

```bash
source .venv/bin/activate
```

## Quick start

Run the standard deterministic evaluation with the repository launcher:

```bash
python run.py
```

The launcher automatically uses `.venv` when present, installs the project and
its declared dependencies, then compares `harnesses/baseline` and
`harnesses/candidate` across all tasks. Reports are written to `results/`.

For explicit control, run the CLI directly:

Run the deterministic mock evaluation:

```powershell
python -m harness_eval.cli compare `
	--baseline harnesses/baseline `
	--candidate harnesses/candidate `
	--tasks benchmark/tasks `
	--project benchmark/example_project `
	--runs 1 `
	--mock `
	--output-dir results
```

The equivalent command using the installed console script is:

```bash
harness-eval compare \
	--baseline harnesses/baseline \
	--candidate harnesses/candidate \
	--tasks benchmark/tasks \
	--project benchmark/example_project \
	--runs 1 \
	--mock \
	--output-dir results
```

Mock mode is deterministic and is useful for testing evaluator behavior. It
does not invoke an external coding agent.

## Live-agent evaluation

Use `--agent-command` to run an actual agent. The command template receives:

- `{workspace}`: isolated project directory for the current run
- `{prompt_file}`: task prompt copied into that workspace
- `{task_id}`: current benchmark task ID

Example:

```powershell
python -m harness_eval.cli compare `
	--baseline harnesses/baseline `
	--candidate harnesses/candidate `
	--tasks benchmark/tasks `
	--project benchmark/example_project `
	--runs 3 `
	--agent-command "python C:\tools\fake_agent.py --workspace {workspace}" `
	--output-dir results
```

Do not combine `--mock` with `--agent-command`; mock mode takes precedence.

## Repository layout

```text
benchmark/example_project/   Starting project copied for each run
benchmark/tasks/             Prompts, specifications, and acceptance tests
harnesses/baseline/          Baseline harness instructions and skills
harnesses/candidate/         Candidate harness instructions and skills
src/harness_eval/            CLI, runner, evaluator, comparison, and reporting code
tests/                       Tests for the evaluator itself
results/                     Generated Markdown and JSON reports
```

## Benchmark tasks

Each task directory contains:

- `prompt.md`: instructions supplied to the agent
- `spec.json`: task metadata and requirement-to-test mappings
- `test_eval.py`: acceptance tests

Acceptance tests are copied into the isolated workspace only after the agent
has finished. This keeps the evaluation tests independent from the agent's
working context and prevents the agent from modifying them during its run.

## Outputs

Each comparison writes:

- `evaluation_report.md`: human-readable comparison and verdict
- `raw_results.json`: serialized per-run telemetry

The report compares test pass rate, requirement satisfaction, quality-tool pass
rates, duration, token usage, and estimated cost. Token usage is reported as
unavailable when the agent does not expose it in a JSON record containing a
`usage` object.

## Safety and reproducibility

- Every run starts from a fresh copy of `benchmark/example_project` in a
	temporary directory.
- Harness files are injected into that temporary workspace.
- The source benchmark project is never modified by an evaluation run.
- Baseline and candidate runs use the same tasks and project snapshot.

## Development checks

Run the evaluator's own tests and quality checks from the repository root:

```bash
python -m pytest
python -m ruff check src tests
python -m mypy src --ignore-missing-imports
```

The `evaluate` command remains available as a backward-compatible alias for
`compare`.
