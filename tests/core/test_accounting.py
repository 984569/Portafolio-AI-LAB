import numpy as np
import pytest
from portfolio_core import (
    PricePanel,
    financial_metrics,
    project_simplex,
    rebalance_step,
)


def test_cash_entry_fee_exactly_financed_and_conserves_holdings():
    step = rebalance_step(1000, None, [0.5, 0.5], [1.1, 0.9], 100)
    assert step.cost == pytest.approx(1000 / 101)
    assert step.equity == pytest.approx(1000 / 1.01)
    assert step.traded_notional + step.cost == pytest.approx(1000)
    assert step.weights == pytest.approx([0.55, 0.45])


def test_exact_rebalance_fee_with_drift_has_known_analytic_solution():
    step = rebalance_step(1000, [0.55, 0.45], [0.5, 0.5], [0.9, 1.1], 100)
    assert step.cost == pytest.approx(1)
    assert step.traded_notional == pytest.approx(100)
    assert step.equity == pytest.approx(999)
    assert step.turnover == pytest.approx(0.1)


@pytest.mark.parametrize("seed", range(10))
def test_random_exact_accounting_identity(seed):
    rng = np.random.default_rng(seed)
    old, target = rng.dirichlet(np.ones(10), size=2)
    step = rebalance_step(4321, old, target, rng.uniform(0.8, 1.2, 10), 75)
    traded = np.abs(target * (4321 - step.cost) - old * 4321).sum()
    assert step.cost == pytest.approx(traded * 0.0075, abs=1e-9)
    assert step.weights.sum() == pytest.approx(1)
    assert (step.weights >= 0).all()


def test_no_cost_if_already_on_target_and_metrics_known_case():
    assert rebalance_step(1000, [0.5, 0.5], [0.5, 0.5], [1, 1], 100).cost < 1e-20
    metrics = financial_metrics([1000, 1100, 990])
    assert metrics["annualized_volatility"] == pytest.approx(2.24499443206436)
    assert metrics["max_drawdown"] == pytest.approx(0.1)
    assert metrics["sharpe_ratio"] == pytest.approx(0, abs=1e-12)
    assert financial_metrics([1000, 1000, 1000])["sharpe_ratio"] is None


def test_simplex_handles_zero_and_extreme_admissible_actions():
    assert project_simplex([0, 0]) == pytest.approx([0.5, 0.5])
    assert project_simplex([1, -1]) == pytest.approx([1, 0])
    with pytest.raises(ValueError):
        project_simplex([np.nan, 0])


def test_panel_is_copied_readonly_and_rejects_corrupt_data():
    prices = np.ones((2, 2))
    panel = PricePanel(("2020-01-01", "2020-01-02"), ("A", "B"), prices, {})
    prices[0, 0] = 2
    assert panel.prices[0, 0] == 1
    with pytest.raises(ValueError):
        panel.prices[0, 0] = 3
    with pytest.raises(ValueError):
        PricePanel(("2020-01-02", "2020-01-01"), ("A", "B"), prices, {})
    with pytest.raises(ValueError):
        rebalance_step(1000, None, [1.1, -0.1], [1, 1], 10)
