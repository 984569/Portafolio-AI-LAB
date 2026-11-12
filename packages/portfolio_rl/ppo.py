"""Configurable Stable-Baselines3 PPO on the existing paper-only portfolio MDP.

Initial hyperparameters are controlled research assumptions, not claimed optima.
PPO's Gaussian Box actions are clipped by SB3 and the unchanged environment
projects them onto the long-only simplex. Observation normalization, financial
accounting, resource limits and artifact integrity belong to the shared pipeline.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from portfolio_core import PricePanel
from stable_baselines3 import PPO

from .common import fit_and_save, prepare_training
from .config import TrainingConfig


def train_ppo(
    panel: PricePanel,
    config: TrainingConfig,
    output_dir: Path,
    *,
    progress: Callable[[dict[str, Any]], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
    resume_from: Path | None = None,
) -> dict[str, Any]:
    """Train or functionally resume PPO and persist a verified checkpoint bundle.

    The shared preparation rejects training after2021 and mismatched dataset or
    resume settings before model loading. Resume restores policy/optimizer and
    frozen normalization, but resets the episode; uninterrupted bitwise resume
    is intentionally not promised. Budgets are validated as complete rollouts.
    """
    if config.algorithm != "ppo":
        raise ValueError("train_ppo requires algorithm='ppo'")
    environment, normalizer = prepare_training(panel, config, output_dir, resume_from=resume_from)
    try:
        if resume_from is not None:
            model = PPO.load(resume_from / "model.zip", environment, device="cpu", force_reset=True)
        else:
            parameters = config.ppo
            model = PPO(
                "MlpPolicy",
                environment,
                learning_rate=parameters.learning_rate,
                n_steps=parameters.n_steps,
                batch_size=parameters.batch_size,
                n_epochs=parameters.n_epochs,
                gamma=parameters.gamma,
                gae_lambda=parameters.gae_lambda,
                clip_range=parameters.clip_range,
                ent_coef=parameters.ent_coef,
                vf_coef=parameters.vf_coef,
                max_grad_norm=parameters.max_grad_norm,
                normalize_advantage=True,
                policy_kwargs={
                    "net_arch": {"pi": list(config.net_arch), "vf": list(config.net_arch)}
                },
                seed=config.seed,
                device="cpu",
                verbose=0,
            )
        return fit_and_save(
            model,
            panel,
            config,
            output_dir,
            normalizer,
            progress=progress,
            cancelled=cancelled,
            save_replay=False,
            resume=resume_from is not None,
        )
    finally:
        environment.close()
