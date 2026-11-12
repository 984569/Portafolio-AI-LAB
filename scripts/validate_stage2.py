"""Verify real historical replay and Gym/SB3 compatibility; never evaluate 2024."""

import argparse
import hashlib
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

import numpy as np  # noqa: E402
from gymnasium.utils.env_checker import check_env as gym_check  # noqa: E402
from market_data import list_snapshots, load_snapshot  # noqa: E402
from portfolio_core import PricePanel  # noqa: E402
from portfolio_env import PortfolioEnv  # noqa: E402
from portfolio_research import run_historical_backtest  # noqa: E402
from stable_baselines3.common.env_checker import check_env as sb3_check  # noqa: E402


def fingerprint(result: dict[str, Any]) -> str:
    encoded = json.dumps(result, sort_keys=True, allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / ".runtime/datasets")
    parser.add_argument("--config", type=Path, default=ROOT / "experiments/stage2-baseline.json")
    parser.add_argument("--output", type=Path, default=ROOT / ".runtime/stage2-validation.json")
    args = parser.parse_args()
    profile = json.loads(args.config.read_text(encoding="utf-8"))
    datasets = list_snapshots(args.root)
    if not datasets:
        raise RuntimeError("No verified historical snapshot exists. Run download_history.py first.")
    panel = load_snapshot(args.root, datasets[-1]["id"])
    report: dict[str, Any] = {
        "recorded_at": datetime.now(UTC).isoformat(),
        "mode": "PAPER",
        "dataset": panel.metadata,
        "holdout_2024_evaluated": False,
        "benchmarks": {},
        "configuration_file_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
    }
    for strategy in ("equal_weight", "markowitz"):
        config = {
            **profile,
            "name": f"Stage2 historical {strategy}",
            "dataset_id": panel.metadata["id"],
            "strategy": strategy,
        }
        first, second = (run_historical_backtest(panel, config) for _ in range(2))
        assert fingerprint(first) == fingerprint(second), "Replay was not deterministic"
        assert first["equity"][-1]["date"] <= "2023-12-31"
        assert all(
            item["information_as_of"] < item["execution_at"]
            for item in first["manifest"]["decisions"]
        )
        report["benchmarks"][strategy] = {
            "configuration": config,
            "metrics": first["metrics"],
            "evaluation": first["manifest"]["evaluation"],
            "optimizer": first["manifest"]["optimizer"],
            "result_sha256": fingerprint(first),
            "identical_replays": 2,
        }
    selected = [index for index, stamp in enumerate(panel.dates) if stamp <= "2021-12-31"]
    training = PricePanel(
        tuple(panel.dates[index] for index in selected),
        panel.assets,
        panel.prices[selected],
        panel.metadata,
    )
    env = PortfolioEnv(training, lookback=20)
    gym_check(env, skip_render_check=True)
    sb3_check(env, warn=True)
    observation, _ = env.reset(seed=42)
    steps, costs = 0, 0.0
    while True:
        observation, reward, terminated, truncated, info = env.step(
            np.zeros(len(panel.assets), dtype=np.float32)
        )
        assert np.isfinite(observation).all() and math.isfinite(reward)
        assert env.observation_space.contains(observation)
        assert info["information_as_of"] < info["execution_at"] < info["valuation_at"]
        assert info["valuation_at"] <= "2021-12-31"
        assert math.isclose(sum(info["next_drift_weights"]), 1, abs_tol=1e-9)
        costs += info["cost"]
        steps += 1
        if terminated or truncated:
            break
    expected = run_historical_backtest(
        training,
        {
            "name": "Environment accounting reference",
            "split": "train",
            "lookback": 20,
        },
    )
    assert math.isclose(info["equity"], expected["metrics"]["final_equity"], rel_tol=1e-10)
    report["environment"] = {
        "gymnasium_checker": "passed",
        "sb3_checker": "passed",
        "training_only": True,
        "start_date": training.dates[0],
        "end_date": training.dates[-1],
        "steps": steps,
        "final_equity": info["equity"],
        "total_costs": costs,
        "observation_shape": list(env.observation_space.shape),
        "action_shape": list(env.action_space.shape),
        "seed": 42,
        "accounting_matches_benchmark": True,
        "model_training_performed": False,
    }
    env.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "passed",
                "dataset_id": panel.metadata["id"],
                "report": str(args.output),
                "environment_steps": steps,
            }
        )
    )


if __name__ == "__main__":
    main()
