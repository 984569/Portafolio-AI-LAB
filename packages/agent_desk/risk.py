"""Deterministic and auditable gates for a single historical allocation from cash."""

import math
import re
from datetime import date
from functools import lru_cache

import exchange_calendars as xcals
from market_data import UNIVERSE

from .contracts import Candidate, Dossier, Gate, RiskReport

MAX_POSITION = 0.35
MAX_ANNUALIZED_VOLATILITY = 0.30
CASH_TURNOVER = 1.0
TRANSACTION_FEE_BPS = 10.0
WEIGHT_SUM_TOLERANCE = 1e-8
MIN_LOOKBACK = 2
MAX_LOOKBACK = 120


@lru_cache(maxsize=1)
def _decision_sessions() -> frozenset[str]:
    calendar = xcals.get_calendar("XNYS", start="2022-01-01", end="2023-12-31")
    return frozenset(stamp.date().isoformat() for stamp in calendar.sessions)


def _canonical_date(value: object) -> str:
    """Preserve canonical requested dates in audit and discard arbitrary text."""
    if not isinstance(value, str):
        return ""
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return ""
    return value if parsed.isoformat() == value else ""


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _gate(
    name: str,
    day: str,
    passed: bool,
    reason_code: str,
    *,
    observed: float | str | None = None,
    threshold: float | str | None = None,
) -> Gate:
    return Gate(
        name=name,
        passed=passed,
        reason_code="ok" if passed else reason_code,
        observed=observed,
        threshold=threshold,
        decision_date=day,
    )


def _report(gates: list[Gate]) -> RiskReport:
    return RiskReport(passed=all(gate.passed for gate in gates), gates=gates)


def _temporal_code(day: str, information_date: str, expected_date: str) -> str:
    if not day:
        return "invalid_decision_date"
    if day.startswith("2024-"):
        return "holdout_locked"
    if not "2022-01-01" <= day <= "2023-12-31":
        return "decision_outside_validation"
    if expected_date and day != expected_date:
        return "decision_date_mismatch"
    if day not in _decision_sessions():
        return "decision_not_xnys_session"
    if _canonical_date(information_date) != day:
        return "information_date_mismatch"
    return "ok"


def evaluate_dossier(dossier: Dossier | None, *, decision_date: str = "") -> RiskReport:
    """Check the numeric fact dossier before it can cross the provider boundary."""
    if dossier is None:
        return _report([_gate("dossier", _canonical_date(decision_date), False, "missing_dossier")])
    day = _canonical_date(dossier.decision_date)
    temporal = _temporal_code(day, dossier.information_date, decision_date)
    snapshot_ok = (
        isinstance(dossier.dataset_sha256, str)
        and re.fullmatch("[a-f0-9]{64}", dossier.dataset_sha256) is not None
        and dossier.dataset_id == f"historical-{dossier.dataset_sha256}"
    )
    coverage_ok = (
        type(dossier.lookback) is int
        and MIN_LOOKBACK <= dossier.lookback <= MAX_LOOKBACK
        and type(dossier.observations) is int
        and dossier.observations == dossier.lookback + 1
    )
    market_return = _finite(dossier.market_return)
    market_volatility = _finite(dossier.market_volatility)
    return _report(
        [
            _gate("snapshot", day, snapshot_ok, "invalid_snapshot_identity"),
            _gate(
                "chronology",
                day,
                temporal == "ok",
                temporal,
                observed=_canonical_date(dossier.information_date) or None,
                threshold="Same XNYS close in 2022–2023",
            ),
            _gate(
                "dossier_universe",
                day,
                isinstance(dossier.assets, list) and dossier.assets == list(UNIVERSE),
                "invalid_dossier_universe",
            ),
            _gate(
                "coverage",
                day,
                coverage_ok,
                "incomplete_lookback",
                observed=_finite(dossier.observations),
                threshold="lookback + 1 closes; 2–120 returns",
            ),
            _gate(
                "market_return",
                day,
                market_return is not None and market_return > -1,
                "invalid_market_return",
                observed=market_return,
                threshold="finite and greater than −1",
            ),
            _gate(
                "market_volatility",
                day,
                market_volatility is not None and market_volatility >= 0,
                "invalid_market_volatility",
                observed=market_volatility,
                threshold="finite and nonnegative",
            ),
        ]
    )


def _candidate_gates(candidate: Candidate, day: str) -> list[Gate]:
    model_id_ok = (
        isinstance(candidate.model_id, str)
        and re.fullmatch("[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}", candidate.model_id)
        is not None
    )
    strategy_ok = (
        (candidate.strategy in ("ppo", "ddpg") and model_id_ok)
        or (candidate.strategy in ("equal_weight", "markowitz") and candidate.model_id is None)
    ) and (
        type(candidate.optimizer_fallback) is bool
        and (not candidate.optimizer_fallback or candidate.strategy == "markowitz")
    )
    universe_ok = isinstance(candidate.weights, dict) and set(candidate.weights) == set(UNIVERSE)
    numbers = [_finite(candidate.weights[asset]) for asset in UNIVERSE] if universe_ok else []
    weights = [weight for weight in numbers if weight is not None and 0 <= weight <= 1]
    weights_ok = len(weights) == len(UNIVERSE)
    total = math.fsum(weights) if weights_ok else None
    maximum = max(weights) if weights_ok else None
    volatility = _finite(candidate.annualized_volatility)
    turnover = _finite(candidate.turnover)
    fees = _finite(candidate.fee_bps)
    return [
        _gate("strategy", day, strategy_ok, "invalid_strategy_provenance"),
        _gate("proposal_universe", day, universe_ok, "invalid_proposal_universe"),
        _gate("long_only", day, weights_ok, "invalid_weight", threshold="Each weight in [0, 1]"),
        _gate(
            "full_investment",
            day,
            total is not None and abs(total - 1.0) <= WEIGHT_SUM_TOLERANCE,
            "weights_do_not_sum_to_one",
            observed=total,
            threshold=1.0,
        ),
        _gate(
            "position_limit",
            day,
            maximum is not None and maximum <= MAX_POSITION,
            "position_limit_exceeded" if maximum is not None else "invalid_weights",
            observed=maximum,
            threshold=MAX_POSITION,
        ),
        _gate(
            "portfolio_volatility",
            day,
            volatility is not None and 0 <= volatility <= MAX_ANNUALIZED_VOLATILITY,
            "volatility_limit_exceeded"
            if volatility is not None and volatility > MAX_ANNUALIZED_VOLATILITY
            else "invalid_portfolio_volatility",
            observed=volatility,
            threshold=MAX_ANNUALIZED_VOLATILITY,
        ),
        _gate(
            "cash_turnover",
            day,
            turnover == CASH_TURNOVER,
            "invalid_cash_turnover",
            observed=turnover,
            threshold=CASH_TURNOVER,
        ),
        _gate(
            "fee_assumption",
            day,
            fees == TRANSACTION_FEE_BPS,
            "invalid_fee_assumption",
            observed=fees,
            threshold=TRANSACTION_FEE_BPS,
        ),
    ]


def evaluate_risk(
    dossier: Dossier | None,
    candidate: Candidate | None,
    *,
    provider_ok: bool,
    decision_date: str = "",
) -> RiskReport:
    """Veto malformed, incomplete, out-of-policy, or provider-failed proposals."""
    day = _canonical_date(dossier.decision_date if dossier is not None else decision_date)
    gates = evaluate_dossier(dossier, decision_date=decision_date).gates
    gates.append(_gate("provider", day, provider_ok is True, "provider_unverified"))
    if candidate is None:
        gates.append(_gate("candidate", day, False, "missing_candidate"))
    else:
        gates.extend(_candidate_gates(candidate, day))
    return _report(gates)
