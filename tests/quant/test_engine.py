"""Hand-computed accounting and temporal invariants, independent of web services."""

import hashlib
import json
import math
from pathlib import Path

import pytest
from portfolio_quant import fixture_metadata, run_backtest
from portfolio_quant.engine import _run_prices, _validate_weights

CONFIG = {
    "name": "Hand-computed synthetic test",
    "initial_capital": 1000,
    "transaction_cost_bps": 0,
}
PRICES = [("2020-01-02", [100, 100]), ("2020-01-03", [110, 90]), ("2020-01-06", [99, 99])]


def test_equal_weight_rebalances_drift_instead_of_buy_and_hold():
    result = _run_prices(CONFIG, ["FICT_A", "FICT_B"], PRICES)
    assert [point["equity"] for point in result["equity"]] == pytest.approx([1000] * 3)
    assert result["allocations"][1]["turnover"] == pytest.approx(0.1)
    # Buy-and-hold of the same initial basket would instead end at 990.
    assert result["metrics"]["final_equity"] != pytest.approx(990)


def test_entry_and_rebalance_fees_are_charged_once_without_terminal_fee():
    result = _run_prices({**CONFIG, "transaction_cost_bps": 100}, ["A", "B"], PRICES)
    assert [point["equity"] for point in result["equity"]] == pytest.approx([1000, 990, 989.01])
    assert [allocation["cost"] for allocation in result["allocations"]] == pytest.approx([10, 0.99])
    assert [allocation["turnover"] for allocation in result["allocations"]] == pytest.approx(
        [1, 0.1]
    )
    assert result["metrics"]["total_costs"] == pytest.approx(10.99)
    assert result["metrics"]["cumulative_return"] == pytest.approx(-0.01099)
    assert len(result["allocations"]) == len(PRICES) - 1


def test_hand_computed_metrics_sample_std_and_initial_peak():
    rows = [("2020-01-02", [100]), ("2020-01-03", [110]), ("2020-01-06", [99])]
    metrics = _run_prices(CONFIG, ["A"], rows)["metrics"]
    assert metrics["final_equity"] == pytest.approx(990)
    assert metrics["cumulative_return"] == pytest.approx(-0.01)
    assert metrics["annualized_volatility"] == pytest.approx(2.24499443206436)
    assert metrics["sharpe_ratio"] == pytest.approx(0, abs=1e-12)
    assert metrics["max_drawdown"] == pytest.approx(0.1)


def test_effective_annual_risk_free_rate_is_converted_to_daily():
    rows = [("2020-01-02", [100]), ("2020-01-03", [110]), ("2020-01-06", [99])]
    metrics = _run_prices({**CONFIG, "risk_free_rate": 0.1}, ["A"], rows)["metrics"]
    expected_daily_rf = 1.1 ** (1 / 252) - 1
    expected_sharpe = -expected_daily_rf / math.sqrt(0.02) * math.sqrt(252)
    assert metrics["sharpe_ratio"] == pytest.approx(expected_sharpe)


def test_flat_prices_without_costs_have_undefined_sharpe():
    rows = [("2020-01-02", [100]), ("2020-01-03", [100]), ("2020-01-06", [100])]
    metrics = _run_prices(CONFIG, ["A"], rows)["metrics"]
    assert metrics["annualized_volatility"] == 0
    assert metrics["sharpe_ratio"] is None
    assert metrics["max_drawdown"] == 0


def test_single_return_has_undefined_sample_volatility_and_sharpe():
    metrics = _run_prices(CONFIG, ["A", "B"], PRICES[:2])["metrics"]
    assert metrics["annualized_volatility"] is None
    assert metrics["sharpe_ratio"] is None


def test_entry_cost_is_in_first_return_and_initial_cash_drawdown():
    rows = [("2020-01-02", [100]), ("2020-01-03", [100]), ("2020-01-06", [100])]
    result = _run_prices({**CONFIG, "transaction_cost_bps": 100}, ["A"], rows)
    assert [point["net_return"] for point in result["equity"]] == pytest.approx([0, -0.01, 0])
    assert result["metrics"]["max_drawdown"] == pytest.approx(0.01)
    assert result["metrics"]["total_costs"] == 10


@pytest.mark.parametrize(
    "override",
    [
        {"initial_capital": 0},
        {"initial_capital": -1},
        {"initial_capital": math.inf},
        {"initial_capital": math.nan},
        {"initial_capital": True},
        {"initial_capital": 1e10},
        {"transaction_cost_bps": -1},
        {"transaction_cost_bps": 101},
        {"transaction_cost_bps": "10"},
        {"transaction_cost_bps": math.nan},
        {"risk_free_rate": -1},
        {"risk_free_rate": math.inf},
        {"seed": True},
        {"seed": 1.1},
        {"seed": -1},
        {"seed": 2147483648},
        {"name": ""},
        {"name": " "},
        {"name": "x" * 81},
        {"strategy": "ppo"},
        {"dataset_id": "market-data"},
        {"unrecognized": 1},
    ],
)
def test_invalid_configuration_fails_closed(override):
    with pytest.raises(ValueError):
        run_backtest({**CONFIG, **override})


@pytest.mark.parametrize(
    "assets,rows",
    [
        ([], PRICES),
        (["A", "A"], PRICES),
        (["A", "B"], []),
        (["A", "B"], PRICES[:1]),
        (["A", "B"], [PRICES[0], PRICES[0]]),
        (["A", "B"], list(reversed(PRICES))),
        (["A", "B"], [("20200102", [100, 100]), PRICES[1]]),
        (["A", "B"], [("2020-01-02", [100]), PRICES[1]]),
        (["A", "B"], [("2020-01-02", [100, 0]), PRICES[1]]),
        (["A", "B"], [("2020-01-02", [100, -1]), PRICES[1]]),
        (["A", "B"], [("2020-01-02", [100, math.nan]), PRICES[1]]),
        (["A", "B"], [("2020-01-02", [100, math.inf]), PRICES[1]]),
        (["A", "B"], [("2020-01-02", [100, True]), PRICES[1]]),
    ],
)
def test_invalid_prices_or_dates_fail_closed(assets, rows):
    with pytest.raises(ValueError):
        _run_prices(CONFIG, assets, rows)


@pytest.mark.parametrize(
    "weights", [[1.1, -0.1], [0.5], [0.4, 0.4], [math.nan, 0.5], [math.inf, 0], [True, 0]]
)
def test_invalid_weights_fail_closed(weights):
    with pytest.raises(ValueError):
        _validate_weights(weights, 2)


def test_future_price_changes_do_not_change_earlier_values_or_decisions():
    full = _run_prices(CONFIG, ["A", "B"], PRICES)
    prefix = _run_prices(CONFIG, ["A", "B"], PRICES[:2])
    altered = _run_prices(CONFIG, ["A", "B"], [*PRICES[:2], ("2020-01-06", [200, 50])])
    assert full["equity"][:2] == prefix["equity"] == altered["equity"][:2]
    assert full["allocations"][:1] == prefix["allocations"]
    assert full["allocations"] == altered["allocations"]
    assert full["equity"][-1] != altered["equity"][-1]


def test_public_fixture_metadata_hash_and_result_are_json_finite_and_reproducible():
    metadata = fixture_metadata()
    fixture = Path(__file__).resolve().parents[2] / "packages/portfolio_quant/fixture-v1.csv"
    assert metadata["sha256"] == hashlib.sha256(fixture.read_bytes()).hexdigest()
    assert metadata["kind"] == "FIXTURE"
    assert len(metadata["assets"]) == 10
    assert all(asset.startswith("FICT_") for asset in metadata["assets"])
    assert metadata["observations"] >= 15
    result = run_backtest(CONFIG)
    assert run_backtest(CONFIG) == result
    assert set(result) == {"metrics", "equity", "allocations", "audit", "manifest"}
    assert len(result["equity"]) == metadata["observations"]
    assert result["equity"][0]["equity"] == CONFIG["initial_capital"]
    assert result["manifest"]["fixture_sha256"] == metadata["sha256"]
    assert result["manifest"]["configuration"]["transaction_cost_bps"] == 0
    json.dumps(result, allow_nan=False)


def test_seed_recorded_without_changing_deterministic_strategy_results():
    first = run_backtest({**CONFIG, "seed": 1})
    second = run_backtest({**CONFIG, "seed": 2})
    assert first["manifest"]["configuration"]["seed"] != second["manifest"]["configuration"]["seed"]
    for key in ("metrics", "equity", "allocations", "audit"):
        assert first[key] == second[key]
