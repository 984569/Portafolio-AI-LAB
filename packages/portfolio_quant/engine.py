"""Canonical fixture accounting, independent of API, persistence and networks.

Fictional close prices are normalized units, not observed or adjusted market data.
The cost approximation charges pre-trade equity times L1 turnover, then allocates
remaining equity to targets. It does not solve exact share-level self financing.
"""

import csv
import hashlib
import io
import math
import statistics
import sys
from datetime import date
from pathlib import Path

ENGINE_VERSION = "0.1.0"
_FIXTURE = Path(__file__).with_name("fixture-v1.csv")
_FIELDS = {
    "name",
    "strategy",
    "dataset_id",
    "initial_capital",
    "transaction_cost_bps",
    "risk_free_rate",
    "seed",
}


def _number(value: object, label: str, lower: float, upper: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be finite") from exc
    if not math.isfinite(result) or not lower <= result <= upper:
        raise ValueError(f"{label} must be finite and between {lower} and {upper}")
    return result


def _validate_config(config: dict) -> dict:
    if not isinstance(config, dict) or set(config) - _FIELDS:
        raise ValueError("Configuration must be an object with only supported fields")
    name = config.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or len(name) > 80:
        raise ValueError("name must contain 1 to 80 characters")
    strategy = config.get("strategy", "equal_weight")
    dataset_id = config.get("dataset_id", "fixture-v1")
    if strategy != "equal_weight" or dataset_id != "fixture-v1":
        raise ValueError("Only equal_weight on fixture-v1 is supported")
    capital = _number(config.get("initial_capital", 10000), "initial_capital", 0, 1e9)
    if capital <= 0:
        raise ValueError("initial_capital must be positive")
    seed = config.get("seed", 42)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2147483647:
        raise ValueError("seed must be an integer between 0 and 2147483647")
    return {
        "name": name,
        "strategy": strategy,
        "dataset_id": dataset_id,
        "initial_capital": capital,
        "transaction_cost_bps": _number(
            config.get("transaction_cost_bps", 10), "transaction_cost_bps", 0, 100
        ),
        "risk_free_rate": _number(config.get("risk_free_rate", 0), "risk_free_rate", -0.99, 1),
        "seed": seed,
    }


def _validate_prices(assets: list[str], rows: list[tuple[str, list[float]]]) -> None:
    if not assets or len(set(assets)) != len(assets):
        raise ValueError("Assets must be nonempty and unique")
    if any(not isinstance(asset, str) or not asset.strip() for asset in assets):
        raise ValueError("Asset symbols must be nonempty strings")
    if len(rows) < 2:
        raise ValueError("At least two price observations are required")
    previous = None
    for stamp, values in rows:
        try:
            parsed = date.fromisoformat(stamp)
        except (ValueError, TypeError) as exc:
            raise ValueError("Dates must use YYYY-MM-DD") from exc
        if parsed.isoformat() != stamp or (previous is not None and parsed <= previous):
            raise ValueError("Dates must be canonical, unique and strictly increasing")
        previous = parsed
        if len(values) != len(assets):
            raise ValueError("Every row must have exactly one price per asset")
        for value in values:
            if (
                isinstance(value, bool)
                or not isinstance(value, (float, int))
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ValueError("Prices must be positive finite numbers")


def _load_fixture() -> tuple[bytes, list[str], list[tuple[str, list[float]]]]:
    raw = _FIXTURE.read_bytes()
    reader = csv.reader(io.StringIO(raw.decode("utf-8")))
    header = next(reader)
    if header[0] != "date" or len(header) != 11:
        raise ValueError("Invalid fixture header: expected date and ten fictional assets")
    assets = header[1:]
    rows = []
    for row in reader:
        if len(row) != len(header):
            raise ValueError("Incomplete fixture row")
        rows.append((row[0], [float(value) for value in row[1:]]))
    _validate_prices(assets, rows)
    return raw, assets, rows


def fixture_metadata() -> dict:
    """Describe the versioned local synthetic fixture; never access a provider."""
    raw, assets, rows = _load_fixture()
    return {
        "id": "fixture-v1",
        "kind": "FIXTURE",
        "source": "Versioned synthetic prices; fictional assets; no exchange calendar or real data",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "assets": assets,
        "start_date": rows[0][0],
        "end_date": rows[-1][0],
        "observations": len(rows),
    }


def _validate_weights(weights: list[float], count: int) -> None:
    if len(weights) != count or any(
        isinstance(weight, bool)
        or not isinstance(weight, (float, int))
        or not math.isfinite(weight)
        or not 0 <= weight <= 1
        for weight in weights
    ):
        raise ValueError("Weights must be finite long-only fractions matching the universe")
    if not math.isclose(math.fsum(weights), 1.0, rel_tol=0, abs_tol=1e-12):
        raise ValueError("Weights must sum to one")


def _calculate_metrics(equity: list[dict], total_costs: float, annual_rf: float) -> dict:
    returns = [point["net_return"] for point in equity[1:]]
    sigma = statistics.stdev(returns) if len(returns) >= 2 else None
    daily_rf = math.expm1(math.log1p(annual_rf) / 252)
    sharpe = None
    if sigma is not None and sigma > 0:
        sharpe = (statistics.mean(returns) - daily_rf) / sigma * math.sqrt(252)
    peak = equity[0]["equity"]
    drawdown = 0.0
    for point in equity:
        peak = max(peak, point["equity"])
        drawdown = max(drawdown, (peak - point["equity"]) / peak)
    return {
        "cumulative_return": equity[-1]["equity"] / equity[0]["equity"] - 1,
        "annualized_volatility": sigma * math.sqrt(252) if sigma is not None else None,
        "sharpe_ratio": sharpe,
        "max_drawdown": drawdown,
        "final_equity": equity[-1]["equity"],
        "total_costs": total_costs,
    }


def _run_prices(config: dict, assets: list[str], rows: list[tuple[str, list[float]]]) -> dict:
    """Internal accounting seam for hand-computed fixtures and causality tests."""
    config = _validate_config(config)
    _validate_prices(assets, rows)
    weights = [1 / len(assets)] * len(assets)
    _validate_weights(weights, len(assets))
    value = config["initial_capital"]
    equity = [{"date": rows[0][0], "equity": value, "net_return": 0.0}]
    allocations = []
    drift = None
    costs = []
    for index in range(len(rows) - 1):
        stamp, current = rows[index]
        next_stamp, following = rows[index + 1]
        turnover = (
            1.0
            if drift is None
            else math.fsum(abs(target - old) for target, old in zip(weights, drift, strict=True))
        )
        cost = value * (config["transaction_cost_bps"] / 10000) * turnover
        relatives = [future / now for now, future in zip(current, following, strict=True)]
        growth = math.fsum(
            weight * relative for weight, relative in zip(weights, relatives, strict=True)
        )
        next_value = (value - cost) * growth
        if not math.isfinite(next_value) or next_value <= 0 or not math.isfinite(growth):
            raise ValueError("Non-finite or nonpositive portfolio valuation")
        allocations.append(
            {
                "date": stamp,
                "weights": dict(zip(assets, weights, strict=True)),
                "turnover": turnover,
                "cost": cost,
            }
        )
        equity.append(
            {"date": next_stamp, "equity": next_value, "net_return": next_value / value - 1}
        )
        drift = [
            weight * relative / growth for weight, relative in zip(weights, relatives, strict=True)
        ]
        _validate_weights(drift, len(assets))
        costs.append(cost)
        value = next_value
    return {
        "metrics": _calculate_metrics(equity, math.fsum(costs), config["risk_free_rate"]),
        "equity": equity,
        "allocations": allocations,
    }


def run_backtest(config: dict) -> dict:
    """Calculate canonical Result using only local fixture-v1; no side effects."""
    config = _validate_config(config)
    raw, assets, rows = _load_fixture()
    result = _run_prices(config, assets, rows)
    result["audit"] = [
        {
            "date": rows[0][0],
            "event": "fixture_validated",
            "detail": "FIXTURE: 10 fictional assets. Synthetic prices, not market observations.",
        },
        {
            "date": rows[0][0],
            "event": "cost_model",
            "detail": "Approximate fee=equity*bps/10000*L1(target-drift); entry turnover=1; "
            "entry charged in first interval; no terminal liquidation fee.",
        },
        {
            "date": rows[-1][0],
            "event": "completed",
            "detail": "Deterministic exogenous equal-weight calculation; PAPER ONLY. "
            "Fixture output is not academic validation or investment performance.",
        },
    ]
    result["manifest"] = {
        "engine_version": ENGINE_VERSION,
        "fixture_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_id": "fixture-v1",
        "data_mode": "FIXTURE",
        "mode": "PAPER",
        "configuration": config,
        "python_version": sys.version.split()[0],
        "timing_convention": {
            "target_information": "Exogenous equal weights fixed before all observations",
            "execution": "Stylized rebalance at close t; costs then t-to-t+1 price relatives",
            "equity": "Initial pre-fee cash then interval end valuations",
            "fees": "Approximate pretrade equity times one-way L1 turnover; initial turnover 1",
            "terminal_liquidation": False,
            "future_signals": "Close-derived policies require a separately frozen lag protocol",
        },
        "metric_definitions": {
            "annualization_factor": 252,
            "volatility_ddof": 1,
            "risk_free": "daily_rf=expm1(log1p(annual_effective_rf)/252)",
            "returns": "net of fees; excludes initial zero-return curve point",
            "sharpe_ratio": "mean(daily_net_return-daily_rf)/sample_std*sqrt(252)",
            "undefined_metrics": "null: volatility with <2 returns; Sharpe also with zero std",
            "max_drawdown": "nonnegative magnitude relative to running equity peak including cash",
            "total_costs": "sum of simulated monetary fees, without compounding",
        },
        "seed_usage": "Recorded for reproducibility; equal_weight contains no random draws",
    }
    return result
