"""Financial replays; normalization belongs to the frozen verified predictor."""

import math
from collections.abc import Callable, Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray
from portfolio_core import PricePanel, financial_metrics
from portfolio_env import PortfolioEnv
from portfolio_research import run_historical_backtest

from .statistics import extra_metrics
from .temporal import canonical_date, evaluation_window

Predictor = Callable[[NDArray[np.float32]], NDArray[np.float32]]


def _number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} is outside supported finite bounds")
    return value


def _configuration(
    panel: PricePanel, config: Mapping[str, Any], strategies: set[str]
) -> dict[str, Any]:
    name = config.get("name")
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or len(name) > 80:
        raise ValueError("name must contain1–80 characters")
    strategy = config.get("strategy", "ppo")
    if strategy not in strategies:
        raise ValueError("Unsupported evaluation strategy")
    lookback = config.get("lookback", 60)
    if isinstance(lookback, bool) or not isinstance(lookback, int) or not 2 <= lookback <= 252:
        raise ValueError("lookback must be an integer between2 and252")
    seed = config.get("seed", 42)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2147483647:
        raise ValueError("seed must be an integer between0 and2147483647")
    dataset_id = config.get("dataset_id", panel.metadata.get("id"))
    if dataset_id != panel.metadata.get("id"):
        raise ValueError("Configuration dataset does not match the source panel")
    capital = _number(config.get("initial_capital", 10000), "initial_capital", 0, 1e9)
    if capital <= 0:
        raise ValueError("initial_capital must be positive")
    reward_mode = config.get("reward_mode", "log_return")
    if reward_mode not in {"log_return", "simple_return"}:
        raise ValueError("Unsupported reward_mode")
    if config.get("split") not in {None, "train", "validation", "walk_forward"}:
        raise ValueError("Final holdout evaluation is locked")
    return {
        "name": name,
        "strategy": strategy,
        "dataset_id": dataset_id,
        "lookback": lookback,
        "seed": seed,
        "initial_capital": capital,
        "transaction_cost_bps": _number(
            config.get("transaction_cost_bps", 10), "transaction_cost_bps", 0, 100
        ),
        "risk_free_rate": _number(config.get("risk_free_rate", 0), "risk_free_rate", -0.99, 1),
        "reward_mode": reward_mode,
        "risk_penalty": _number(config.get("risk_penalty", 0), "risk_penalty", 0, 1e6),
    }


def evaluate_policy(
    panel: PricePanel,
    predictor: Predictor,
    config: Mapping[str, Any],
    *,
    train_end: str,
    eval_start: str = "2022-01-01",
    eval_end: str = "2023-12-31",
) -> dict[str, Any]:
    """Evaluate deterministic actions, never fitting or updating a normalizer.

    Pass PolicyBundle.predict (or another frozen raw-observation callable). The
    model/bundle owner verifies checkpoint integrity and train-only fitted stats.
    This function feeds only the environment's lagged observation to that callable;
    post-transition info and realized rewards never enter the policy input.
    """
    cfg = _configuration(panel, config, {"ppo", "ddpg"})
    train_end = canonical_date(train_end, "train_end")
    eval_start, eval_end = (
        canonical_date(eval_start, "eval_start"),
        canonical_date(eval_end, "eval_end"),
    )
    if not "2015-01-01" <= train_end <= "2021-12-31" or eval_start <= train_end:
        raise ValueError("Evaluation must follow training; training ends by2021")
    window = evaluation_window(panel, eval_start, eval_end, cfg["lookback"])
    env = PortfolioEnv(
        window,
        lookback=cfg["lookback"],
        initial_capital=cfg["initial_capital"],
        transaction_cost_bps=cfg["transaction_cost_bps"],
        reward_mode=cfg["reward_mode"],
        risk_penalty=cfg["risk_penalty"],
    )
    observation, reset_info = env.reset(seed=cfg["seed"])
    equity = [
        {"date": reset_info["execution_at"], "equity": cfg["initial_capital"], "net_return": 0.0}
    ]
    allocations: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    rewards: list[float] = []
    try:
        while True:
            action = np.asarray(predictor(observation.copy()), dtype=np.float32)
            observation, reward, terminated, truncated, info = env.step(action)
            if truncated:
                raise ValueError(
                    "Financial validation cannot silently truncate its requested horizon"
                )
            if not info["information_as_of"] < info["execution_at"] < info["valuation_at"]:
                raise ValueError("Environment violated the information/decision/valuation clocks")
            if info["valuation_at"] >= "2024-01-01":
                raise ValueError("Final2024 holdout cannot enter validation output")
            equity.append(
                {
                    "date": info["valuation_at"],
                    "equity": info["equity"],
                    "net_return": info["net_return"],
                }
            )
            allocations.append(
                {
                    "date": info["execution_at"],
                    "weights": dict(zip(window.assets, info["target_weights"], strict=True)),
                    "turnover": info["turnover"],
                    "cost": info["cost"],
                }
            )
            decisions.append(
                {
                    "information_as_of": info["information_as_of"],
                    "execution_at": info["execution_at"],
                    "valuation_at": info["valuation_at"],
                    "traded_notional": info["traded_notional"],
                }
            )
            rewards.append(reward)
            if terminated:
                break
    finally:
        env.close()
    costs = math.fsum(item["cost"] for item in allocations)
    result: dict[str, Any] = {
        "metrics": financial_metrics(
            [point["equity"] for point in equity], cfg["risk_free_rate"], costs
        ),
        "equity": equity,
        "allocations": allocations,
        "audit": [
            {
                "date": equity[0]["date"],
                "event": "rl_evaluation_started",
                "detail": f"PAPER: frozen {cfg['strategy']} policy; training through {train_end}.",
            },
            {
                "date": equity[-1]["date"],
                "event": "rl_evaluation_completed",
                "detail": "Validation complete; no fitting, normalizer updates or2024 evaluation.",
            },
        ],
        "manifest": {
            "engine_version": "0.3.0",
            "accounting_version": "exact-self-financing-v1",
            "dataset_id": cfg["dataset_id"],
            "dataset_sha256": panel.metadata.get("sha256"),
            "data_mode": panel.metadata.get("kind", "HISTORICAL"),
            "mode": "PAPER",
            "configuration": cfg,
            "training_end": train_end,
            "requested_evaluation": {"start": eval_start, "end": eval_end},
            "evaluation": {
                "split": "validation" if eval_start >= "2022-01-01" else "walk_forward",
                "start_date": equity[0]["date"],
                "end_date": equity[-1]["date"],
                "intervals": len(allocations),
                "holdout_evaluated": False,
            },
            "timing_convention": {
                "information": "Lagged log returns and targets known at t-1",
                "execution": "Stylized adjusted close t; t-to-t+1 adjusted-price ratio",
                "costs": "Exact self-financing proportional buy-plus-sell fees, entry included",
                "terminal_liquidation": False,
            },
            "action_transform": "euclidean_simplex_projection_from_Box[-1,1]",
            "normalization": "Delegated to frozen verified predictor; evaluator never fits stats",
            "learning_evaluation": {
                "reward_mode": cfg["reward_mode"],
                "risk_penalty": cfg["risk_penalty"],
                "reward_sum": math.fsum(rewards),
                "reward_mean": float(np.mean(rewards)),
                "fees_already_in_net_growth": True,
            },
            "decisions": decisions,
        },
    }
    result["manifest"]["research_metrics"] = extra_metrics(result)
    return result


def evaluate_baseline_window(
    panel: PricePanel, config: Mapping[str, Any], *, eval_start: str, eval_end: str
) -> dict[str, Any]:
    """Use unchanged Stage2 benchmark code on the identical warmup/evaluation slice."""
    cfg = _configuration(panel, config, {"equal_weight", "markowitz"})
    window = evaluation_window(panel, eval_start, eval_end, cfg["lookback"])
    if eval_end <= "2021-12-31":
        split = "train"
    elif eval_start >= "2022-01-01":
        split = "validation"
    else:
        raise ValueError("A benchmark window cannot cross the train/validation boundary")
    baseline = {
        key: value for key, value in cfg.items() if key not in {"reward_mode", "risk_penalty"}
    }
    baseline["split"] = split
    baseline["risk_aversion"] = config.get("risk_aversion", 5)
    result = run_historical_backtest(window, baseline)
    result["manifest"]["research_metrics"] = extra_metrics(result)
    result["manifest"]["requested_evaluation"] = {"start": eval_start, "end": eval_end}
    return result
