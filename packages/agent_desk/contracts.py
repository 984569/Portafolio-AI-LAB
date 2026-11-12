"""Strict contracts for the Agent Desk, shared across the API and agents."""

from datetime import date
from typing import Annotated, Any, Literal, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Strategy = Literal["equal_weight", "markowitz", "ppo", "ddpg"]
Stage = Literal["data", "analyst", "strategist", "judge", "risk", "final"]
Decision = Literal["approved", "watch", "rejected", "blocked"]
Finite = Annotated[float, Field(allow_inf_nan=False)]
SnapshotId = Annotated[str, Field(pattern=r"^historical-[a-f0-9]{64}$")]
Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
ModelId = Annotated[str, Field(pattern=r"^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$")]


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, frozen=True)


class DeskRequest(StrictContract):
    dataset_id: SnapshotId
    decision_date: str
    strategy: Strategy
    model_id: ModelId | None = None

    @field_validator("decision_date")
    @classmethod
    def development_date(cls, value: str) -> str:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or parsed.year not in {2022, 2023}:
            raise ValueError("Use a canonical 2022–2023 decision date")
        return value

    @model_validator(mode="after")
    def model_matches_strategy(self) -> "DeskRequest":
        if (self.strategy in {"ppo", "ddpg"}) != (self.model_id is not None):
            raise ValueError("A saved model ID is required only for PPO or DDPG")
        return self


class Dossier(StrictContract):
    dataset_id: SnapshotId
    dataset_sha256: Hash
    decision_date: str
    information_date: str
    assets: list[str]
    observations: int
    lookback: int
    market_return: Finite
    market_volatility: Finite


class Candidate(StrictContract):
    strategy: Strategy
    model_id: ModelId | None = None
    weights: dict[str, Finite]
    annualized_volatility: Finite
    turnover: Finite
    fee_bps: Finite
    optimizer_fallback: bool = False


class Analysis(StrictContract):
    trend: Literal["up", "down", "mixed"]
    regime: Literal["low", "moderate", "high"]
    evidence: list[Literal["market_return", "market_volatility"]] = Field(
        min_length=1, max_length=2
    )


class Judgment(StrictContract):
    verdict: Literal["approve", "watch", "reject"]
    reason: Literal["aligned", "concentration", "volatility", "caution"]
    evidence: list[
        Literal["market_return", "market_volatility", "weights", "turnover", "portfolio_volatility"]
    ] = Field(min_length=1, max_length=5)


class ProviderTrace(StrictContract):
    provider: Literal["openrouter", "mock"]
    model: str
    endpoint_provider: str | None = None
    stage: str
    attempts: int
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    elapsed_ms: int
    config: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class ProviderError(Exception):
    def __init__(self, code: str, trace: ProviderTrace | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.trace = trace


Response = TypeVar("Response", bound=BaseModel)


class Provider(Protocol):
    @property
    def provider(self) -> Literal["openrouter", "mock"]: ...

    @property
    def model(self) -> str: ...

    @property
    def endpoint_provider(self) -> str | None: ...

    def complete(
        self, stage: str, payload: dict[str, Any], schema: type[Response]
    ) -> tuple[Response, ProviderTrace]: ...


class Gate(StrictContract):
    name: str
    passed: bool
    reason_code: str
    observed: Finite | str | None = None
    threshold: Finite | str | None = None
    decision_date: str


class RiskReport(StrictContract):
    passed: bool
    gates: list[Gate]
    policy_version: str = "desk-cash-v1"

    @model_validator(mode="after")
    def matches_gates(self) -> "RiskReport":
        if self.passed != (bool(self.gates) and all(gate.passed for gate in self.gates)):
            raise ValueError("Risk verdict must match the deterministic gates")
        return self


class DeskEvent(StrictContract):
    stage: Stage
    status: Literal["completed", "blocked"]
    code: str
    payload: dict[str, Any] = Field(default_factory=dict)
    provider: ProviderTrace | None = None


class DeskOutcome(StrictContract):
    decision: Decision
    code: str
    dossier: Dossier | None = None
    analysis: Analysis | None = None
    candidate: Candidate | None = None
    judgment: Judgment | None = None
    risk: RiskReport | None = None

    @model_validator(mode="after")
    def requires_judgment_and_risk(self) -> "DeskOutcome":
        if self.decision == "blocked":
            return self
        verdict = {"approved": "approve", "watch": "watch", "rejected": "reject"}[self.decision]
        if (
            self.dossier is None
            or self.analysis is None
            or self.candidate is None
            or self.judgment is None
            or self.judgment.verdict != verdict
            or self.risk is None
            or not self.risk.passed
        ):
            raise ValueError("A verified judgment and risk pass are required")
        return self
