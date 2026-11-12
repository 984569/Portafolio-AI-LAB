"""Long-only rolling mean-variance optimization with audited safe fallback.

Callers must supply returns already restricted to the information set available
before execution. This module never reads prices, dates, providers or a test set.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize

FloatArray = NDArray[np.float64]
ANNUALIZATION = 252
COVARIANCE_RIDGE = 1e-8
SOLVER_FTOL = 1e-10
SOLVER_MAXITER = 300
WEIGHT_TOLERANCE = 1e-7


@dataclass(frozen=True)
class OptimizationDecision:
    """A feasible allocation and explicit optimization/fallback evidence."""

    weights: FloatArray
    used_fallback: bool
    reason: str
    objective: float | None
    iterations: int


def markowitz_weights(past_returns: FloatArray, risk_aversion: float = 5.0) -> OptimizationDecision:
    """Maximize annualized mean minus half risk-aversion times annual variance.

    There is no leverage, shorting, target return, additional concentration cap
    or stochastic initialization. Covariance is sample ddof=1 plus a fixed ridge.
    Solver failures and materially infeasible outputs return equal weights with
    an explicit reason; tiny numerical residuals are projected by clip/normalize.
    Invalid market inputs raise instead of pretending the optimizer succeeded.
    """
    returns = np.asarray(past_returns, dtype=np.float64)
    if returns.ndim != 2 or returns.shape[0] < 2 or returns.shape[1] < 1:
        raise ValueError("A rectangular return window with at least two rows is required")
    if not np.isfinite(returns).all() or np.any(returns <= -1):
        raise ValueError("Historical returns must be finite and greater than -1")
    if (
        isinstance(risk_aversion, bool)
        or not isinstance(risk_aversion, (int, float, np.floating))
        or not np.isfinite(risk_aversion) or risk_aversion <= 0
    ):
        raise ValueError("risk_aversion must be finite and positive")
    assets = returns.shape[1]
    equal = np.full(assets, 1.0 / assets, dtype=np.float64)
    means = np.mean(returns, axis=0) * ANNUALIZATION
    covariance = np.atleast_2d(np.cov(returns, rowvar=False, ddof=1)) * ANNUALIZATION
    covariance = (covariance + covariance.T) / 2 + COVARIANCE_RIDGE * np.eye(assets)
    if not np.isfinite(means).all() or not np.isfinite(covariance).all():
        raise ValueError("Historical moments are non-finite")

    def objective(weights: FloatArray) -> float:
        return float(0.5 * risk_aversion * weights @ covariance @ weights - means @ weights)

    def gradient(weights: FloatArray) -> FloatArray:
        return np.asarray(risk_aversion * covariance @ weights - means, dtype=np.float64)

    def fallback(reason: str, iterations: int = 0) -> OptimizationDecision:
        return OptimizationDecision(equal.copy(), True, reason, None, iterations)

    try:
        result = minimize(
            objective,
            equal,
            method="SLSQP",
            jac=gradient,
            bounds=[(0.0, 1.0)] * assets,
            constraints={
                "type": "eq",
                "fun": lambda weights: float(np.sum(weights) - 1.0),
                "jac": lambda _weights: np.ones(assets, dtype=np.float64),
            },
            options={"ftol": SOLVER_FTOL, "maxiter": SOLVER_MAXITER, "disp": False},
        )
    except Exception:
        # Do not leak raw solver exception text into an audit or API response.
        return fallback("solver_exception")
    iterations = int(getattr(result, "nit", 0))
    if not result.success:
        return fallback("solver_unsuccessful", iterations)
    weights = np.asarray(result.x, dtype=np.float64)
    if weights.shape != equal.shape or not np.isfinite(weights).all():
        return fallback("solver_invalid_weights", iterations)
    if (
        np.any(weights < -WEIGHT_TOLERANCE)
        or np.any(weights > 1 + WEIGHT_TOLERANCE)
        or abs(float(np.sum(weights)) - 1.0) > WEIGHT_TOLERANCE
    ):
        return fallback("solver_infeasible_weights", iterations)
    clipped = np.clip(weights, 0.0, 1.0)
    normalized = clipped / np.sum(clipped)
    value = objective(normalized)
    if not np.isfinite(value):
        return fallback("solver_nonfinite_objective", iterations)
    adjusted = not np.array_equal(normalized, weights)
    return OptimizationDecision(
        normalized, False, "optimized_numeric_normalization" if adjusted else "optimized",
        value, iterations,
    )
