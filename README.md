# Harness Eval

A small CLI project for evaluating whether changes to a coding-agent harness improve real engineering outcomes.

## Quick start

```bash
python -m pip install -e .
harness-eval compare --baseline harnesses/baseline --candidate harnesses/candidate --benchmark benchmark --runs 1 --mock
```

## Project goals

- isolate each benchmark run in a temporary workspace
- inject hidden acceptance tests after the agent is done
- collect pass/fail telemetry from pytest, ruff, and mypy
- compare baseline vs candidate harness outcomes objectively
