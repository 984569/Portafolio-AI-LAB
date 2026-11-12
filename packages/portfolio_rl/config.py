"""Versioned, bounded training configuration shared by CLI, jobs and algorithms."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Width = Annotated[int, Field(strict=True, ge=8, le=256)]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_default=True)


class PPOSettings(Settings):
    learning_rate: float = Field(default=3e-4, gt=0, le=0.01, strict=True)
    n_steps: int = Field(default=256, ge=16, le=2048, strict=True)
    batch_size: int = Field(default=64, ge=8, le=512, strict=True)
    n_epochs: int = Field(default=5, ge=1, le=20, strict=True)
    gamma: float = Field(default=0.99, gt=0, le=1, strict=True)
    gae_lambda: float = Field(default=0.95, ge=0, le=1, strict=True)
    clip_range: float = Field(default=0.2, gt=0, le=1, strict=True)
    ent_coef: float = Field(default=0, ge=0, le=1, strict=True)
    vf_coef: float = Field(default=0.5, ge=0, le=2, strict=True)
    max_grad_norm: float = Field(default=0.5, gt=0, le=10, strict=True)


class DDPGSettings(Settings):
    learning_rate: float = Field(default=1e-3, gt=0, le=0.01, strict=True)
    buffer_size: int = Field(default=20000, ge=128, le=100000, strict=True)
    batch_size: int = Field(default=64, ge=8, le=256, strict=True)
    gamma: float = Field(default=0.99, gt=0, le=1, strict=True)
    tau: float = Field(default=0.005, gt=0, le=1, strict=True)
    train_freq: int = Field(default=1, ge=1, le=8, strict=True)
    gradient_steps: int = Field(default=1, ge=1, le=4, strict=True)
    learning_starts: int = Field(default=256, ge=0, le=10000, strict=True)
    noise_sigma: float = Field(default=0.1, ge=0, le=1, strict=True)


class TrainingConfig(Settings):
    name: str = Field(default="Portfolio RL research", min_length=1, max_length=80)
    algorithm: Literal["ppo", "ddpg"]
    dataset_id: str = Field(min_length=1, max_length=100)
    seed: int = Field(default=42, ge=0, le=2147483647, strict=True)
    total_timesteps: int = Field(default=1024, ge=32, le=262144, strict=True)
    lookback: int = Field(default=60, ge=2, le=120, strict=True)
    initial_capital: float = Field(default=10000, gt=0, le=1e9, strict=True)
    transaction_cost_bps: float = Field(default=10, ge=0, le=100, strict=True)
    risk_free_rate: float = Field(default=0, ge=-0.99, le=1, strict=True)
    reward_mode: Literal["log_return", "simple_return"] = "log_return"
    risk_penalty: float = Field(default=0, ge=0, le=1000, strict=True)
    normalize_observations: bool = True
    net_arch: list[Width] = Field(default_factory=lambda: [64, 64], min_length=1, max_length=3)
    checkpoint_frequency: int = Field(default=1024, ge=32, le=100000, strict=True)
    max_seconds: int = Field(default=600, ge=5, le=7200, strict=True)
    max_memory_mb: int = Field(default=2048, ge=512, le=4096, strict=True)
    training_end: str = "2021-12-31"
    ppo: PPOSettings = Field(default_factory=PPOSettings)
    ddpg: DDPGSettings = Field(default_factory=DDPGSettings)

    @field_validator("name")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name must contain non-whitespace characters")
        return value

    @field_validator("training_end")
    @classmethod
    def chronological_end(cls, value: str) -> str:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or not "2015-01-01" <= value <= "2021-12-31":
            raise ValueError("Training must end within2015–2021; validation/2024 cannot be fitted")
        return value

    @model_validator(mode="after")
    def resource_and_algorithm_limits(self) -> "TrainingConfig":
        if self.total_timesteps / self.checkpoint_frequency > 16:
            raise ValueError("At most16 intermediate checkpoints are allowed per job")
        if self.algorithm == "ppo" and (
            self.total_timesteps % self.ppo.n_steps or self.ppo.n_steps % self.ppo.batch_size
        ):
            raise ValueError(
                "PPO timesteps must divide into rollouts, and batch must divide rollout"
            )
        if self.algorithm == "ddpg":
            if self.ddpg.batch_size > self.ddpg.buffer_size:
                raise ValueError("Replay buffer must fit a batch")
            if self.total_timesteps <= self.ddpg.learning_starts:
                raise ValueError("DDPG budget must exceed learning_starts to perform updates")
            replay_mb = self.ddpg.buffer_size * (self.lookback + 1) * 10 * 8 / 2**20
            if replay_mb + 384 > self.max_memory_mb:
                raise ValueError("Estimated replay plus process overhead exceeds memory budget")
            if replay_mb * (self.total_timesteps // self.checkpoint_frequency + 2) > 4096:
                raise ValueError("Estimated replay checkpoints exceed4GiB disk budget")
        return self
