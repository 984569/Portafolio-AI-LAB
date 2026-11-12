"""Long-only portfolio MDP with a deliberately lagged information clock.

For a decision executed at close t, observations contain log price relatives
ending at t-1 and portfolio targets last chosen at t-1. Revalued execution-time
weights are kept internal: showing them would indirectly reveal close t.
Targets trade at close t; net equity is valued at close t+1 using the shared
exact self-financing fee engine. Adjusted prices are total-return research
units, not a claim that retrospective adjusted closes were executable quotes.
"""

from typing import Any, Literal

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from numpy.typing import NDArray
from portfolio_core import PricePanel, project_simplex, rebalance_step

FloatArray = NDArray[np.float32]
RewardMode = Literal["log_return", "simple_return"]


class PortfolioEnv(gym.Env[FloatArray, FloatArray]):
    """Allocate a portfolio with continuous, simplex-projected actions.

    Observation: flattened (lookback, n_assets) log-return window through t-1,
    then n_assets lagged target weights. Initial zero asset weights mean cash.
    Logs are computed as log(P_next)-log(P_previous), not log(P_next/P_previous),
    avoiding overflow/underflow in observation ratios. No future-fitted scaler.

    Action: Box[-1,1]^N projected Euclideanly onto the long-only unit simplex.
    Zero actions map to equal weights. Projection permits exact zero/one weights;
    invalid or out-of-bounds actions are rejected rather than silently clipped.

    Reward: log(net equity growth) or simple net return, minus risk_penalty
    times sample variance of *lagged* target-weighted log returns. Fees are
    already in net growth and are never subtracted again. No leverage/shorts,
    terminal liquidation, order-book/slippage or market-impact model is implied.

    Episode starts at index lookback+1 and ends on final dataset valuation.
    max_episode_steps applies an optional distinct truncation horizon. Reset
    does not randomly move across dates or partitions, regardless of seed.
    Caller owns selecting a chronological train/validation/final-test panel;
    this environment performs no fitting, downloading or holdout selection.
    """

    metadata: dict[str, Any] = {"render_modes": []}

    def __init__(
        self,
        panel: PricePanel,
        lookback: int = 20,
        initial_capital: float = 10000,
        transaction_cost_bps: float = 10,
        reward_mode: RewardMode = "log_return",
        risk_penalty: float = 0.0,
        max_episode_steps: int | None = None,
    ) -> None:
        super().__init__()
        if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 1:
            raise ValueError("lookback must be a positive integer")
        if len(panel.dates) < lookback + 3:
            raise ValueError("Panel requires lookback+3 observations for an executable episode")
        if reward_mode not in {"log_return", "simple_return"}:
            raise ValueError("Unsupported reward_mode")
        for label, value in (
            ("initial_capital", initial_capital),
            ("transaction_cost_bps", transaction_cost_bps),
            ("risk_penalty", risk_penalty),
        ):
            if isinstance(value, bool) or not np.isfinite(value):
                raise ValueError(f"{label} must be finite")
        if not 0 < initial_capital <= 1e9:
            raise ValueError("initial_capital must be positive and at most 1e9")
        if not 0 <= transaction_cost_bps <= 100:
            raise ValueError("transaction_cost_bps must be between 0 and 100")
        if not 0 <= risk_penalty <= 1e6:
            raise ValueError("risk_penalty must be between 0 and 1e6")
        if max_episode_steps is not None and (
            isinstance(max_episode_steps, bool)
            or not isinstance(max_episode_steps, int)
            or max_episode_steps < 1
        ):
            raise ValueError("max_episode_steps must be a positive integer or None")

        self.panel = panel
        self.lookback = lookback
        self.initial_capital = float(initial_capital)
        self.transaction_cost_bps = float(transaction_cost_bps)
        self.reward_mode = reward_mode
        self.risk_penalty = float(risk_penalty)
        self.max_episode_steps = max_episode_steps
        self.n_assets = len(panel.assets)
        # This contains future data internally, but observation slices and the
        # variance penalty below are explicitly bounded to the information clock.
        self._log_returns = np.diff(np.log(panel.prices), axis=0)
        self.action_space = spaces.Box(-1.0, 1.0, shape=(self.n_assets,), dtype=np.float32)
        low = np.concatenate(
            [
                np.full(lookback * self.n_assets, -2000, dtype=np.float32),
                np.zeros(self.n_assets, dtype=np.float32),
            ]
        )
        high = np.concatenate(
            [
                np.full(lookback * self.n_assets, 2000, dtype=np.float32),
                np.ones(self.n_assets, dtype=np.float32),
            ]
        )
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.float32)
        self._index = lookback + 1
        self._value = self.initial_capital
        self._drift_weights: NDArray[np.float64] | None = None
        self._known_weights = np.zeros(self.n_assets, dtype=np.float64)
        self._steps = 0
        self._needs_reset = True

    def _history(self) -> NDArray[np.float64]:
        # Return j joins prices j to j+1; last allowed close is index-1.
        return self._log_returns[self._index - self.lookback - 1 : self._index - 1]

    def _observation(self) -> FloatArray:
        observation = np.concatenate([self._history().ravel(), self._known_weights]).astype(
            np.float32
        )
        if not self.observation_space.contains(observation):
            raise ValueError("Observation violates finite, lagged state bounds")
        return observation

    def _reset_info(self) -> dict[str, Any]:
        return {
            "mode": "PAPER",
            "information_as_of": self.panel.dates[self._index - 1],
            "execution_at": self.panel.dates[self._index],
            "equity": self._value,
            "dataset_id": self.panel.metadata.get("id"),
            "dataset_sha256": self.panel.metadata.get("sha256"),
            "action_transform": "euclidean_simplex_projection",
            "observation_returns": "lagged_log_price_relatives",
        }

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[FloatArray, dict[str, Any]]:
        super().reset(seed=seed)
        if options:
            raise ValueError("Reset options cannot change chronological episode boundaries")
        if seed is not None:
            self.action_space.seed(seed)
        self._index = self.lookback + 1
        self._value = self.initial_capital
        self._drift_weights = None
        self._known_weights = np.zeros(self.n_assets, dtype=np.float64)
        self._steps = 0
        self._needs_reset = False
        return self._observation(), self._reset_info()

    def step(self, action: FloatArray) -> tuple[FloatArray, float, bool, bool, dict[str, Any]]:
        if self._needs_reset:
            raise RuntimeError("Call reset before step or after episode termination/truncation")
        raw = np.asarray(action, dtype=np.float64)
        if raw.shape != (self.n_assets,) or not np.isfinite(raw).all():
            raise ValueError("Action must be a finite vector matching the asset universe")
        if np.any(raw < -1) or np.any(raw > 1):
            raise ValueError("Action must lie inside Box[-1,1]; clipping is not implicit")
        target = project_simplex(raw)
        risk_variance = (
            float(np.var(self._history() @ target, ddof=1)) if self.lookback > 1 else 0.0
        )
        previous_index = self._index
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            relatives = self.panel.prices[previous_index + 1] / self.panel.prices[previous_index]
        transition = rebalance_step(
            self._value, self._drift_weights, target, relatives, self.transaction_cost_bps
        )
        net_return = transition.net_return
        base_reward = (
            float(np.log(transition.equity) - np.log(self._value))
            if self.reward_mode == "log_return"
            else net_return
        )
        reward = float(base_reward - self.risk_penalty * risk_variance)
        if not np.isfinite(reward):
            raise ValueError("Non-finite reward")

        # State mutations follow successful accounting/reward validation only.
        self._value = transition.equity
        self._drift_weights = transition.weights.copy()
        self._known_weights = target.copy()
        self._steps += 1
        self._index += 1
        terminated = self._index >= len(self.panel.dates) - 1
        truncated = not terminated and (
            self.max_episode_steps is not None and self._steps >= self.max_episode_steps
        )
        self._needs_reset = terminated or truncated
        info = {
            "mode": "PAPER",
            "information_as_of": self.panel.dates[previous_index - 1],
            "execution_at": self.panel.dates[previous_index],
            "valuation_at": self.panel.dates[self._index],
            "equity": transition.equity,
            "net_return": net_return,
            "cost": transition.cost,
            "turnover": transition.turnover,
            "traded_notional": transition.traded_notional,
            "raw_action": raw.tolist(),
            "target_weights": target.tolist(),
            "next_drift_weights": transition.weights.tolist(),
            "risk_variance": risk_variance,
            "risk_penalty": self.risk_penalty,
            "reward_mode": self.reward_mode,
            "action_transform": "euclidean_simplex_projection",
        }
        return self._observation(), reward, bool(terminated), bool(truncated), info
