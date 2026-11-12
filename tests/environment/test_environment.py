"""Synthetic offline MDP accounting, temporal eligibility and API invariants."""

import math
from datetime import date, timedelta

import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env as gym_check_env
from portfolio_core import PricePanel
from portfolio_env import PortfolioEnv
from stable_baselines3.common.env_checker import check_env as sb3_check_env


def panel(rows):
    prices = np.asarray(rows, dtype=np.float64)
    dates = tuple((date(2020, 1, 1) + timedelta(days=i)).isoformat() for i in range(len(rows)))
    return PricePanel(
        dates=dates,
        assets=tuple(f"FICT_{i}" for i in range(prices.shape[1])),
        prices=prices,
        metadata={"id": "offline-env-fixture", "sha256": "test-only", "kind": "FIXTURE"},
    )


def long_panel():
    ticks = np.arange(80, dtype=np.float64)
    return panel(np.column_stack([100 * np.exp(ticks * 0.001), 90 + np.sin(ticks) * 2]))


def test_initial_state_is_lagged_log_returns_and_cash_weights():
    prices = panel([[100, 100], [110, 90], [121, 99], [242, 49.5], [266.2, 54.45]])
    env = PortfolioEnv(prices, lookback=1)
    observation, info = env.reset(seed=17)
    assert observation.dtype == np.float32
    assert observation.shape == (4,)
    np.testing.assert_allclose(observation[:2], np.log([1.1, 0.9]), rtol=1e-6)
    np.testing.assert_array_equal(observation[2:], [0, 0])
    assert info["information_as_of"] == prices.dates[1]
    assert info["execution_at"] == prices.dates[2]
    assert info["mode"] == "PAPER"
    assert info["observation_returns"] == "lagged_log_price_relatives"
    assert env.observation_space.contains(observation)


def test_exact_entry_and_rebalance_costs_without_terminal_liquidation():
    prices = panel([[100, 100], [100, 100], [100, 100], [110, 90], [99, 99]])
    env = PortfolioEnv(prices, lookback=1, initial_capital=1000, transaction_cost_bps=100)
    env.reset(seed=42)
    observation, reward, terminated, truncated, first = env.step(np.zeros(2, dtype=np.float32))
    assert first["cost"] == pytest.approx(1000 / 101)
    assert first["equity"] == pytest.approx(1000 / 1.01)
    assert reward == pytest.approx(math.log(1 / 1.01))
    assert not terminated and not truncated
    assert first["target_weights"] == pytest.approx([0.5, 0.5])
    assert first["next_drift_weights"] == pytest.approx([0.55, 0.45])
    # This state's portfolio weights are known at the preceding execution close;
    # revealing current drift would leak a price not eligible for the next action.
    np.testing.assert_array_equal(observation[-2:], [0.5, 0.5])
    _, second_reward, terminated, truncated, second = env.step(np.zeros(2, dtype=np.float32))
    assert second["cost"] == pytest.approx((1000 / 1.01) * 0.001)
    assert second["equity"] == pytest.approx(989.108910891089)
    assert second_reward == pytest.approx(math.log(0.999))
    assert terminated and not truncated
    assert second["information_as_of"] == prices.dates[2]
    assert second["execution_at"] == prices.dates[3]
    assert second["valuation_at"] == prices.dates[4]
    assert first["cost"] + second["cost"] == pytest.approx(10.89108910891089)


def test_simple_reward_is_net_return_without_doubled_fee():
    env = PortfolioEnv(
        panel([[100], [100], [100], [100]]), lookback=1,
        initial_capital=1000, transaction_cost_bps=100, reward_mode="simple_return",
    )
    env.reset()
    _, reward, terminated, truncated, info = env.step(np.array([1], dtype=np.float32))
    assert reward == pytest.approx(-1 / 101)
    assert reward == info["net_return"]
    assert info["cost"] == pytest.approx(1000 / 101)
    assert info["equity"] == pytest.approx(1000 - info["cost"])
    assert terminated and not truncated


def test_risk_penalty_uses_only_lagged_variance():
    prices = panel([[100], [110], [99], [118.8], [237.6], [261.36]])
    plain = PortfolioEnv(prices, lookback=2, transaction_cost_bps=0)
    penalized = PortfolioEnv(prices, lookback=2, transaction_cost_bps=0, risk_penalty=3)
    plain.reset()
    penalized.reset()
    _, reward_plain, _, _, _ = plain.step(np.array([1], dtype=np.float32))
    _, reward_penalty, _, _, info = penalized.step(np.array([1], dtype=np.float32))
    expected = np.var(np.log([1.1, 0.9]), ddof=1)
    assert info["risk_variance"] == pytest.approx(expected)
    assert reward_plain - reward_penalty == pytest.approx(3 * expected)


def test_execution_close_and_future_prices_do_not_change_initial_observation_or_risk():
    first = panel([[100, 100], [105, 99], [110, 98], [120, 100], [121, 110], [123, 120]])
    second = panel([[100, 100], [105, 99], [110, 98], [300, 30], [600, 10], [5, 1000]])
    # lookback2 starts execution at3; first changed price is itself close3.
    a = PortfolioEnv(first, lookback=2, risk_penalty=2)
    b = PortfolioEnv(second, lookback=2, risk_penalty=2)
    obs_a, _ = a.reset(seed=2)
    obs_b, _ = b.reset(seed=2)
    np.testing.assert_array_equal(obs_a, obs_b)
    action = np.array([0.2, 0.8], dtype=np.float32)
    _, _, _, _, info_a = a.step(action)
    _, _, _, _, info_b = b.step(action)
    assert info_a["target_weights"] == info_b["target_weights"]
    assert info_a["risk_variance"] == info_b["risk_variance"]
    assert info_a["equity"] != info_b["equity"]


def test_appending_or_changing_future_prices_preserves_trajectory_prefix():
    original = long_panel()
    changed = original.prices.copy()
    changed[30:] *= np.array([2, 0.5])
    future = PricePanel(original.dates, original.assets, changed, original.metadata)
    a, b = PortfolioEnv(original, lookback=3), PortfolioEnv(future, lookback=3)
    np.testing.assert_array_equal(a.reset(seed=8)[0], b.reset(seed=8)[0])
    action = np.array([0.7, -0.2], dtype=np.float32)
    for _ in range(20):
        step_a, step_b = a.step(action), b.step(action)
        np.testing.assert_array_equal(step_a[0], step_b[0])
        assert step_a[1:] == step_b[1:]


def test_action_projection_can_reach_long_only_corners_and_equal_weights():
    env = PortfolioEnv(long_panel(), lookback=3, transaction_cost_bps=0)
    env.reset()
    for action, expected in [([0, 0], [0.5, 0.5]), ([1, -1], [1, 0]), ([-1, 1], [0, 1])]:
        observation, _, _, _, info = env.step(np.asarray(action, dtype=np.float32))
        assert info["target_weights"] == pytest.approx(expected)
        assert sum(info["target_weights"]) == pytest.approx(1)
        assert min(info["target_weights"]) >= 0
        assert max(info["target_weights"]) <= 1
        assert sum(info["next_drift_weights"]) == pytest.approx(1)
        assert env.observation_space.contains(observation)


@pytest.mark.parametrize("action", [
    [0], [[0, 0]], [math.nan, 0], [math.inf, 0], [1.001, 0], [-1.001, 0],
])
def test_invalid_action_is_rejected_without_mutating_financial_state(action):
    env = PortfolioEnv(long_panel(), lookback=3)
    initial, _ = env.reset()
    with pytest.raises(ValueError):
        env.step(np.asarray(action, dtype=np.float32))
    np.testing.assert_array_equal(env._observation(), initial)
    assert env._value == env.initial_capital
    assert env._steps == 0


def test_deterministic_seed_and_reset_restore_all_financial_state():
    env = PortfolioEnv(long_panel(), lookback=3)
    first, first_info = env.reset(seed=123)
    first_actions = [env.action_space.sample() for _ in range(4)]
    first_trajectory = [env.step(action) for action in first_actions]
    second, second_info = env.reset(seed=123)
    second_actions = [env.action_space.sample() for _ in range(4)]
    np.testing.assert_array_equal(first, second)
    assert first_info == second_info
    for original_action, repeated_action in zip(first_actions, second_actions, strict=True):
        np.testing.assert_array_equal(original_action, repeated_action)
    second_trajectory = [env.step(action) for action in second_actions]
    for original, repeated in zip(first_trajectory, second_trajectory, strict=True):
        np.testing.assert_array_equal(original[0], repeated[0])
        assert original[1:] == repeated[1:]


def test_step_before_reset_or_after_terminal_requires_reset():
    env = PortfolioEnv(panel([[100], [100], [100], [100]]), lookback=1)
    action = np.array([0], dtype=np.float32)
    with pytest.raises(RuntimeError, match="reset"):
        env.step(action)
    env.reset()
    assert env.step(action)[2] is True
    with pytest.raises(RuntimeError, match="reset"):
        env.step(action)
    env.reset()
    assert env.step(action)[2] is True


def test_explicit_horizon_is_truncation_and_reset_does_not_shift_dates():
    env = PortfolioEnv(long_panel(), lookback=3, max_episode_steps=1)
    _, start = env.reset(seed=1)
    _, _, terminated, truncated, info = env.step(np.zeros(2, dtype=np.float32))
    assert not terminated and truncated
    assert info["valuation_at"] == env.panel.dates[5]
    with pytest.raises(RuntimeError):
        env.step(np.zeros(2, dtype=np.float32))
    _, repeated_start = env.reset(seed=2)
    assert start == repeated_start


@pytest.mark.parametrize("config", [
    {"lookback": 0}, {"lookback": True}, {"lookback": 1.1}, {"lookback": 100},
    {"initial_capital": 0}, {"initial_capital": math.nan}, {"initial_capital": True},
    {"transaction_cost_bps": -1}, {"transaction_cost_bps": 101},
    {"transaction_cost_bps": math.inf}, {"risk_penalty": -1},
    {"risk_penalty": math.nan}, {"risk_penalty": 1000001},
    {"reward_mode": "unsupported"}, {"max_episode_steps": 0},
    {"max_episode_steps": True}, {"max_episode_steps": 1.5},
])
def test_invalid_environment_config_is_rejected(config):
    with pytest.raises(ValueError):
        PortfolioEnv(long_panel(), **config)


def test_reset_options_cannot_change_chronological_boundaries():
    env = PortfolioEnv(long_panel(), lookback=3)
    with pytest.raises(ValueError):
        env.reset(options={"start_index": 70})


def test_both_actual_gymnasium_and_stable_baselines_checkers_accept_environment():
    gym_check_env(PortfolioEnv(long_panel(), lookback=3), skip_render_check=True)
    sb3_check_env(PortfolioEnv(long_panel(), lookback=3), warn=True)
