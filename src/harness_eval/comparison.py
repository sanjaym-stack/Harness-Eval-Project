"""Multi-run statistical aggregator and rule-based verdict engine."""
from __future__ import annotations

import statistics
from typing import List, Optional

from harness_eval.models import (
    ComparisonReport,
    EvaluationVerdict,
    HarnessSummary,
    RunMetrics,
    VerdictType,
)


class ComparisonEngine:
    """Computes transparent metric deltas and derives human-readable verdicts."""

    def __init__(
        self,
        min_pass_rate_delta: float = 0.05,
        regression_tolerance: float = -0.02,
        cost_tradeoff_threshold: float = 0.25,
    ):
        self.min_pass_rate_delta = min_pass_rate_delta
        self.regression_tolerance = regression_tolerance
        self.cost_tradeoff_threshold = cost_tradeoff_threshold

    def summarize_harness(self, harness_name: str, runs: List[RunMetrics]) -> HarnessSummary:
        h_runs = [r for r in runs if r.harness_name == harness_name]
        total_runs = len(h_runs)
        if total_runs == 0:
            raise ValueError(f"No runs recorded for harness: {harness_name}")

        successful_runs = sum(1 for r in h_runs if r.exit_code == 0 and r.pass_rate == 1.0)
        mean_pass_rate = statistics.mean([r.pass_rate for r in h_runs])

        all_req_checks = [val for r in h_runs for val in r.requirement_results.values()]
        mean_req_sat = (sum(1 for v in all_req_checks if v) / len(all_req_checks)) if all_req_checks else 0.0

        ruff_passes = sum(1 for r in h_runs if r.quality.ruff_passed)
        mypy_passes = sum(1 for r in h_runs if r.quality.mypy_passed)

        token_runs = [r.total_tokens for r in h_runs if r.total_tokens is not None]
        mean_tokens = statistics.mean(token_runs) if token_runs else None

        cost_runs = [r.estimated_cost_usd for r in h_runs if r.estimated_cost_usd is not None]
        total_cost = sum(cost_runs) if cost_runs else None

        return HarnessSummary(
            harness_name=harness_name,
            total_runs=total_runs,
            successful_runs=successful_runs,
            run_success_rate=round(successful_runs / total_runs, 3),
            mean_pass_rate=round(mean_pass_rate, 3),
            mean_requirement_satisfaction=round(mean_req_sat, 3),
            ruff_pass_rate=round(ruff_passes / total_runs, 3),
            mypy_pass_rate=round(mypy_passes / total_runs, 3),
            mean_duration_seconds=round(statistics.mean([r.duration_seconds for r in h_runs]), 2),
            mean_tokens=round(mean_tokens, 1) if mean_tokens is not None else None,
            total_estimated_cost=round(total_cost, 4) if total_cost is not None else None,
        )

    def compare(
        self,
        baseline_summary: HarnessSummary,
        candidate_summary: HarnessSummary,
        raw_runs: List[RunMetrics],
    ) -> ComparisonReport:
        pass_delta = round(candidate_summary.mean_pass_rate - baseline_summary.mean_pass_rate, 3)
        req_delta = round(
            candidate_summary.mean_requirement_satisfaction - baseline_summary.mean_requirement_satisfaction,
            3,
        )
        dur_delta = round(candidate_summary.mean_duration_seconds - baseline_summary.mean_duration_seconds, 2)

        cost_delta_pct: Optional[float] = None
        if candidate_summary.total_estimated_cost is not None and baseline_summary.total_estimated_cost is not None:
            base_cost = baseline_summary.total_estimated_cost
            cand_cost = candidate_summary.total_estimated_cost
            if base_cost > 0:
                cost_delta_pct = round(((cand_cost - base_cost) / base_cost) * 100, 2)

        verdict = self._evaluate_verdict(pass_delta, req_delta, cost_delta_pct, candidate_summary, baseline_summary)

        return ComparisonReport(
            baseline_summary=baseline_summary,
            candidate_summary=candidate_summary,
            pass_rate_delta=pass_delta,
            req_satisfaction_delta=req_delta,
            cost_delta_percentage=cost_delta_pct,
            duration_delta_seconds=dur_delta,
            verdict=verdict,
            raw_runs=raw_runs,
        )

    def _evaluate_verdict(
        self,
        pass_delta: float,
        req_delta: float,
        cost_delta_pct: Optional[float],
        candidate: HarnessSummary,
        baseline: HarnessSummary,
    ) -> EvaluationVerdict:
        reasons: List[str] = []
        thresholds = {
            "min_pass_rate_delta": self.min_pass_rate_delta,
            "regression_tolerance": self.regression_tolerance,
            "cost_tradeoff_threshold_pct": self.cost_tradeoff_threshold * 100,
        }

        if pass_delta < self.regression_tolerance or req_delta < self.regression_tolerance:
            reasons.append(f"Pass rate dropped by {pass_delta * 100:.1f} percentage points.")
            if req_delta < self.regression_tolerance:
                reasons.append(f"Requirement satisfaction dropped by {req_delta * 100:.1f} percentage points.")
            return EvaluationVerdict(
                verdict=VerdictType.NEGATIVE,
                summary_reason="Candidate harness caused a measurable regression in correctness.",
                detailed_reasons=reasons,
                thresholds_applied=thresholds,
            )

        is_improved = pass_delta >= self.min_pass_rate_delta or req_delta >= self.min_pass_rate_delta
        if is_improved:
            reasons.append(
                f"Correctness improved: pass rate Δ={pass_delta * 100:+.1f}%, requirements Δ={req_delta * 100:+.1f}%."
            )
            if candidate.ruff_pass_rate > baseline.ruff_pass_rate:
                reasons.append(
                    f"Ruff compliance improved (+{(candidate.ruff_pass_rate - baseline.ruff_pass_rate) * 100:.1f}%)."
                )

            if cost_delta_pct is not None and cost_delta_pct > (self.cost_tradeoff_threshold * 100):
                reasons.append(f"Token cost increased significantly (+{cost_delta_pct:.1f}%).")
                return EvaluationVerdict(
                    verdict=VerdictType.POSITIVE_WITH_COST_TRADEOFF,
                    summary_reason="Candidate improved correctness and requirements but incurred substantial cost overhead.",
                    detailed_reasons=reasons,
                    thresholds_applied=thresholds,
                )

            return EvaluationVerdict(
                verdict=VerdictType.POSITIVE,
                summary_reason="Candidate delivered measurable improvements in code correctness within acceptable cost boundaries.",
                detailed_reasons=reasons,
                thresholds_applied=thresholds,
            )

        reasons.append(
            f"Pass rate change ({pass_delta * 100:+.1f}%) is within noise margin (±{self.min_pass_rate_delta * 100:.1f}%)."
        )
        return EvaluationVerdict(
            verdict=VerdictType.INCONCLUSIVE,
            summary_reason="Observed delta between harnesses is statistically insignificant or insufficient.",
            detailed_reasons=reasons,
            thresholds_applied=thresholds,
        )
