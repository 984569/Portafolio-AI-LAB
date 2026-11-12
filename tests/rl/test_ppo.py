"""Actual small PPO updates on explicit synthetic train-only test panels."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch
from portfolio_core import PricePanel
from portfolio_env import PortfolioEnv
from portfolio_rl.common import load_bundle
from portfolio_rl.config import TrainingConfig
from portfolio_rl.ppo import train_ppo
from stable_baselines3 import PPO


def training_panel() -> PricePanel:
    """Offline test data, never a published or registered historical snapshot."""
    days = tuple((date(2018, 1, 1) + timedelta(days=i)).isoformat() for i in range(96))
    ticks = np.arange(len(days), dtype=np.float64)
    prices = np.column_stack(
        [
            100 * np.exp(0.001 * ticks + 0.008 * np.sin(ticks)),
            90 * np.exp(-0.0002 * ticks + 0.012 * np.cos(ticks)),
        ]
    )
    return PricePanel(
        days,
        ("SYNTHETIC_PPO_A", "SYNTHETIC_PPO_B"),
        prices,
        {
            "id": "historical-" + "1" * 64,
            "sha256": "1" * 64,
            "kind": "FIXTURE",
            "source": "OFFLINE PPO UNIT TEST ONLY",
        },
    )


def configuration(panel: PricePanel, **updates: Any) -> TrainingConfig:
    return TrainingConfig.model_validate(
        {
            "name": "PPO offline smoke",
            "algorithm": "ppo",
            "dataset_id": panel.metadata["id"],
            "seed": 42,
            "lookback": 3,
            "total_timesteps": 128,
            "net_arch": [16, 16],
            "checkpoint_frequency": 64,
            "max_seconds": 60,
            "max_memory_mb": 2048,
            "training_end": panel.dates[-1],
            "ppo": {"n_steps": 64, "batch_size": 32, "n_epochs": 2},
            **updates,
        }
    )


def test_actual_ppo_updates_actor_saves_checkpoint_and_predicts_valid_allocations(
    tmp_path: Path,
) -> None:
    panel = training_panel()
    config = configuration(panel)
    torch.set_num_threads(1)
    original_env = PortfolioEnv(panel, lookback=config.lookback)
    original = PPO(
        "MlpPolicy",
        original_env,
        n_steps=64,
        batch_size=32,
        n_epochs=2,
        policy_kwargs={"net_arch": {"pi": [16, 16], "vf": [16, 16]}},
        seed=config.seed,
        device="cpu",
        verbose=0,
    )
    before = original.policy.action_net.weight.detach().clone()
    original_env.close()
    progress: list[dict[str, Any]] = []
    manifest = train_ppo(panel, config, tmp_path / "trained", progress=progress.append)
    assert manifest["status"] == "completed"
    assert manifest["actual_timesteps"] == config.total_timesteps
    assert (tmp_path / "trained/model.zip").is_file()
    assert (tmp_path / "trained/normalizer.json").is_file()
    assert (tmp_path / "trained/manifest.json").is_file()
    trained = PPO.load(tmp_path / "trained/model.zip", device="cpu")
    assert not torch.equal(before, trained.policy.action_net.weight.detach())
    assert progress, "Real callback progress must be emitted"
    checkpoint_dirs = sorted((tmp_path / "trained/checkpoints").iterdir())
    assert len(checkpoint_dirs) == 2
    env = PortfolioEnv(panel, lookback=config.lookback)
    observation, _ = env.reset(seed=42)
    first = load_bundle(tmp_path / "trained")
    second = load_bundle(tmp_path / "trained")
    action = first.predict(observation, deterministic=True)
    np.testing.assert_array_equal(action, second.predict(observation, deterministic=True))
    assert action.shape == env.action_space.shape
    assert np.isfinite(action).all()
    assert np.isfinite(load_bundle(checkpoint_dirs[0]).predict(observation)).all()
    _, reward, _, _, info = env.step(action)
    assert np.isfinite(reward)
    assert sum(info["target_weights"]) == pytest.approx(1)
    assert min(info["target_weights"]) >= 0
    env.close()


def test_same_seed_retrains_same_policy_predictions(tmp_path: Path) -> None:
    panel = training_panel()
    config = configuration(panel)
    train_ppo(panel, config, tmp_path / "first")
    train_ppo(panel, config, tmp_path / "second")
    env = PortfolioEnv(panel, lookback=config.lookback)
    observation, _ = env.reset(seed=42)
    one, two = load_bundle(tmp_path / "first"), load_bundle(tmp_path / "second")
    for _ in range(4):
        first = one.predict(observation, deterministic=True)
        np.testing.assert_array_equal(first, two.predict(observation, deterministic=True))
        observation, _, _, _, _ = env.step(first)
    env.close()


def test_ppo_resume_is_functional_with_same_normalizer_and_compatible_settings(
    tmp_path: Path,
) -> None:
    panel = training_panel()
    config = configuration(panel)
    first = train_ppo(panel, config, tmp_path / "first")
    resumed = train_ppo(panel, config, tmp_path / "resumed", resume_from=tmp_path / "first")
    assert first["status"] == resumed["status"] == "completed"
    assert resumed["actual_timesteps"] > first["actual_timesteps"]
    env = PortfolioEnv(panel, lookback=config.lookback)
    observation, _ = env.reset(seed=42)
    assert np.isfinite(load_bundle(tmp_path / "resumed").predict(observation)).all()
    env.close()


def test_ppo_rejects_other_algorithm_before_creating_artifacts(tmp_path: Path) -> None:
    panel = training_panel()
    config = configuration(panel, algorithm="ddpg", ddpg={"learning_starts": 16})
    with pytest.raises(ValueError, match="algorithm"):
        train_ppo(panel, config, tmp_path / "wrong")
    assert not (tmp_path / "wrong").exists()


def test_ppo_does_not_train_a_2024_only_panel(tmp_path: Path) -> None:
    panel = training_panel()
    config = configuration(panel)
    dates = tuple((date(2024, 1, 1) + timedelta(days=i)).isoformat() for i in range(len(panel)))
    holdout = PricePanel(dates, panel.assets, panel.prices, panel.metadata)
    with pytest.raises(ValueError):
        train_ppo(holdout, config, tmp_path / "holdout")
    assert not (tmp_path / "holdout/model.zip").exists()


def test_ppo_cooperative_cancellation_is_not_reported_as_completed(tmp_path: Path) -> None:
    panel = training_panel()
    config = configuration(panel)
    manifest = train_ppo(panel, config, tmp_path / "cancelled", cancelled=lambda: True)
    assert manifest["status"] == "cancelled"
    assert manifest["actual_timesteps"] < config.total_timesteps
