import numpy as np
import pytest
from portfolio_core import PricePanel
from portfolio_env import PortfolioEnv


def test_log_reward_stays_finite_for_positive_equity_after_extreme_loss():
    panel = PricePanel(
        ("2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"),
        ("TEST",),
        np.array([[100.0], [100.0], [100.0], [1e-20]]),
        {},
    )
    env = PortfolioEnv(panel, lookback=1, transaction_cost_bps=0)
    env.reset(seed=42)
    _, reward, terminated, _, info = env.step(np.array([0], dtype=np.float32))
    assert np.isfinite(reward)
    assert reward == pytest.approx(np.log(1e-22))
    assert info["equity"] > 0
    assert terminated
