from pathlib import Path

from typer.testing import CliRunner

from harness_eval.cli import app
from harness_eval.evaluator import evaluate_harness
from harness_eval.runner import AgentRunner

runner = CliRunner()


def test_evaluate_harness_with_mock_runner(tmp_path):
    benchmark_dir = Path("benchmark")
    harness_dir = Path("harnesses/candidate")

    report = evaluate_harness(
        benchmark_dir=benchmark_dir,
        harness_dir=harness_dir,
        runner=AgentRunner(mock_mode=True),
        runs=1,
        temp_root=tmp_path,
    )

    assert report.total_runs >= 1
    assert report.successful_runs >= 1
    assert report.harness_name == "candidate"
    assert report.mean_pass_rate >= 0.0


def test_compare_cli_with_mock_runner():
    result = runner.invoke(
        app,
        [
            "compare",
            "--baseline",
            "harnesses/baseline",
            "--candidate",
            "harnesses/candidate",
            "--tasks",
            "benchmark/tasks",
            "--project",
            "benchmark/example_project",
            "--runs",
            "1",
            "--mock",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "VERDICT" in result.output
    assert "Baseline" in result.output or "Candidate" in result.output


def test_mock_runner_reads_instructions_from_non_candidate_harness(tmp_path):
    harness_dir = tmp_path / "strict"
    harness_dir.mkdir()
    (harness_dir / "AGENTS.md").write_text(
        "Validate query parameters and use Pydantic response schemas."
    )

    report = evaluate_harness(
        benchmark_dir=Path("benchmark"),
        harness_dir=harness_dir,
        runner=AgentRunner(mock_mode=True),
        runs=1,
        temp_root=tmp_path / "runs",
    )

    assert report.harness_name == "strict"
    assert report.mean_requirement_satisfaction > 0.0


def test_candidate_mcp_harness_includes_mcp_config():
    harness_dir = Path("harnesses/candidate-mcp")

    assert harness_dir.is_dir()
    assert (harness_dir / "AGENTS.md").exists()
    assert (harness_dir / ".mcp.json").exists()
    assert "static-analysis" in (harness_dir / ".mcp.json").read_text()
