"""Real CPU DDPG learning on offline test inputs, never historical evidence."""

from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch
from portfolio_core import PricePanel
from portfolio_env import PortfolioEnv
from portfolio_rl import ddpg as module
from portfolio_rl.common import load_bundle
from portfolio_rl.config import TrainingConfig
from stable_baselines3 import DDPG
from stable_baselines3.common.noise import NormalActionNoise


def offline_panel() -> PricePanel:
    generator = np.random.default_rng(17)
    prices = 100 * np.exp(np.cumsum(generator.normal(0.001, 0.01, (64, 3)), axis=0))
    dates = tuple((date(2018, 1, 1) + timedelta(days=index)).isoformat() for index in range(64))
    return PricePanel(
        dates,
        ("TEST_A", "TEST_B", "TEST_C"),
        prices,
        {
            "id": "historical-" + "a" * 64,
            "sha256": "a" * 64,
            "kind": "FIXTURE",
            "source": "In-memory offline DDPG test only",
        },
    )


def configuration(**changes: Any) -> TrainingConfig:
    values: dict[str, Any] = {
        "name": "Offline DDPG integration",
        "algorithm": "ddpg",
        "dataset_id": "historical-" + "a" * 64,
        "total_timesteps": 64,
        "lookback": 3,
        "net_arch": [16, 16],
        "checkpoint_frequency": 32,
        "max_seconds": 60,
        "ddpg": {
            "buffer_size": 256,
            "batch_size": 16,
            "learning_starts": 16,
            "noise_sigma": 0.1,
        },
    }
    values.update(changes)
    return TrainingConfig.model_validate(values)


def raw_observation(panel: PricePanel) -> np.ndarray:
    env = PortfolioEnv(panel, lookback=3)
    try:
        return env.reset(seed=42)[0]
    finally:
        env.close()


def assert_same_policy(first: DDPG, second: DDPG) -> None:
    a, b = first.policy.state_dict(), second.policy.state_dict()
    assert a.keys() == b.keys()
    assert all(torch.equal(a[key], b[key]) for key in a)


def test_ddpg_performs_actor_and_critic_updates_with_real_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[Any] = []

    class CapturedDDPG(DDPG):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            if hasattr(self, "actor"):
                self.actor_before = [
                    parameter.detach().clone() for parameter in self.actor.parameters()
                ]
                self.critic_before = [
                    parameter.detach().clone() for parameter in self.critic.parameters()
                ]
                captured.append(self)

    monkeypatch.setattr(module, "DDPG", CapturedDDPG)
    manifest = module.train_ddpg(offline_panel(), configuration(), tmp_path / "smoke")
    model = captured[0]
    assert manifest["status"] == "completed"
    assert manifest["actual_timesteps"] == 64
    assert model._n_updates == 48
    assert model.replay_buffer.size() == 64
    assert isinstance(model.action_noise, NormalActionNoise)
    np.testing.assert_allclose(model.action_noise._sigma, [0.1, 0.1, 0.1])
    assert any(
        not torch.equal(old, new)
        for old, new in zip(model.actor_before, model.actor.parameters(), strict=True)
    )
    assert any(
        not torch.equal(old, new)
        for old, new in zip(model.critic_before, model.critic.parameters(), strict=True)
    )
    assert manifest["learning_metrics"]
    assert any(name.startswith("train/") for name in manifest["learning_metrics"])


def test_ddpg_checkpoint_and_bundle_reproduce_predictions_and_financial_actions(
    tmp_path: Path,
) -> None:
    panel = offline_panel()
    output = tmp_path / "artifact"
    manifest = module.train_ddpg(panel, configuration(), output)
    assert set(manifest["files"]) == {"model.zip", "normalizer.json", "replay_buffer.pkl"}
    checkpoint = output / manifest["checkpoints"][0]["path"]
    assert (checkpoint / "manifest.json").is_file()
    loaded = load_bundle(output)
    restored = load_bundle(output)
    observation = raw_observation(panel)
    np.testing.assert_array_equal(loaded.predict(observation), restored.predict(observation))
    env = PortfolioEnv(panel, lookback=3)
    observation, _ = env.reset(seed=42)
    for _ in range(10):
        action = loaded.predict(observation, deterministic=True)
        assert action.dtype == np.float32
        assert env.action_space.contains(action)
        observation, reward, _, _, info = env.step(action)
        assert np.isfinite(reward) and info["equity"] > 0
        assert info["cost"] >= 0
        assert min(info["target_weights"]) >= 0
        assert sum(info["target_weights"]) == pytest.approx(1)
    env.close()


def test_ddpg_fresh_same_seed_matches_weights_and_distinct_seed_changes_them(
    tmp_path: Path,
) -> None:
    panel = offline_panel()
    for name, seed in (("first", 42), ("second", 42), ("other", 7)):
        module.train_ddpg(panel, configuration(seed=seed), tmp_path / name)
    first = DDPG.load(tmp_path / "first/model.zip", device="cpu")
    second = DDPG.load(tmp_path / "second/model.zip", device="cpu")
    other = DDPG.load(tmp_path / "other/model.zip", device="cpu")
    assert_same_policy(first, second)
    assert any(
        not torch.equal(value, other.policy.state_dict()[key])
        for key, value in first.policy.state_dict().items()
    )


def test_ddpg_resume_restores_replay_and_performs_additional_training(tmp_path: Path) -> None:
    panel = offline_panel()
    original = module.train_ddpg(panel, configuration(), tmp_path / "original")
    continued = module.train_ddpg(
        panel,
        configuration(name="Functional resume"),
        tmp_path / "continued",
        resume_from=tmp_path / "original",
    )
    assert continued["resumed"]
    assert continued["starting_timesteps"] == original["actual_timesteps"]
    assert continued["actual_timesteps"] == original["actual_timesteps"] + 64
    assert "not bitwise" in continued["resume_semantics"]
    restored = DDPG.load(tmp_path / "continued/model.zip", device="cpu")
    restored.load_replay_buffer(tmp_path / "continued/replay_buffer.pkl")
    assert restored.replay_buffer is not None
    assert restored.replay_buffer.size() == 128
    assert restored._n_updates > 48


def test_ddpg_changed_economics_cannot_resume(tmp_path: Path) -> None:
    panel = offline_panel()
    module.train_ddpg(panel, configuration(), tmp_path / "original")
    with pytest.raises(ValueError, match="Resume"):
        module.train_ddpg(
            panel,
            configuration(transaction_cost_bps=20),
            tmp_path / "other",
            resume_from=tmp_path / "original",
        )


def test_ddpg_corrupt_replay_is_rejected_before_unpickling(tmp_path: Path) -> None:
    panel = offline_panel()
    output = tmp_path / "original"
    module.train_ddpg(panel, configuration(), output)
    path = output / "replay_buffer.pkl"
    path.write_bytes(path.read_bytes() + b"tampered offline checkpoint")
    with pytest.raises(ValueError, match="integrity"):
        module.train_ddpg(panel, configuration(), tmp_path / "other", resume_from=output)


def test_ddpg_panel_with_validation_or_2024_is_rejected_before_training(tmp_path: Path) -> None:
    original = offline_panel()
    for stamp in ("2022-01-03", "2024-01-02"):
        panel = PricePanel(
            (*original.dates, stamp),
            original.assets,
            np.vstack([original.prices, original.prices[-1]]),
            original.metadata,
        )
        with pytest.raises(ValueError, match="chronological"):
            module.train_ddpg(panel, configuration(), tmp_path / stamp)
        assert not (tmp_path / stamp).exists()


def test_ddpg_wrong_algorithm_rejected_without_artifacts(tmp_path: Path) -> None:
    config = configuration(algorithm="ppo", ppo={"n_steps": 32, "batch_size": 16})
    with pytest.raises(ValueError, match="algorithm"):
        module.train_ddpg(offline_panel(), config, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()
