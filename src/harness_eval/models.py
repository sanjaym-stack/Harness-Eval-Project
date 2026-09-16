"""Domain models and schemas for harness evaluation."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VerdictType(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    POSITIVE_WITH_COST_TRADEOFF = "POSITIVE WITH COST TRADE-OFF"
    INCONCLUSIVE = "INCONCLUSIVE"


class RequirementSpec(BaseModel):
    id: str
    description: str
    check_type: str = "pytest"
    target: str


class TaskSpec(BaseModel):
    id: str
    name: str
    description: str
    prompt_file: str = "prompt.md"
    eval_test_file: str = "test_eval.py"
    requirements: List[RequirementSpec] = Field(default_factory=list)


class QualityMetrics(BaseModel):
    ruff_passed: bool
    ruff_violations: int
    mypy_passed: bool
    mypy_errors: int


class RunMetrics(BaseModel):
    task_id: str
    harness_name: str
    run_index: int
    exit_code: int
    duration_seconds: float
    tests_passed: int
    tests_failed: int
    tests_total: int
    pass_rate: float
    requirement_results: Dict[str, bool] = Field(default_factory=dict)
    quality: QualityMetrics
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    is_mock: bool = False
    error_message: Optional[str] = None


class HarnessSummary(BaseModel):
    harness_name: str
    total_runs: int
    successful_runs: int
    run_success_rate: float
    mean_pass_rate: float
    mean_requirement_satisfaction: float
    ruff_pass_rate: float
    mypy_pass_rate: float
    mean_duration_seconds: float
    mean_tokens: Optional[float] = None
    total_estimated_cost: Optional[float] = None


class EvaluationVerdict(BaseModel):
    verdict: VerdictType
    summary_reason: str
    detailed_reasons: List[str]
    thresholds_applied: Dict[str, Any]


class ComparisonReport(BaseModel):
    baseline_summary: HarnessSummary
    candidate_summary: HarnessSummary
    pass_rate_delta: float
    req_satisfaction_delta: float
    cost_delta_percentage: Optional[float]
    duration_delta_seconds: float
    verdict: EvaluationVerdict
    raw_runs: List[RunMetrics]
