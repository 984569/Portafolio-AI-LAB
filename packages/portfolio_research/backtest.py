"""Historical replay with a strict one-close information lag and exact fees."""

import math
from importlib.metadata import version
from typing import Any

import numpy as np
from numpy.typing import NDArray
from portfolio_core import PricePanel, financial_metrics, rebalance_step

from .markowitz import (
    ANNUALIZATION,
    COVARIANCE_RIDGE,
    SOLVER_FTOL,
    SOLVER_MAXITER,
    markowitz_weights,
)

ENGINE_VERSION = "0.2.0"
SPLITS = {"train": ("2015-01-01", "2021-12-31"), "validation": ("2022-01-01", "2023-12-31")}
FIELDS = {
    "name", "strategy", "dataset_id", "initial_capital", "transaction_cost_bps",
    "risk_free_rate", "seed", "split", "lookback", "risk_aversion",
}


def _number(value: Any, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result) or not low <= result <= high:
        raise ValueError(f"{name} is outside its finite supported range")
    return result


def _configuration(panel: PricePanel, config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(config, dict) or set(config) - FIELDS:
        raise ValueError("Unsupported historical experiment configuration fields")
    name = config.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or len(name) > 80:
        raise ValueError("name must contain 1 to 80 characters")
    strategy = config.get("strategy", "equal_weight")
    if strategy not in {"equal_weight", "markowitz"}:
        raise ValueError("Only equal_weight and markowitz are implemented")
    split = config.get("split", "validation")
    if split not in SPLITS:
        raise ValueError("Only train and validation are allowed; 2024 remains locked")
    lookback = config.get("lookback", 60)
    if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 2:
        raise ValueError("lookback must be an integer of at least two returns")
    seed = config.get("seed", 42)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2147483647:
        raise ValueError("seed must be an integer between 0 and 2147483647")
    capital = _number(config.get("initial_capital", 10000), "initial_capital", 0, 1e9)
    if capital <= 0:
        raise ValueError("initial_capital must be positive")
    risk_aversion = _number(config.get("risk_aversion", 5), "risk_aversion", 0, 1e12)
    if risk_aversion <= 0:
        raise ValueError("risk_aversion must be positive")
    dataset_id = config.get("dataset_id", panel.metadata.get("id"))
    if dataset_id != panel.metadata.get("id"):
        raise ValueError("Configuration dataset_id does not match the price panel")
    return {
        "name": name, "strategy": strategy, "dataset_id": dataset_id,
        "initial_capital": capital,
        "transaction_cost_bps": _number(
            config.get("transaction_cost_bps", 10), "transaction_cost_bps", 0, 100
        ),
        "risk_free_rate": _number(config.get("risk_free_rate", 0), "risk_free_rate", -0.99, 1),
        "seed": seed, "split": split, "lookback": lookback, "risk_aversion": risk_aversion,
    }


def run_historical_backtest(panel: PricePanel, config: dict[str, Any]) -> dict[str, Any]:
    """Replay one development split; 2024 cannot be evaluated through this API.

    A decision executed at close t uses precisely W returns ending at close t-1.
    The target then receives adjusted-price relative P[t+1]/P[t]. Both benchmarks
    use the same warmup, intervals, fee accounting and final valuation boundary.
    Pre-split history can warm up an estimator but contributes no portfolio PnL.
    """
    config = _configuration(panel, config)
    lookback = config["lookback"]
    split_start, split_end = SPLITS[config["split"]]
    eligible = [index for index, date in enumerate(panel.dates) if split_start <= date <= split_end]
    if not eligible:
        raise ValueError("Selected split has no price observations")
    first = max(eligible[0], lookback + 1)
    last = eligible[-1]
    if first >= last:
        raise ValueError("Selected split has insufficient warmup and evaluation observations")
    value = config["initial_capital"]
    drift: NDArray[np.float64] | None = None
    equal = np.full(len(panel.assets), 1 / len(panel.assets), dtype=np.float64)
    equity: list[dict[str, Any]] = [
        {"date": panel.dates[first], "equity": value, "net_return": 0.0}
    ]
    allocations: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    audit: list[dict[str, str]] = [
        {"date": panel.dates[first], "event": "historical_replay_started",
         "detail": "PAPER: lagged adjusted-close total-return simulation, not actual fills."}
    ]
    costs: list[float] = []
    fallback_count = 0
    normalization_count = 0
    for index in range(first, last):
        # Excludes P[t] and every later close from mean/covariance estimation.
        window_prices = panel.prices[index - lookback - 1:index]
        returns = window_prices[1:] / window_prices[:-1] - 1.0
        reason = "exogenous_equal_weight"
        iterations = 0
        target = equal
        if config["strategy"] == "markowitz":
            decision = markowitz_weights(returns, config["risk_aversion"])
            target, reason, iterations = decision.weights, decision.reason, decision.iterations
            if decision.used_fallback:
                fallback_count += 1
                audit.append({
                    "date": panel.dates[index], "event": "markowitz_fallback",
                    "detail": f"Equal-weight fallback: {reason}; information through "
                              f"{panel.dates[index - 1]} only.",
                })
            elif reason == "optimized_numeric_normalization":
                normalization_count += 1
        step = rebalance_step(
            value, drift, target,
            panel.prices[index + 1] / panel.prices[index],
            config["transaction_cost_bps"],
        )
        allocations.append({
            "date": panel.dates[index],
            "weights": dict(zip(panel.assets, target.tolist(), strict=True)),
            "turnover": step.turnover, "cost": step.cost,
        })
        equity.append({
            "date": panel.dates[index + 1], "equity": step.equity,
            "net_return": step.net_return,
        })
        decisions.append({
            "execution_at": panel.dates[index],
            "information_as_of": panel.dates[index - 1],
            "window_start": panel.dates[index - lookback - 1],
            "window_end": panel.dates[index - 1], "return_observations": lookback,
            "solver_status": reason, "solver_iterations": iterations,
            "traded_notional": step.traded_notional,
        })
        value, drift = step.equity, step.weights
        costs.append(step.cost)
    audit.append({
        "date": panel.dates[last], "event": "historical_replay_completed",
        "detail": f"Completed {len(allocations)} daily intervals; optimizer fallbacks "
                  f"{fallback_count}. No 2024 holdout evaluation.",
    })
    total_costs = math.fsum(costs)
    metrics = financial_metrics(
        [point["equity"] for point in equity], config["risk_free_rate"], total_costs
    )
    return {
        "metrics": metrics, "equity": equity, "allocations": allocations, "audit": audit,
        "manifest": {
            "engine_version": ENGINE_VERSION, "accounting_version": "exact-self-financing-v1",
            "dataset_id": config["dataset_id"], "dataset_sha256": panel.metadata.get("sha256"),
            "data_mode": panel.metadata.get("kind", "HISTORICAL"), "mode": "PAPER",
            "configuration": config,
            "evaluation": {"split": config["split"], "start_date": panel.dates[first],
                           "end_date": panel.dates[last], "intervals": len(allocations),
                           "holdout_evaluated": False},
            "timing_convention": {
                "information": "W simple returns ending at close t-1; never close t",
                "execution": "Stylized adjusted close t; then t-to-t+1 adjusted-price relative",
                "price_basis": "Vendor adjusted close total returns, not executable raw quotes",
                "warmup": "Same W+1 prior closes and evaluation dates for both baselines",
                "costs": "Exact fee F=c*sum(abs(target*(V-F)-V*drift)); entry included",
                "terminal_liquidation": False,
            },
            "optimizer": {
                "active": config["strategy"] == "markowitz",
                "method": "SLSQP", "objective": "0.5*risk_aversion*annual_variance-annual_mean",
                "annualization_factor": ANNUALIZATION, "sample_ddof": 1,
                "covariance_ridge_annual": COVARIANCE_RIDGE,
                "ftol": SOLVER_FTOL, "maxiter": SOLVER_MAXITER,
                "constraints": "long-only, each weight <=1, sum=1; no leverage",
                "fallback": "audited equal_weight", "fallback_count": fallback_count,
                "numeric_normalization_count": normalization_count,
            },
            "metric_definitions": {
                "annualization_factor": 252, "volatility_ddof": 1,
                "risk_free": "effective annual rate converted to daily",
                "returns": "net of exact fees; initial zero curve point excluded",
                "drawdown": "nonnegative magnitude, initial pre-fee cash included",
                "undefined_values": "null",
            },
            "seed_usage": "Recorded; deterministic optimizer and benchmarks use no random draws",
            "dependency_versions": {"numpy": version("numpy"), "scipy": version("scipy")},
            "decisions": decisions,
        },
    }
