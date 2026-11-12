"""Versioned public HTTP contracts."""

from typing import Any, Literal

from portfolio_rl.config import TrainingConfig
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ExperimentConfig(Contract):
    name: str = Field(min_length=1, max_length=80)
    strategy: Literal["equal_weight", "markowitz", "ppo", "ddpg"] = "equal_weight"
    dataset_id: str = Field(
        default="fixture-v1", pattern=r"^(fixture-v1|historical-[a-f0-9]{12,64})$"
    )
    initial_capital: float = Field(default=10000, gt=0, le=1e9, strict=True)
    transaction_cost_bps: float = Field(default=10, ge=0, le=100, strict=True)
    risk_free_rate: float = Field(default=0, ge=-0.99, le=1, strict=True)
    seed: int = Field(default=42, ge=0, le=2147483647, strict=True)
    split: Literal["train", "validation"] = "validation"
    lookback: int = Field(default=60, ge=2, le=252, strict=True)
    risk_aversion: float = Field(default=5, gt=0, le=10000, strict=True)
    model_id: str | None = Field(
        default=None, pattern=r"^[a-f0-9-]{36}$", exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def compatible_strategy(self) -> "ExperimentConfig":
        if self.dataset_id == "fixture-v1" and self.strategy != "equal_weight":
            raise ValueError("Markowitz requires a verified historical snapshot")
        if self.strategy in {"ppo", "ddpg"} and (
            self.model_id is None or self.split != "validation"
        ):
            raise ValueError("RL replay requires a saved model and validation split")
        if self.strategy not in {"ppo", "ddpg"} and self.model_id is not None:
            raise ValueError("A model is only used by PPO/DDPG")
        return self

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must contain a non-whitespace character")
        return value


class Dataset(Contract):
    id: str
    kind: Literal["FIXTURE", "HISTORICAL"]
    source: str
    sha256: str
    assets: list[str]
    start_date: str
    end_date: str
    observations: int
    provenance: dict[str, Any] = Field(default_factory=dict)
    quality_report: dict[str, Any] = Field(default_factory=dict)
    splits: dict[str, Any] = Field(default_factory=dict)


class Metrics(Contract):
    cumulative_return: float
    annualized_volatility: float | None
    sharpe_ratio: float | None
    max_drawdown: float
    final_equity: float
    total_costs: float


class EquityPoint(Contract):
    date: str
    equity: float
    net_return: float


class Allocation(Contract):
    date: str
    weights: dict[str, float]
    turnover: float
    cost: float


class AuditEvent(Contract):
    date: str
    event: str
    detail: str


class Result(Contract):
    metrics: Metrics
    equity: list[EquityPoint]
    allocations: list[Allocation]
    audit: list[AuditEvent]
    manifest: dict[str, Any]


class Experiment(Contract):
    id: str
    name: str
    status: Literal["queued", "running", "completed", "failed"]
    created_at: str
    completed_at: str | None
    config: ExperimentConfig
    dataset: Dataset
    result: Result | None
    error: str | None


class ExperimentList(Contract):
    items: list[Experiment]


class DatasetList(Contract):
    items: list[Dataset]


class Health(Contract):
    status: Literal["ok"] = "ok"
    service: Literal["portfolio-ai-lab-api"] = "portfolio-ai-lab-api"
    mode: Literal["PAPER"] = "PAPER"


class Ready(Contract):
    status: Literal["ready"] = "ready"
    mode: Literal["PAPER"] = "PAPER"


class TrainingRequest(TrainingConfig):
    dataset_id: str = Field(pattern=r"^historical-[a-f0-9]{12,64}$")
    resume_from_job_id: str | None = Field(default=None, pattern=r"^[a-f0-9-]{36}$")


class TrainingJob(Contract):
    id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    config: TrainingConfig
    dataset: Dataset
    progress: dict[str, Any] = Field(default_factory=dict)
    manifest: dict[str, Any] | None = None
    evaluation: dict[str, Any] | None = None
    error: str | None = None
    cancel_requested: bool = False
    resume_from_job_id: str | None = None


class TrainingJobList(Contract):
    items: list[TrainingJob]


class ModelInfo(Contract):
    id: str
    algorithm: Literal["ppo", "ddpg"]
    dataset_id: str
    seed: int
    timesteps: int
    training_end: str
    lookback: int
    initial_capital: float
    transaction_cost_bps: float
    risk_free_rate: float
    validation_metrics: dict[str, Any] | None = None


class ModelList(Contract):
    items: list[ModelInfo]


class ComparisonItem(Contract):
    algorithm: Literal["ppo", "ddpg", "markowitz", "equal_weight"]
    model_id: str | None
    seed: int | None
    timesteps: int | None
    metrics: Metrics
    research_metrics: dict[str, Any]


class ComparisonReport(Contract):
    items: list[ComparisonItem]
    methodology: str
    holdout_2024_evaluated: bool = False
