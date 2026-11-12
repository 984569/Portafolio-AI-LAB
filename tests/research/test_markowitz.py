"""Optimizer contract checks on explicitly synthetic return windows."""

from types import SimpleNamespace

import numpy as np
import pytest
from portfolio_research import markowitz as module
from portfolio_research import markowitz_weights


def test_optimizer_selects_dominant_asset_under_long_only_simplex() -> None:
    returns = np.array([[0.01, 0], [0.01, 0], [0.01, 0]], dtype=np.float64)
    decision = markowitz_weights(returns)
    assert not decision.used_fallback
    np.testing.assert_allclose(decision.weights, [1, 0], atol=1e-7)
    assert decision.objective is not None


def test_zero_history_is_regularized_and_stable_equal_weight() -> None:
    decision = markowitz_weights(np.zeros((8, 3), dtype=np.float64))
    assert not decision.used_fallback
    np.testing.assert_allclose(decision.weights, [1 / 3] * 3)
    assert decision.objective is not None and np.isfinite(decision.objective)


def test_single_asset_is_feasible_and_finite() -> None:
    decision = markowitz_weights(np.array([[0.01], [-0.01], [0]], dtype=np.float64))
    np.testing.assert_allclose(decision.weights, [1])
    assert not decision.used_fallback


def test_risk_aversion_penalizes_an_extremely_volatile_asset() -> None:
    returns = np.array([[0.3, 0.001], [-0.2, 0.001]] * 10, dtype=np.float64)
    low = markowitz_weights(returns, risk_aversion=0.1)
    high = markowitz_weights(returns, risk_aversion=100)
    assert not low.used_fallback and not high.used_fallback
    assert high.weights[0] < low.weights[0]


@pytest.mark.parametrize("returns", [
    np.empty((0, 2)), np.zeros((1, 2)), np.ones(2),
    np.array([[0.0, np.nan], [0.0, 0.0]]),
    np.array([[0.0, np.inf], [0.0, 0.0]]),
    np.array([[0.0, -1.0], [0.0, 0.0]]),
])
def test_invalid_market_window_raises_instead_of_fabricating_optimum(returns: np.ndarray) -> None:
    with pytest.raises(ValueError):
        markowitz_weights(returns)


@pytest.mark.parametrize("risk", [0, -1, np.nan, np.inf, True, "5"])
def test_invalid_risk_aversion_fails_closed(risk: object) -> None:
    with pytest.raises(ValueError):
        markowitz_weights(np.zeros((3, 2)), risk)  # type: ignore[arg-type]


def test_solver_exception_has_audited_equal_weight_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("untrusted solver diagnostic")

    monkeypatch.setattr(module, "minimize", broken)
    decision = markowitz_weights(np.zeros((3, 2)))
    assert decision.used_fallback
    assert decision.reason == "solver_exception"
    assert decision.objective is None
    np.testing.assert_allclose(decision.weights, [0.5, 0.5])


@pytest.mark.parametrize("success,weights,reason", [
    (False, [0.5, 0.5], "solver_unsuccessful"),
    (True, [np.nan, 0.5], "solver_invalid_weights"),
    (True, [1.1, -0.1], "solver_infeasible_weights"),
    (True, [0.2, 0.2], "solver_infeasible_weights"),
    (True, [1.0], "solver_invalid_weights"),
])
def test_invalid_solver_output_falls_back_to_feasible_weights(
    monkeypatch: pytest.MonkeyPatch, success: bool, weights: list[float], reason: str,
) -> None:
    def fake(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(success=success, x=np.array(weights), nit=3)

    monkeypatch.setattr(module, "minimize", fake)
    decision = markowitz_weights(np.zeros((3, 2)))
    assert decision.used_fallback and decision.reason == reason
    np.testing.assert_allclose(decision.weights, [0.5, 0.5])


def test_only_tiny_numerical_residuals_are_normalized(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(success=True, x=np.array([1 + 1e-10, -1e-10]), nit=1)

    monkeypatch.setattr(module, "minimize", fake)
    decision = markowitz_weights(np.zeros((3, 2)))
    assert not decision.used_fallback
    assert decision.reason == "optimized_numeric_normalization"
    np.testing.assert_allclose(decision.weights, [1, 0])
