# PPO and DDPG research protocol

Both trainers use Stable-Baselines3 and PyTorch on CPU. PPO uses an actor and
value function with clipped policy updates and generalized advantage estimation.
DDPG uses a deterministic actor, a critic, Gaussian exploration noise and
off-policy replay with soft target updates. Both have configurable MLP layers,
learning rate, seed and step budget. The exact parameters for each run are in
its manifest. The full defaults and allowed settings are documented in
[the training contract](STAGE3-CONTRACTS.md).

With ten assets and a 60-session lookback, the observation has 610 float32
values: 600 lagged log returns and 10 lagged target weights. The policy receives
returns through close t−1. At close t the environment projects continuous
actions onto the long-only unit simplex and rebalances. The next close values
the new holdings. Accounting charges the proportional fee on traded holdings
with exact self-financing. With net portfolio value V and penalty coefficient
λ, the default step reward is log(V[t+1]/V[t]) − λ × lagged portfolio return
variance. The study sets λ=0. Simple net return is also supported as the
first term. See the [Stage 2 contract](STAGE2-CONTRACTS.md) for the exact
observation and reward conventions.

The observation transform uses per-asset log-return mean and standard deviation
from the training partition. It leaves target weights on their original scale
and clips normalized observations at ±10. It is fitted once per training run
and frozen for inference. Whole-partition scaling is available to the offline
learner during training, and every scored window is later than that fit. The
validation replay performs deterministic inference without policy updates or
exploration noise.

The predeclared [experiment protocol](../experiments/stage3-protocol.json)
compares two learning rates per algorithm with seed 42 and 2,048 steps per job.
The two development folds train through 2018 and 2020 and score 2019 and 2021,
respectively. The mean fold Sharpe selects a rate from the tested candidates.
Each selected rate is used to train on 2015–2021 with seeds 7, 42 and 123.
The study evaluates every seed on 2022–2023. Checkpoints are saved at the declared
step cadence. Financial evaluation is performed after the development and final
jobs with their respective evaluation windows.

The four strategies use the same snapshot, 60-session window, USD 10,000 capital,
10 bps cost and zero risk-free rate. Markowitz uses risk aversion 5. PPO and
DDPG have different declared learning budgets. The comparison reports realized
net return, annualized return and volatility, Sharpe, drawdown magnitude, fees
and turnover. It retains the equity path and target weights in the runtime
report. Seed dispersion describes sensitivity to initialization on one validation
period. The seed-42 paired block bootstrap compares daily net returns with
equal-weight and is exploratory.

The study uses a fixed present-day universe and vendor-adjusted price history.
The accounting models adjusted-close fills and proportional fees. Conclusions
are conditional on that dataset and execution model. The 2024 holdout remains
locked for fitting, candidate selection and evaluation.
