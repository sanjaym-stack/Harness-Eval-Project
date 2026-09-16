"""CLI entrypoint for harness-eval."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from harness_eval.comparison import ComparisonEngine
from harness_eval.evaluator import IndependentEvaluator
from harness_eval.models import RunMetrics, TaskSpec
from harness_eval.reporter import ReportGenerator
from harness_eval.runner import AgentRunner, WorkspaceManager

app = typer.Typer(help="Controlled evaluation CLI for coding-agent harnesses.")
console = Console()


def _run_comparison(
    baseline: Path,
    candidate: Path,
    tasks: Path,
    project: Path,
    runs: int,
    agent_command: Optional[str],
    mock: bool,
    output_dir: Path,
) -> None:
    console.print("[bold blue]Starting Harness Evaluation Pipeline...[/bold blue]")
    console.print(f" • Old harness (baseline):  [cyan]{baseline}[/cyan]")
    console.print(f" • New harness (candidate): [cyan]{candidate}[/cyan]")
    console.print(f" • Project:   [cyan]{project}[/cyan]")
    console.print(f" • Tasks:     [cyan]{tasks}[/cyan]")
    console.print(f" • Runs/Task: [cyan]{runs}[/cyan]")
    console.print(f" • Mode:      [yellow]{'Deterministic Mock' if mock else 'Live Agent'}[/yellow]\n")

    task_dirs = sorted([d for d in tasks.iterdir() if d.is_dir()])
    if not task_dirs:
        console.print("[red]Error: No task directories found in tasks directory.[/red]")
        raise typer.Exit(code=1)

    workspace_mgr = WorkspaceManager(project)
    evaluator = IndependentEvaluator()
    all_runs: list[RunMetrics] = []

    with console.status("[bold green]Executing evaluation runs across isolated workspaces...") as status:
        for task_dir in task_dirs:
            spec_file = task_dir / "spec.json"
            prompt_file = task_dir / "prompt.md"
            if not spec_file.exists() or not prompt_file.exists():
                console.print(f"[yellow]Skipping malformed task directory: {task_dir.name}[/yellow]")
                continue

            task_spec = TaskSpec.model_validate_json(spec_file.read_text())
            task_prompt = prompt_file.read_text()

            for h_name, h_dir in [("baseline", baseline), ("candidate", candidate)]:
                runner = AgentRunner(command_template=agent_command, mock_mode=mock, harness_dir=h_dir)
                for run_idx in range(1, runs + 1):
                    label = "OLD harness" if h_name == "baseline" else "NEW harness"
                    status.update(
                        f"Running [bold magenta]{task_spec.id}[/bold magenta] | {label} | Run {run_idx}/{runs}"
                    )

                    with tempfile.TemporaryDirectory() as temp_root_str:
                        temp_root = Path(temp_root_str)
                        workspace = workspace_mgr.create_isolated_workspace(temp_root)
                        workspace_mgr.inject_harness(workspace, h_dir)

                        exit_code, duration, in_tokens, out_tokens, err = runner.run(
                            workspace, task_prompt, task_spec, h_name
                        )

                        passed, failed, total, pass_rate, reqs, quality = evaluator.evaluate_task(
                            workspace, task_dir, task_spec
                        )

                        tot_tokens = (in_tokens + out_tokens) if (in_tokens is not None and out_tokens is not None) else None
                        cost = evaluator.calculate_cost(in_tokens, out_tokens)

                        run_record = RunMetrics(
                            task_id=task_spec.id,
                            harness_name=h_name,
                            run_index=run_idx,
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
                            total_tokens=tot_tokens,
                            estimated_cost_usd=cost,
                            is_mock=mock,
                            error_message=err,
                        )
                        all_runs.append(run_record)

    engine = ComparisonEngine()
    baseline_summary = engine.summarize_harness("baseline", all_runs)
    candidate_summary = engine.summarize_harness("candidate", all_runs)
    report = engine.compare(baseline_summary, candidate_summary, all_runs)

    console.print("\n")
    ReportGenerator.print_terminal_summary(report)

    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / "evaluation_report.md"
    json_path = output_dir / "raw_results.json"

    ReportGenerator.write_markdown_report(report, md_path)
    ReportGenerator.write_json_results(report, json_path)

    console.print(f" • Markdown Report: [cyan]{md_path}[/cyan]")
    console.print(f" • Raw JSON Results: [cyan]{json_path}[/cyan]\n")


@app.command()
def compare(
    baseline: Path = typer.Option(..., "--baseline", "-b", exists=True, file_okay=False, help="Baseline harness directory"),
    candidate: Path = typer.Option(..., "--candidate", "-c", exists=True, file_okay=False, help="Candidate harness directory"),
    tasks: Path = typer.Option(..., "--tasks", "-t", exists=True, file_okay=False, help="Benchmark tasks directory"),
    project: Path = typer.Option(..., "--project", "-p", exists=True, file_okay=False, help="Starting project base directory"),
    runs: int = typer.Option(3, "--runs", "-r", help="Number of repetitions per task to counter non-determinism"),
    agent_command: Optional[str] = typer.Option(None, "--agent-command", help="Agent command template (e.g. 'claude-code --dir {workspace}')"),
    mock: bool = typer.Option(False, "--mock", help="Run in deterministic mock mode without external agent execution"),
    output_dir: Path = typer.Option(Path("./results"), "--output-dir", "-o", help="Directory to save output reports"),
):
    """Compare an old harness against a new one across the same benchmark tasks."""
    _run_comparison(
        baseline=baseline,
        candidate=candidate,
        tasks=tasks,
        project=project,
        runs=runs,
        agent_command=agent_command,
        mock=mock,
        output_dir=output_dir,
    )


@app.command()
def evaluate(
    baseline: Path = typer.Option(..., "--baseline", "-b", exists=True, file_okay=False, help="Baseline harness directory"),
    candidate: Path = typer.Option(..., "--candidate", "-c", exists=True, file_okay=False, help="Candidate harness directory"),
    tasks: Path = typer.Option(..., "--tasks", "-t", exists=True, file_okay=False, help="Benchmark tasks directory"),
    project: Path = typer.Option(..., "--project", "-p", exists=True, file_okay=False, help="Starting project base directory"),
    runs: int = typer.Option(3, "--runs", "-r", help="Number of repetitions per task to counter non-determinism"),
    agent_command: Optional[str] = typer.Option(None, "--agent-command", help="Agent command template (e.g. 'claude-code --dir {workspace}')"),
    mock: bool = typer.Option(False, "--mock", help="Run in deterministic mock mode without external agent execution"),
    output_dir: Path = typer.Option(Path("./results"), "--output-dir", "-o", help="Directory to save output reports"),
):
    """Backward-compatible alias for the old/new harness comparison command."""
    _run_comparison(
        baseline=baseline,
        candidate=candidate,
        tasks=tasks,
        project=project,
        runs=runs,
        agent_command=agent_command,
        mock=mock,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    app()
