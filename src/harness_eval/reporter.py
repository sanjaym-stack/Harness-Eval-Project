"""Generates Rich terminal tables, Markdown reports, and raw JSON outputs."""
from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from harness_eval.models import ComparisonReport, VerdictType

console = Console()


class ReportGenerator:
    """Generates evaluation output across terminal, Markdown, and JSON formats."""

    @staticmethod
    def print_terminal_summary(report: ComparisonReport) -> None:
        b = report.baseline_summary
        c = report.candidate_summary

        table = Table(title="Harness Evaluation Metrics Summary", show_header=True, header_style="bold cyan")
        table.add_column("Metric Dimension", style="bold")
        table.add_column("Old Harness", style="white")
        table.add_column("New Harness", style="white")
        table.add_column("Delta (Δ)", style="yellow")

        table.add_row(
            "Overall Test Pass Rate",
            f"{b.mean_pass_rate * 100:.1f}%",
            f"{c.mean_pass_rate * 100:.1f}%",
            f"{report.pass_rate_delta * 100:+.1f}%",
        )
        table.add_row(
            "Requirement Satisfaction",
            f"{b.mean_requirement_satisfaction * 100:.1f}%",
            f"{c.mean_requirement_satisfaction * 100:.1f}%",
            f"{report.req_satisfaction_delta * 100:+.1f}%",
        )
        table.add_row(
            "Ruff Lint Pass Rate",
            f"{b.ruff_pass_rate * 100:.1f}%",
            f"{c.ruff_pass_rate * 100:.1f}%",
            f"{(c.ruff_pass_rate - b.ruff_pass_rate) * 100:+.1f}%",
        )
        table.add_row(
            "Mypy Type Pass Rate",
            f"{b.mypy_pass_rate * 100:.1f}%",
            f"{c.mypy_pass_rate * 100:.1f}%",
            f"{(c.mypy_pass_rate - b.mypy_pass_rate) * 100:+.1f}%",
        )
        table.add_row(
            "Avg Run Duration",
            f"{b.mean_duration_seconds:.2f}s",
            f"{c.mean_duration_seconds:.2f}s",
            f"{report.duration_delta_seconds:+.2f}s",
        )

        b_tokens = f"{b.mean_tokens:,.0f}" if b.mean_tokens is not None else "Unavailable"
        c_tokens = f"{c.mean_tokens:,.0f}" if c.mean_tokens is not None else "Unavailable"
        cost_delta_str = f"{report.cost_delta_percentage:+.1f}%" if report.cost_delta_percentage is not None else "N/A"
        table.add_row("Mean Tokens / Run", b_tokens, c_tokens, cost_delta_str)

        console.print(table)

        color = "green" if report.verdict.verdict == VerdictType.POSITIVE else "yellow"
        if report.verdict.verdict == VerdictType.NEGATIVE:
            color = "red"

        console.print(
            Panel(
                f"[bold {color}]VERDICT: {report.verdict.verdict.value}[/bold {color}]\n\n"
                f"[white]{report.verdict.summary_reason}[/white]\n"
                + "\n".join(f" • {r}" for r in report.verdict.detailed_reasons),
                title="Final Evaluation Assessment",
                border_style=color,
            )
        )

    @staticmethod
    def write_markdown_report(report: ComparisonReport, output_file: Path) -> None:
        b = report.baseline_summary
        c = report.candidate_summary

        lines = [
            "# Harness Evaluation Report",
            "",
            "## Executive Summary",
            f"**Verdict:** `{report.verdict.verdict.value}`  ",
            f"**Conclusion:** {report.verdict.summary_reason}",
            "",
            "### Supporting Evidence",
        ]
        for r in report.verdict.detailed_reasons:
            lines.append(f"- {r}")

        lines.extend(
            [
                "",
                "## Controlled Comparison Matrix",
                "",
                f"| Dimension | Old Harness — `{b.harness_name}` | New Harness — `{c.harness_name}` | Delta (Δ) |",
                "|---|---|---|---|",
                f"| **Test Pass Rate** | {b.mean_pass_rate * 100:.1f}% | {c.mean_pass_rate * 100:.1f}% | `{report.pass_rate_delta * 100:+.1f}%` |",
                f"| **Requirement Satisfaction** | {b.mean_requirement_satisfaction * 100:.1f}% | {c.mean_requirement_satisfaction * 100:.1f}% | `{report.req_satisfaction_delta * 100:+.1f}%` |",
                f"| **Ruff Pass Rate** | {b.ruff_pass_rate * 100:.1f}% | {c.ruff_pass_rate * 100:.1f}% | `{(c.ruff_pass_rate - b.ruff_pass_rate) * 100:+.1f}%` |",
                f"| **Mypy Pass Rate** | {b.mypy_pass_rate * 100:.1f}% | {c.mypy_pass_rate * 100:.1f}% | `{(c.mypy_pass_rate - b.mypy_pass_rate) * 100:+.1f}%` |",
                f"| **Mean Duration** | {b.mean_duration_seconds:.2f}s | {c.mean_duration_seconds:.2f}s | `{report.duration_delta_seconds:+.2f}s` |",
                f"| **Est. Cost / Run** | {b.total_estimated_cost or 0.0:.4f} | {c.total_estimated_cost or 0.0:.4f} | `{report.cost_delta_percentage or 0.0:+.1f}%` |",
                "",
                "## Limitations",
                "- Focused benchmark sample for controlled verification.",
                "- Token counts reflect provider exposure; reported as unavailable when unsupported.",
                "- Multiple runs per task are used to quantify and counter agent non-determinism.",
                "",
                "## Raw Run Telemetry",
                f"Total individual runs recorded: `{len(report.raw_runs)}`",
                "",
            ]
        )

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(lines), encoding="utf-8")

    @staticmethod
    def write_json_results(report: ComparisonReport, output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")
