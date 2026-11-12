"""Hand accounting and look-ahead prevention on labeled offline test panels."""

import json
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest
from portfolio_core import PricePanel
from portfolio_research import OptimizationDecision, run_historical_backtest
from portfolio_research import backtest as module
from portfolio_research import markowitz as optimizer_module


def panel(
    rows: int = 24, assets: int = 3, dates: tuple[str, ...] | None = None,
    prices: np.ndarray | None = None,
) -> PricePanel:
    """Fictional unit-test data only; never persisted as historical provenance."""
    dates = dates or tuple((date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(rows))
    if prices is None:
        generator = np.random.default_rng(123)
        prices = 100 * np.cumprod(1 + generator.normal(0.0005, 0.02, (len(dates), assets)), axis=0)
    return PricePanel(
        dates, tuple(f"SYNTHETIC_{i}" for i in range(prices.shape[1])), prices,
        {"id": "offline-synthetic", "kind": "FIXTURE", "sha256": "offline-test-only"},
    )


def config(**updates: Any) -> dict[str, Any]:
    return {
        "name": "Offline research test", "strategy": "markowitz", "lookback": 3,
        "split": "train", "initial_capital": 1000, "transaction_cost_bps": 0,
        **updates,
    }


def test_window_ends_before_execution_price_and_manifest_proves_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[np.ndarray] = []

    def capture(returns: np.ndarray, _risk: float) -> OptimizationDecision:
        observed.append(returns.copy())
        return OptimizationDecision(np.full(3, 1 / 3), False, "optimized", 0.0, 1)

    monkeypatch.setattr(module, "markowitz_weights", capture)
    prices = panel()
    result = run_historical_backtest(prices, config())
    assert result["equity"][0]["date"] == prices.dates[4]
    np.testing.assert_allclose(observed[0], prices.prices[1:4] / prices.prices[:3] - 1)
    for decision in result["manifest"]["decisions"]:
        assert decision["information_as_of"] < decision["execution_at"]
        assert decision["return_observations"] == 3
    assert result["manifest"]["data_mode"] == "FIXTURE"


def test_future_changes_cannot_change_prior_or_same_close_target_decisions() -> None:
    original = panel()
    cut = 12
    changed = original.prices.copy()
    changed[cut:] *= np.array([4, 0.25, 2])
    alternative = PricePanel(original.dates, original.assets, changed, original.metadata)
    first = run_historical_backtest(original, config())
    second = run_historical_backtest(alternative, config())
    for before, after in zip(first["allocations"], second["allocations"], strict=True):
        if before["date"] <= original.dates[cut]:
            assert before["weights"] == after["weights"]
    first_equity = [point for point in first["equity"] if point["date"] < original.dates[cut]]
    second_equity = [point for point in second["equity"] if point["date"] < original.dates[cut]]
    assert first_equity == second_equity


def test_validation_uses_train_warmup_without_evaluating_2024() -> None:
    dates = (
        "2021-12-27", "2021-12-28", "2021-12-29", "2021-12-30", "2021-12-31",
        "2022-01-03", "2022-01-04", "2023-12-28", "2023-12-29", "2024-01-02",
    )
    data = panel(dates=dates)
    result = run_historical_backtest(data, config(split="validation"))
    assert result["equity"][0]["date"] == "2022-01-03"
    assert result["equity"][-1]["date"] == "2023-12-29"
    assert result["manifest"]["decisions"][0]["information_as_of"] == "2021-12-31"
    assert not result["manifest"]["evaluation"]["holdout_evaluated"]
    assert all(point["date"] < "2024-01-01" for point in result["equity"])


def test_2024_prices_have_no_effect_on_validation_results() -> None:
    dates = (
        "2021-12-27", "2021-12-28", "2021-12-29", "2021-12-30", "2021-12-31",
        "2022-01-03", "2022-01-04", "2023-12-28", "2023-12-29", "2024-01-02",
    )
    original = panel(dates=dates)
    changed = original.prices.copy()
    changed[-1] *= 1000
    alternate = PricePanel(original.dates, original.assets, changed, original.metadata)
    assert run_historical_backtest(original, config(split="validation")) == run_historical_backtest(
        alternate, config(split="validation")
    )


def test_equal_weight_and_markowitz_share_evaluation_dates_and_accounting() -> None:
    data = panel()
    classical = run_historical_backtest(data, config())
    equal = run_historical_backtest(data, config(strategy="equal_weight"))
    assert [point["date"] for point in classical["equity"]] == [
        point["date"] for point in equal["equity"]
    ]
    assert classical["manifest"]["accounting_version"] == equal["manifest"]["accounting_version"]
    assert classical["manifest"]["timing_convention"] == equal["manifest"]["timing_convention"]


def test_exact_initial_and_rebalance_costs_match_hand_calculation() -> None:
    prices = np.array([
        [100, 100], [100, 100], [100, 100], [100, 100], [110, 90], [99, 99],
    ], dtype=np.float64)
    result = run_historical_backtest(
        panel(prices=prices, rows=6, assets=2),
        config(strategy="equal_weight", lookback=2, transaction_cost_bps=100),
    )
    # Initial F=0.01*1000/(1.01); next fee=0.01*(0.1*V)=0.001*V.
    expected = [1000, 1000 / 1.01, 1000 / 1.01 * 0.999]
    assert [point["equity"] for point in result["equity"]] == pytest.approx(expected)
    assert result["allocations"][0]["cost"] == pytest.approx(1000 / 101)
    assert result["metrics"]["final_equity"] == pytest.approx(expected[-1])


def test_optimizer_failure_is_counted_and_audited_without_fake_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unsuccessful(*_args: object, **_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(success=False, x=np.array([1, 0, 0]), nit=300)

    monkeypatch.setattr(optimizer_module, "minimize", unsuccessful)
    data = panel()
    result = run_historical_backtest(data, config())
    intervals = len(result["allocations"])
    assert result["manifest"]["optimizer"]["fallback_count"] == intervals
    assert sum(event["event"] == "markowitz_fallback" for event in result["audit"]) == intervals
    for allocation in result["allocations"]:
        np.testing.assert_allclose(list(allocation["weights"].values()), [1 / 3] * 3)


def test_reproducibility_and_finite_json_manifest() -> None:
    data = panel()
    first = run_historical_backtest(data, config(transaction_cost_bps=10))
    assert first == run_historical_backtest(data, config(transaction_cost_bps=10))
    json.dumps(first, allow_nan=False)
    assert first["manifest"]["dataset_sha256"] == data.metadata["sha256"]
    assert first["manifest"]["dependency_versions"]["scipy"]


@pytest.mark.parametrize("overrides", [
    {"split": "final_test"}, {"split": "2024"}, {"lookback": 1}, {"lookback": True},
    {"lookback": 1.5}, {"strategy": "ppo"}, {"dataset_id": "other"},
    {"initial_capital": 0}, {"initial_capital": np.inf}, {"initial_capital": True},
    {"transaction_cost_bps": -1}, {"transaction_cost_bps": 101},
    {"risk_free_rate": -1}, {"risk_aversion": 0}, {"risk_aversion": np.nan},
    {"seed": -1}, {"seed": 1.5}, {"seed": True}, {"name": " "}, {"name": "x" * 81},
    {"extra": "not-accepted"},
])
def test_invalid_configuration_fails_closed(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        run_historical_backtest(panel(), config(**overrides))


def test_missing_split_or_insufficient_history_fails_without_inventing_data() -> None:
    with pytest.raises(ValueError, match="no price"):
        run_historical_backtest(panel(), config(split="validation"))
    with pytest.raises(ValueError, match="insufficient"):
        run_historical_backtest(panel(rows=5), config(lookback=10))
