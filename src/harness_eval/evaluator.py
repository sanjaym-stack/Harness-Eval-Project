"""Independent verification: Pytest acceptance tests, Ruff, and Mypy."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from harness_eval.comparison import ComparisonEngine
from harness_eval.models import HarnessSummary, QualityMetrics, RunMetrics, TaskSpec
from harness_eval.runner import AgentRunner, WorkspaceManager


class IndependentEvaluator:
    """Executes objective verification checks against the modified workspace."""

    def __init__(
        self,
        token_price_input_per_million: float = 3.0,
        token_price_output_per_million: float = 15.0,
    ):
        self.price_input = token_price_input_per_million
        self.price_output = token_price_output_per_million

    def evaluate_task(
        self,
        workspace: Path,
        task_dir: Path,
        task_spec: TaskSpec,
    ) -> Tuple[int, int, int, float, Dict[str, bool], QualityMetrics]:
        eval_test_src = task_dir / task_spec.eval_test_file
        eval_test_dst = workspace / "tests" / task_spec.eval_test_file
        eval_test_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(eval_test_src, eval_test_dst)

        tests_passed, tests_failed, tests_total, req_results = self._run_pytest(workspace, task_spec)
        pass_rate = (tests_passed / tests_total) if tests_total > 0 else 0.0
        quality = self._run_quality_checks(workspace)

        return tests_passed, tests_failed, tests_total, pass_rate, req_results, quality

    def _run_pytest(self, workspace: Path, task_spec: TaskSpec) -> Tuple[int, int, int, Dict[str, bool]]:
        report_path = workspace / ".pytest-report.json"
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "-v",
            "--tb=short",
            "--json-report",
            f"--json-report-file={report_path}",
        ]
        subprocess.run(cmd, cwd=workspace, capture_output=True, text=True)

        if not report_path.exists():
            return 0, 0, 0, {req.id: False for req in task_spec.requirements}

        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return 0, 0, 0, {req.id: False for req in task_spec.requirements}

        tests = report.get("tests", [])
        passed = sum(1 for test in tests if test.get("outcome") == "passed")
        failed = sum(1 for test in tests if test.get("outcome") in {"failed", "error"})
        total = passed + failed

        req_results: Dict[str, bool] = {}
        for req in task_spec.requirements:
            matches = [
                test
                for test in tests
                if test.get("nodeid") == req.target or test.get("nodeid", "").endswith(f"::{req.target}")
            ]
            req_results[req.id] = bool(matches) and all(test.get("outcome") == "passed" for test in matches)

        return passed, failed, total, req_results

    def _run_quality_checks(self, workspace: Path) -> QualityMetrics:
        ruff_res = subprocess.run([sys.executable, "-m", "ruff", "check", "app/"], cwd=workspace, capture_output=True, text=True)
        ruff_passed = ruff_res.returncode == 0
        ruff_violations = len([line for line in ruff_res.stdout.splitlines() if line.strip() and not line.startswith("Found")])

        mypy_res = subprocess.run(
            [sys.executable, "-m", "mypy", "app/", "--ignore-missing-imports"],
            cwd=workspace,
            capture_output=True,
            text=True,
        )
        mypy_passed = mypy_res.returncode == 0
        mypy_errors = len([line for line in mypy_res.stdout.splitlines() if ": error:" in line])

        return QualityMetrics(
            ruff_passed=ruff_passed,
            ruff_violations=ruff_violations,
            mypy_passed=mypy_passed,
            mypy_errors=mypy_errors,
        )

    def calculate_cost(self, input_tokens: Optional[int], output_tokens: Optional[int]) -> Optional[float]:
        if input_tokens is None or output_tokens is None:
            return None
        cost = (input_tokens / 1_000_000 * self.price_input) + (output_tokens / 1_000_000 * self.price_output)
        return round(cost, 6)


def evaluate_harness(
    benchmark_dir: Path,
    harness_dir: Path,
    runner: AgentRunner,
    runs: int = 1,
    temp_root: Optional[Path] = None,
) -> HarnessSummary:
    """Run a harness against the benchmark tasks and summarize the aggregate outcome."""
    benchmark_dir = Path(benchmark_dir)
    harness_dir = Path(harness_dir)
    temp_root = temp_root or Path(tempfile.gettempdir()) / "harness-eval"
    temp_root.mkdir(parents=True, exist_ok=True)

    project_dir = benchmark_dir / "example_project"
    if not project_dir.exists():
        raise FileNotFoundError(f"Benchmark project directory does not exist: {project_dir}")

    task_dir = benchmark_dir / "tasks"
    if not task_dir.exists():
        raise FileNotFoundError(f"Benchmark tasks directory does not exist: {task_dir}")

    workspace_mgr = WorkspaceManager(project_dir)
    evaluator = IndependentEvaluator()
    all_runs: List[RunMetrics] = []
    runner.harness_dir = harness_dir

    for task_path in sorted(task_dir.iterdir()):
        if not task_path.is_dir():
            continue

        spec_file = task_path / "spec.json"
        prompt_file = task_path / "prompt.md"
        if not spec_file.exists() or not prompt_file.exists():
            continue

        task_spec = TaskSpec.model_validate_json(spec_file.read_text())
        task_prompt = prompt_file.read_text()

        for run_index in range(1, runs + 1):
            run_tmp = temp_root / f"{task_spec.id}-{harness_dir.name}-{run_index}"
            run_tmp.mkdir(parents=True, exist_ok=True)
            workspace = workspace_mgr.create_isolated_workspace(run_tmp)
            workspace_mgr.inject_harness(workspace, harness_dir)

            exit_code, duration, in_tokens, out_tokens, err = runner.run(
                workspace,
                task_prompt,
                task_spec,
                harness_dir.name,
            )
            passed, failed, total, pass_rate, reqs, quality = evaluator.evaluate_task(
                workspace,
                task_path,
                task_spec,
            )
            cost = evaluator.calculate_cost(in_tokens, out_tokens)
            total_tokens = (in_tokens + out_tokens) if in_tokens is not None and out_tokens is not None else None

            all_runs.append(
                RunMetrics(
                    task_id=task_spec.id,
                    harness_name=harness_dir.name,
                    run_index=run_index,
                    exit_code=exit_code,
                    duration_seconds=duration,
                    tests_passed=passed,
                    tests_failed=failed,
                    tests_total=total,
                    pass_rate=pass_rate,
                    requirement_results=reqs,
                    quality=quality,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=cost,
                    is_mock=runner.mock_mode,
                    error_message=err,
                )
            )

    if not all_runs:
        raise ValueError(f"No benchmark runs were produced for harness: {harness_dir}")

    return ComparisonEngine().summarize_harness(harness_dir.name, all_runs)
