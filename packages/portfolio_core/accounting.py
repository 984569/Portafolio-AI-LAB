"""Self-financing fractional targets with proportional costs on buys plus sells."""

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray


def validate_weights(weights: ArrayLike, count: int) -> NDArray[np.float64]:
    result = np.asarray(weights, dtype=np.float64)
    if result.shape != (count,) or not np.isfinite(result).all():
        raise ValueError("Weights must match the universe and be finite")
    if (
        (result < 0).any()
        or (result > 1).any()
        or not np.isclose(result.sum(), 1.0, rtol=0, atol=1e-9)
    ):
        raise ValueError("Weights must be long-only and sum to one")
    return result.copy()


def project_simplex(action: ArrayLike) -> NDArray[np.float64]:
    """Euclidean projection (not clipping or softmax) onto nonnegative sum-one."""
    values = np.asarray(action, dtype=np.float64)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise ValueError("Action must be a finite nonempty vector")
    ordered = np.sort(values)[::-1]
    cumulative = np.cumsum(ordered) - 1.0
    positive = ordered - cumulative / np.arange(1, len(values) + 1) > 0
    rho = int(np.flatnonzero(positive)[-1])
    threshold = cumulative[rho] / (rho + 1)
    projected = np.maximum(values - threshold, 0)
    return validate_weights(projected / projected.sum(), len(values))


@dataclass(frozen=True)
class StepResult:
    equity: float
    net_return: float
    cost: float
    turnover: float
    traded_notional: float
    weights: NDArray[np.float64]


def rebalance_step(
    value: float,
    drift_weights: ArrayLike | None,
    target: ArrayLike,
    price_relatives: ArrayLike,
    transaction_cost_bps: float,
) -> StepResult:
    """Solve fee from post-fee target holdings, then value the subsequent interval.

    Initial drift=None is cash. No terminal liquidation cost is charged. This
    stylized adjusted-price replay models fractional holdings, not live fills.
    """
    if isinstance(value, bool) or not np.isfinite(value) or value <= 0:
        raise ValueError("Capital must be finite and positive")
    if (
        isinstance(transaction_cost_bps, bool)
        or not np.isfinite(transaction_cost_bps)
        or not (0 <= transaction_cost_bps <= 100)
    ):
        raise ValueError("Transaction costs must be finite and between 0 and 100 bps")
    relatives = np.asarray(price_relatives, dtype=np.float64)
    if (
        relatives.ndim != 1
        or not relatives.size
        or not np.isfinite(relatives).all()
        or (relatives <= 0).any()
    ):
        raise ValueError("Price relatives must be finite positive numbers")
    weights = validate_weights(target, len(relatives))
    previous = (
        np.zeros(len(weights))
        if drift_weights is None
        else validate_weights(drift_weights, len(weights))
    )
    rate = transaction_cost_bps / 10000.0
    # Solve in units of pre-trade equity to retain accuracy for small/large capital.
    low, high = 0.0, 2 * rate
    for _ in range(80):
        fraction = (low + high) / 2
        residual = fraction - rate * float(np.abs(weights * (1 - fraction) - previous).sum())
        if residual > 0:
            high = fraction
        else:
            low = fraction
    fee_fraction = (low + high) / 2
    cost = float(value * fee_fraction)
    turnover = float(np.abs(weights * (1 - fee_fraction) - previous).sum())
    growth = float(weights @ relatives)
    equity = float((value - cost) * growth)
    if not np.isfinite(equity) or equity <= 0 or not np.isfinite(growth):
        raise ValueError("Nonpositive or nonfinite resulting equity")
    drift = validate_weights(weights * relatives / growth, len(weights))
    drift.flags.writeable = False
    return StepResult(equity, equity / value - 1, cost, turnover, turnover * value, drift)


def financial_metrics(
    values: ArrayLike, annual_rf: float = 0, total_costs: float = 0
) -> dict[str, float | None]:
    curve = np.asarray(values, dtype=np.float64)
    if curve.ndim != 1 or len(curve) < 2 or not np.isfinite(curve).all() or (curve <= 0).any():
        raise ValueError("Equity must contain at least two positive finite values")
    if not np.isfinite(annual_rf) or not -0.99 <= annual_rf <= 1:
        raise ValueError("Annual risk-free rate is outside supported bounds")
    if not np.isfinite(total_costs) or total_costs < 0:
        raise ValueError("Costs must be finite and nonnegative")
    returns = curve[1:] / curve[:-1] - 1
    sigma = float(np.std(returns, ddof=1)) if len(returns) > 1 else None
    daily_rf = float(np.expm1(np.log1p(annual_rf) / 252))
    sharpe = (
        float((returns.mean() - daily_rf) / sigma * np.sqrt(252))
        if (sigma is not None and sigma > 0)
        else None
    )
    result: dict[str, Any] = {
        "cumulative_return": float(curve[-1] / curve[0] - 1),
        "annualized_volatility": sigma * float(np.sqrt(252)) if sigma is not None else None,
        "sharpe_ratio": sharpe,
        "max_drawdown": float(np.max(1 - curve / np.maximum.accumulate(curve))),
        "final_equity": float(curve[-1]),
        "total_costs": float(total_costs),
    }
    if any(value is not None and not np.isfinite(value) for value in result.values()):
        raise ValueError("Nonfinite financial metric")
    return result
