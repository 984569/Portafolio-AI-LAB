"""Causal market analysis and one paper allocation proposal through a closed state flow."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Any, TypeVar

import numpy as np
from exchange_calendars import get_calendar
from market_data import UNIVERSE
from numpy.typing import NDArray
from portfolio_core import PricePanel, project_simplex
from portfolio_research import markowitz_weights
from pydantic import BaseModel

from .contracts import (
    Analysis,
    Candidate,
    Decision,
    DeskEvent,
    DeskOutcome,
    DeskRequest,
    Dossier,
    Judgment,
    Provider,
    ProviderError,
    ProviderTrace,
    Stage,
)
from .risk import evaluate_dossier, evaluate_risk

if TYPE_CHECKING:
    from portfolio_rl.common import PolicyBundle


CLASSICAL_LOOKBACK = 60
SCENARIO_FEE_BPS = 10.0
ANNUALIZATION = 252
CASH_TARGET_TURNOVER = 1.0
FloatArray = NDArray[np.float64]
Response = TypeVar("Response", bound=BaseModel)


@dataclass(frozen=True)
class MarketWindow:
    dossier: Dossier
    simple_returns: FloatArray
    log_returns: FloatArray


def _model_lookback(request: DeskRequest, panel: PricePanel, bundle: PolicyBundle | None) -> int:
    if request.strategy in {"markowitz", "equal_weight"}:
        if bundle is not None or request.model_id is not None:
            raise ValueError("Classical strategies do not use a model artifact")
        return CLASSICAL_LOOKBACK
    if bundle is None or request.model_id is None:
        raise ValueError("A verified model is required")
    manifest = bundle.manifest
    configuration = manifest["configuration"]
    fit_end = manifest["training_end"]
    fit_date = date.fromisoformat(fit_end)
    lookback = configuration["lookback"]
    if (
        manifest.get("status") != "completed"
        or manifest.get("mode") != "PAPER"
        or manifest.get("data_mode") != "HISTORICAL"
        or manifest.get("validation_used_for_training") is not False
        or manifest.get("holdout_2024_used") is not False
        or configuration.get("algorithm") != request.strategy
        or configuration.get("dataset_id") != request.dataset_id
        or configuration.get("transaction_cost_bps") != SCENARIO_FEE_BPS
        or manifest.get("dataset_sha256") != panel.metadata.get("sha256")
        or manifest.get("normalization_fit_end") != fit_end
        or bundle.normalizer.fit_end != fit_end
        or fit_end != fit_date.isoformat()
        or not date(2015, 1, 1) <= fit_date <= date(2021, 12, 31)
        or fit_date >= date.fromisoformat(str(request.decision_date))
        or type(lookback) is not int
        or not 2 <= lookback <= 120
    ):
        raise ValueError("Model provenance or training window mismatch")
    return lookback


def _market_window(request: DeskRequest, panel: PricePanel, lookback: int) -> MarketWindow:
    decision = str(request.decision_date)
    decision_date = date.fromisoformat(decision)
    digest = panel.metadata.get("sha256")
    if (
        decision != decision_date.isoformat()
        or not date(2022, 1, 1) <= decision_date <= date(2023, 12, 31)
        or panel.metadata.get("kind") != "HISTORICAL"
        or panel.metadata.get("id") != request.dataset_id
        or not isinstance(digest, str)
        or request.dataset_id != f"historical-{digest}"
        or panel.assets != UNIVERSE
    ):
        raise ValueError("Decision date, snapshot identity or universe mismatch")
    index = bisect_left(panel.dates, decision)
    if index < lookback or index >= len(panel.dates) or panel.dates[index] != decision:
        raise ValueError("The decision close or required warmup is unavailable")
    expected = tuple(
        stamp.date().isoformat()
        for stamp in get_calendar("XNYS").sessions_window(decision, -(lookback + 1))
    )
    if panel.dates[index - lookback : index + 1] != expected:
        raise ValueError("The lookback does not match consecutive XNYS sessions")

    prices = panel.prices[index - lookback : index + 1]
    with np.errstate(over="raise", divide="raise", invalid="raise"):
        simple = prices[1:] / prices[:-1] - 1.0
        logs = np.diff(np.log(prices), axis=0)
        market = np.mean(simple, axis=1)
        market_return = float(np.prod(1.0 + market) - 1.0)
        market_volatility = float(np.std(market, ddof=1) * np.sqrt(ANNUALIZATION))
    dossier = Dossier(
        dataset_id=request.dataset_id,
        dataset_sha256=digest,
        decision_date=request.decision_date,
        information_date=request.decision_date,
        assets=list(panel.assets),
        observations=len(prices),
        lookback=lookback,
        market_return=market_return,
        market_volatility=market_volatility,
    )
    return MarketWindow(dossier, simple, logs)


def quant_strategist(
    request: DeskRequest, window: MarketWindow, bundle: PolicyBundle | None
) -> Candidate:
    assets = window.dossier.assets
    fallback = False
    if request.strategy == "equal_weight":
        weights = np.full(len(assets), 1.0 / len(assets), dtype=np.float64)
    elif request.strategy == "markowitz":
        decision = markowitz_weights(window.simple_returns)
        weights, fallback = decision.weights, decision.used_fallback
    else:
        if bundle is None:
            raise ValueError("A verified model is required")
        # The Gym reset observation has the lagged log returns and zero target
        # weights (cash). There is no step, execution close or subsequent return.
        observation = np.concatenate([window.log_returns.ravel(), np.zeros(len(assets))])
        if not np.isfinite(observation).all() or (np.abs(observation) > 2000).any():
            raise ValueError("Observation violates Gym bounds")
        action = bundle.predict(observation.astype(np.float32), deterministic=True)
        if (
            action.shape != (len(assets),)
            or not np.isfinite(action).all()
            or (np.abs(action) > 1).any()
        ):
            raise ValueError("Policy action violates its Gym action space")
        weights = project_simplex(action)
    with np.errstate(over="raise", invalid="raise"):
        annualized_volatility = float(
            np.std(window.simple_returns @ weights, ddof=1) * np.sqrt(ANNUALIZATION)
        )
    return Candidate(
        strategy=request.strategy,
        model_id=request.model_id,
        weights=dict(zip(assets, map(float, weights), strict=True)),
        annualized_volatility=annualized_volatility,
        # The pre-fee unit target is acquired entirely from cash. The risk
        # engine separately validates the weights' sum to machine tolerance.
        turnover=CASH_TARGET_TURNOVER,
        fee_bps=SCENARIO_FEE_BPS,
        optimizer_fallback=fallback,
    )


def _facts(dossier: Dossier) -> dict[str, Any]:
    # Explicit allowlist: no provider text, metadata, user text or raw news.
    return {
        "lookback": dossier.lookback,
        "market_return": dossier.market_return,
        "market_volatility": dossier.market_volatility,
    }


def _provider_call(
    provider: Provider, stage: str, payload: dict[str, Any], schema: type[Response]
) -> tuple[Response, ProviderTrace]:
    response, trace = provider.complete(stage, payload, schema)
    try:
        # Enforce the exact response schema even for injected test providers.
        if type(response) is not schema:
            raise TypeError("Unexpected structured response")
        return schema.model_validate(response.model_dump(mode="python"), strict=True), trace
    except (ValueError, TypeError) as exc:
        raise ProviderError("provider_invalid_output", trace) from exc


def market_analyst(dossier: Dossier, provider: Provider) -> tuple[Analysis, ProviderTrace]:
    return _provider_call(provider, "analyst", _facts(dossier), Analysis)


def portfolio_judge(
    dossier: Dossier, analysis: Analysis, candidate: Candidate, provider: Provider
) -> tuple[Judgment, ProviderTrace]:
    payload = {
        **_facts(dossier),
        "analysis": analysis.model_dump(mode="json"),
        "strategy": candidate.strategy,
        "weights": candidate.weights.copy(),
        "turnover": candidate.turnover,
        "portfolio_volatility": candidate.annualized_volatility,
    }
    return _provider_call(provider, "judge", payload, Judgment)


def run_workflow(
    request: DeskRequest,
    panel: PricePanel,
    provider: Provider,
    emit: Callable[[DeskEvent], None],
    *,
    bundle: PolicyBundle | None = None,
) -> DeskOutcome:
    """Chief Orchestrator. Approval requires a closed verdict and all hard gates."""
    dossier: Dossier | None = None
    analysis: Analysis | None = None
    candidate: Candidate | None = None
    judgment: Judgment | None = None

    def finish(decision: Decision, code: str, *, provider_ok: bool) -> DeskOutcome:
        risk = evaluate_risk(
            dossier, candidate, provider_ok=provider_ok, decision_date=request.decision_date
        )
        emit(
            DeskEvent(
                stage="risk",
                status="completed" if risk.passed else "blocked",
                code="risk_passed" if risk.passed else "risk_veto",
                payload=risk.model_dump(mode="json"),
            )
        )
        if not risk.passed and decision != "blocked":
            decision, code = "blocked", "risk_veto"
        emit(
            DeskEvent(
                stage="final",
                status="blocked" if decision == "blocked" else "completed",
                code=code,
                payload={"decision": decision},
            )
        )
        return DeskOutcome(
            decision=decision,
            code=code,
            dossier=dossier,
            analysis=analysis,
            candidate=candidate,
            judgment=judgment,
            risk=risk,
        )

    def abort(
        stage: Stage, code: str, *, provider_ok: bool, trace: ProviderTrace | None = None
    ) -> DeskOutcome:
        emit(DeskEvent(stage=stage, status="blocked", code=code, provider=trace))
        return finish("blocked", code, provider_ok=provider_ok)

    try:
        lookback = _model_lookback(request, panel, bundle)
        window = _market_window(request, panel, lookback)
        dossier = window.dossier
    except (ValueError, TypeError, KeyError, AttributeError, FloatingPointError):
        return abort("data", "invalid_input", provider_ok=False)
    preflight = evaluate_dossier(dossier, decision_date=request.decision_date)
    if not preflight.passed:
        return abort("data", "ineligible_dossier", provider_ok=False)
    emit(
        DeskEvent(
            stage="data",
            status="completed",
            code="dossier_verified",
            payload=dossier.model_dump(mode="json"),
        )
    )

    try:
        analysis, analyst_trace = market_analyst(dossier, provider)
    except ProviderError as error:
        return abort("analyst", _provider_code(error.code), provider_ok=False, trace=error.trace)
    except Exception:
        return abort("analyst", "provider_error", provider_ok=False)
    emit(
        DeskEvent(
            stage="analyst",
            status="completed",
            code="analysis_validated",
            payload=analysis.model_dump(mode="json"),
            provider=analyst_trace,
        )
    )

    try:
        candidate = quant_strategist(request, window, bundle)
        strategist_payload = candidate.model_dump(mode="json")
        if bundle is not None:
            strategist_payload["artifact"] = {
                "training_end": bundle.manifest["training_end"],
                "normalization_fit_end": bundle.manifest["normalization_fit_end"],
                "files": bundle.manifest["files"],
            }
    except Exception:
        return abort("strategist", "invalid_candidate", provider_ok=True)
    emit(
        DeskEvent(
            stage="strategist",
            status="completed",
            code="candidate_computed",
            payload=strategist_payload,
        )
    )

    try:
        judgment, judge_trace = portfolio_judge(dossier, analysis, candidate, provider)
    except ProviderError as error:
        return abort("judge", _provider_code(error.code), provider_ok=False, trace=error.trace)
    except Exception:
        return abort("judge", "provider_error", provider_ok=False)
    emit(
        DeskEvent(
            stage="judge",
            status="completed",
            code=f"judge_{judgment.verdict}",
            payload=judgment.model_dump(mode="json"),
            provider=judge_trace,
        )
    )

    if judgment.verdict == "approve":
        return finish("approved", "judge_approve", provider_ok=True)
    if judgment.verdict == "watch":
        return finish("watch", "judge_watch", provider_ok=True)
    return finish("rejected", "judge_reject", provider_ok=True)


def _provider_code(code: str) -> str:
    # Never persist arbitrary provider bodies or exception text in event codes.
    if code in {
        "provider_configuration",
        "provider_quota",
        "provider_timeout",
        "provider_unavailable",
        "provider_rate_limited",
        "provider_auth",
        "provider_capability",
        "provider_http",
        "provider_invalid_response",
        "provider_transport",
        "provider_invalid_stage",
        "provider_invalid_input",
        "provider_route_mismatch",
        "provider_invalid_output",
    }:
        return code
    return "provider_error"
