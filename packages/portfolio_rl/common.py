"""Train-only normalization, callbacks, verified checkpoints and frozen inference."""

from __future__ import annotations

import hashlib
import json
import math
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
import psutil
import torch
from numpy.typing import NDArray
from portfolio_core import PricePanel
from portfolio_env import PortfolioEnv
from stable_baselines3.common.base_class import BaseAlgorithm
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.off_policy_algorithm import OffPolicyAlgorithm

from .config import TrainingConfig

Progress = Callable[[dict[str, Any]], None]
Cancelled = Callable[[], bool]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    # Windows readers briefly deny replacement while the supervisor polls JSON.
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.01 * (attempt + 1))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compatibility_signature(config: TrainingConfig) -> str:
    values = config.model_dump(
        exclude={
            "name",
            "total_timesteps",
            "checkpoint_frequency",
            "max_seconds",
            "max_memory_mb",
        }
    )
    return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


@dataclass
class Normalizer:
    mean: NDArray[np.float64]
    scale: NDArray[np.float64]
    enabled: bool
    fit_end: str

    def transform(self, observation: NDArray[Any]) -> NDArray[np.float32]:
        raw = np.asarray(observation, dtype=np.float64)
        if raw.shape != self.mean.shape or not np.isfinite(raw).all():
            raise ValueError("Observation shape/finiteness does not match normalizer")
        value = (raw - self.mean) / self.scale if self.enabled else raw
        return np.clip(value, -10, 10).astype(np.float32)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
            "enabled": self.enabled,
            "fit_end": self.fit_end,
            "method": "training-only per-asset log-return standardization; weights identity",
            "clip": 10,
            "frozen_at_inference": True,
            "reward_normalization": False,
        }

    @classmethod
    def load(cls, path: Path) -> Normalizer:
        data = json.loads(path.read_text(encoding="utf-8"))
        mean, scale = np.asarray(data["mean"]), np.asarray(data["scale"])
        if (
            mean.ndim != 1
            or mean.shape != scale.shape
            or not np.isfinite(mean).all()
            or (
                not np.isfinite(scale).all() or (scale <= 0).any() or data["fit_end"] > "2021-12-31"
            )
        ):
            raise ValueError("Invalid train-only normalizer")
        return cls(mean, scale, bool(data["enabled"]), data["fit_end"])


class NormalizedEnv(gym.ObservationWrapper):
    def __init__(self, env: PortfolioEnv, normalizer: Normalizer):
        super().__init__(env)
        self.normalizer = normalizer
        self.observation_space = gym.spaces.Box(
            -10, 10, shape=env.observation_space.shape, dtype=np.float32
        )

    def observation(self, observation: NDArray[Any]) -> NDArray[np.float32]:
        return self.normalizer.transform(observation)


def verify_artifact(directory: Path) -> dict[str, Any]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    required = {"model.zip", "normalizer.json"}
    if manifest["configuration"]["algorithm"] == "ddpg":
        required.add("replay_buffer.pkl")
    if set(manifest["files"]) != required:
        raise ValueError("Incomplete model artifact")
    for name, checksum in manifest["files"].items():
        path = (directory / name).resolve()
        if path.parent != directory.resolve() or sha256(path) != checksum:
            raise ValueError("Checkpoint integrity mismatch")
    if manifest["training_end"] > "2021-12-31":
        raise ValueError("Model fitted on forbidden dates")
    return manifest


def prepare_training(
    panel: PricePanel,
    config: TrainingConfig,
    output_dir: Path,
    resume_from: Path | None = None,
) -> tuple[gym.Env, Normalizer]:
    if panel.dates[-1] > config.training_end or panel.dates[0] < "2015-01-01":
        raise ValueError("Training panel extends outside the permitted chronological window")
    if panel.metadata.get("id") != config.dataset_id:
        raise ValueError("Dataset mismatch")
    random.seed(config.seed)
    np.random.seed(config.seed)
    torch.set_num_threads(1)
    torch.manual_seed(config.seed)
    torch.use_deterministic_algorithms(True)
    output_dir.mkdir(parents=True, exist_ok=True)
    if resume_from is not None:
        manifest = verify_artifact(resume_from)
        if manifest["compatibility_signature"] != compatibility_signature(config):
            raise ValueError("Resume requires identical dataset, learning and economic settings")
        if manifest["dataset_sha256"] != panel.metadata.get("sha256"):
            raise ValueError("Resume dataset hash mismatch")
        normalizer = Normalizer.load(resume_from / "normalizer.json")
    else:
        logs = np.diff(np.log(panel.prices), axis=0)
        mean, scale = logs.mean(axis=0), np.maximum(logs.std(axis=0, ddof=1), 1e-6)
        normalizer = Normalizer(
            np.concatenate([np.tile(mean, config.lookback), np.zeros(panel.n_assets)]),
            np.concatenate([np.tile(scale, config.lookback), np.ones(panel.n_assets)]),
            config.normalize_observations,
            panel.dates[-1],
        )
    env = PortfolioEnv(
        panel,
        lookback=config.lookback,
        initial_capital=config.initial_capital,
        transaction_cost_bps=config.transaction_cost_bps,
        reward_mode=config.reward_mode,
        risk_penalty=config.risk_penalty,
    )
    env.reset(seed=config.seed)
    return NormalizedEnv(env, normalizer), normalizer


def fit_and_save(
    model: BaseAlgorithm,
    panel: PricePanel,
    config: TrainingConfig,
    output_dir: Path,
    normalizer: Normalizer,
    *,
    progress: Progress | None = None,
    cancelled: Cancelled | None = None,
    save_replay: bool = False,
    resume: bool = False,
) -> dict[str, Any]:
    started = time.monotonic()
    starting_steps = int(model.num_timesteps)
    telemetry: list[dict[str, Any]] = []
    checkpoints: list[dict[str, Any]] = []
    was_cancelled = False
    process = psutil.Process()

    def metrics() -> dict[str, float]:
        values = {}
        for key, value in model.logger.name_to_value.items():
            if key.startswith("train/") and isinstance(value, (float, int, np.number)):
                if math.isfinite(float(value)):
                    values[key] = float(value)
        return values

    def report() -> dict[str, Any]:
        item = {
            "timesteps": int(model.num_timesteps),
            "requested_timesteps": config.total_timesteps,
            "progress": min((model.num_timesteps - starting_steps) / config.total_timesteps, 1),
            "elapsed_seconds": time.monotonic() - started,
            "rss_mb": process.memory_info().rss / 2**20,
            "learning_metrics": metrics(),
        }
        telemetry.append(item)
        if progress:
            progress(item)
        return item

    def save(directory: Path, status: str) -> dict[str, Any]:
        directory.mkdir(parents=True, exist_ok=True)
        model.save(directory / "model.zip")
        write_json(directory / "normalizer.json", normalizer.as_dict())
        files = {
            "model.zip": sha256(directory / "model.zip"),
            "normalizer.json": sha256(directory / "normalizer.json"),
        }
        if save_replay:
            if not isinstance(model, OffPolicyAlgorithm):
                raise ValueError("Replay checkpoints require an off-policy algorithm")
            model.save_replay_buffer(directory / "replay_buffer.pkl")
            files["replay_buffer.pkl"] = sha256(directory / "replay_buffer.pkl")
        manifest = {
            "schema_version": 1,
            "status": status,
            "mode": "PAPER",
            "configuration": config.model_dump(),
            "configuration_sha256": hashlib.sha256(
                json.dumps(config.model_dump(), sort_keys=True).encode()
            ).hexdigest(),
            "compatibility_signature": compatibility_signature(config),
            "dataset_sha256": panel.metadata.get("sha256"),
            "data_mode": panel.metadata.get("kind"),
            "training_start": panel.dates[0],
            "training_end": panel.dates[-1],
            "actual_timesteps": int(model.num_timesteps),
            "starting_timesteps": starting_steps,
            "duration_seconds": time.monotonic() - started,
            "learning_metrics": metrics(),
            "telemetry": telemetry[-500:],
            "checkpoints": checkpoints.copy(),
            "files": files,
            "dependencies": {
                name: version(name) for name in ("numpy", "torch", "gymnasium", "stable-baselines3")
            },
            "device": "cpu",
            "torch_threads": 1,
            "resume_semantics": (
                "optimizer/model/normalizer/replay restored; episode/RNG reset; "
                "not bitwise continuation"
            ),
            "resumed": resume,
            "normalization_fit_end": normalizer.fit_end,
            "validation_used_for_training": False,
            "holdout_2024_used": False,
        }
        write_json(directory / "manifest.json", manifest)
        return manifest

    class Observer(BaseCallback):
        def _on_step(self) -> bool:
            nonlocal was_cancelled
            if cancelled is not None and cancelled():
                was_cancelled = True
                return False
            if time.monotonic() - started > config.max_seconds:
                raise TimeoutError("Training exceeded configured wall-time budget")
            if self.num_timesteps % 32 == 0:
                item = report()
                if item["rss_mb"] > config.max_memory_mb:
                    raise MemoryError("Training exceeded configured memory budget")
            if self.num_timesteps % config.checkpoint_frequency == 0:
                relative = f"checkpoints/step-{self.num_timesteps:08d}"
                save(output_dir / relative, "checkpoint")
                checkpoints.append({"path": relative, "timesteps": self.num_timesteps})
            return True

    model.learn(
        total_timesteps=config.total_timesteps,
        callback=Observer(),
        reset_num_timesteps=not resume,
        progress_bar=False,
    )
    report()
    return save(output_dir, "cancelled" if was_cancelled else "completed")


@dataclass
class PolicyBundle:
    model: BaseAlgorithm
    normalizer: Normalizer
    manifest: dict[str, Any]

    def predict(self, observation: NDArray[Any], deterministic: bool = True) -> NDArray[np.float32]:
        action, _ = self.model.predict(
            self.normalizer.transform(observation), deterministic=deterministic
        )
        return np.asarray(action, dtype=np.float32)


def load_bundle(artifact_dir: Path) -> PolicyBundle:
    from stable_baselines3 import DDPG, PPO

    manifest = verify_artifact(artifact_dir)
    torch.set_num_threads(1)
    algorithm = PPO if manifest["configuration"]["algorithm"] == "ppo" else DDPG
    model = algorithm.load(artifact_dir / "model.zip", device="cpu")
    return PolicyBundle(model, Normalizer.load(artifact_dir / "normalizer.json"), manifest)
