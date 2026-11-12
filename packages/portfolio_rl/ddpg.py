"""Stable-Baselines3 DDPG adapter for the shared, causally bounded trainer.

The actor and critic consume the same static train-only observation transform as
PPO. Exploration is Gaussian noise in the raw Box action space; PortfolioEnv
projects that raw action onto its long-only simplex. DDPG learns a Q function
over raw actions and does not differentiate through the environment projection.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
from portfolio_core import PricePanel
from stable_baselines3 import DDPG
from stable_baselines3.common.noise import NormalActionNoise

from .common import fit_and_save, prepare_training
from .config import TrainingConfig


def train_ddpg(
    panel: PricePanel,
    config: TrainingConfig,
    output_dir: Path,
    *,
    progress: Callable[[dict[str, Any]], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    resume_from: Path | None = None,
) -> dict[str, Any]:
    """Fit a CPU DDPG model and persist model, normalizer and replay buffer.

    Defaults are documented initial research settings, not optimal parameters.
    Resume restores model/optimizers and the separately saved replay buffer,
    but restarts the environment episode and RNG stream. It is intentionally
    not claimed equivalent to uninterrupted training.

    ``prepare_training`` verifies dataset/date boundaries and, when resuming,
    artifact hashes and the complete learning/economic compatibility signature
    before any trusted local model or replay pickle is loaded.
    """
    if config.algorithm != "ddpg":
        raise ValueError("train_ddpg requires algorithm='ddpg'")
    environment, normalizer = prepare_training(panel, config, output_dir, resume_from=resume_from)
    try:
        if resume_from is not None:
            model = DDPG.load(
                resume_from / "model.zip", env=environment, device="cpu", force_reset=True
            )
            model.load_replay_buffer(resume_from / "replay_buffer.pkl", truncate_last_traj=True)
        else:
            action_shape = environment.action_space.shape
            if action_shape is None or len(action_shape) != 1:
                raise ValueError("DDPG requires a one-dimensional continuous action vector")
            actions = int(action_shape[0])
            settings = config.ddpg
            noise = NormalActionNoise(
                mean=np.zeros(actions, dtype=np.float32),
                sigma=np.full(actions, settings.noise_sigma, dtype=np.float32),
                dtype=np.float32,
            )
            model = DDPG(
                "MlpPolicy",
                environment,
                learning_rate=settings.learning_rate,
                buffer_size=settings.buffer_size,
                learning_starts=settings.learning_starts,
                batch_size=settings.batch_size,
                gamma=settings.gamma,
                tau=settings.tau,
                train_freq=settings.train_freq,
                gradient_steps=settings.gradient_steps,
                action_noise=noise,
                policy_kwargs={
                    "net_arch": {
                        "pi": list(config.net_arch),
                        "qf": list(config.net_arch),
                    }
                },
                verbose=0,
                seed=config.seed,
                device="cpu",
            )
        return fit_and_save(
            model,
            panel,
            config,
            output_dir,
            normalizer,
            progress=progress,
            cancelled=cancelled,
            save_replay=True,
            resume=resume_from is not None,
        )
    finally:
        environment.close()
