"""Repeat the two historical Stage 3 smoke trainings on the verified local snapshot."""

from __future__ import annotations

import hashlib
import json
import sys
from bisect import bisect_right
from collections.abc import Mapping
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING, Any
from uuid import UUID

import numpy as np
import torch
from numpy.typing import NDArray

if TYPE_CHECKING:
    from portfolio_core import PricePanel
    from portfolio_rl.common import PolicyBundle
    from portfolio_rl.config import TrainingConfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

RUNTIME = ROOT / ".runtime"
SMOKE_REPORT = RUNTIME / "stage3/smoke-report.json"
EVIDENCE = ROOT / "docs/evidence/stage3/reproducibility.json"
VALIDATION_START = "2022-01-01"
VALIDATION_END = "2023-12-31"


def through(panel: PricePanel, end: str) -> PricePanel:
    stop = bisect_right(panel.dates, end)
    return type(panel)(panel.dates[:stop], panel.assets, panel.prices[:stop], panel.metadata)


def tensor_digest(tensors: Mapping[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(tensors.items()):
        values = tensor.detach().cpu().numpy()
        digest.update(json.dumps([name, values.dtype.str, list(values.shape)]).encode())
        digest.update(values.tobytes())
    return digest.hexdigest()


def validation_replay(
    panel: PricePanel, bundle: PolicyBundle, config: TrainingConfig
) -> tuple[dict[str, Any], NDArray[np.float32]]:
    from portfolio_evaluation import evaluate_policy

    actions: list[NDArray[np.float32]] = []

    def predict(observation: NDArray[np.float32]) -> NDArray[np.float32]:
        action = bundle.predict(observation, deterministic=True)
        actions.append(action.copy())
        return action

    result = evaluate_policy(
        panel,
        predict,
        config.model_dump() | {"strategy": config.algorithm},
        train_end=config.training_end,
        eval_start=VALIDATION_START,
        eval_end=VALIDATION_END,
    )
    return result, np.stack(actions)


def reproduce(
    panel: PricePanel, job: dict[str, Any], smoke: dict[str, Any], output: Path
) -> dict[str, Any]:
    from portfolio_rl.common import load_bundle
    from portfolio_rl.config import TrainingConfig
    from portfolio_rl.ddpg import train_ddpg
    from portfolio_rl.ppo import train_ppo

    config = TrainingConfig.model_validate(job["configuration"])
    algorithm = config.algorithm
    if config.total_timesteps != 256:
        raise ValueError(f"Expected the 256-step smoke budget for {algorithm}")
    job_id = str(UUID(job["job_id"]))
    reference = load_bundle(RUNTIME / "training" / job_id)
    if (
        reference.manifest["status"] != "completed"
        or reference.manifest["configuration"] != config.model_dump()
        or reference.manifest["files"] != job["files"]
        or reference.manifest["dataset_sha256"] != smoke["dataset_sha256"]
        or reference.manifest["actual_timesteps"] != job["actual_timesteps"]
        or reference.manifest["holdout_2024_used"] is not False
        or reference.manifest["resumed"] is not False
        or config.dataset_id != smoke["dataset_id"]
    ):
        raise ValueError(f"Smoke report and verified checkpoint disagree for {algorithm}")

    trainer = train_ppo if algorithm == "ppo" else train_ddpg
    # Match the worker's indexed copy so NumPy reduces C-contiguous price rows.
    indices = list(range(bisect_right(panel.dates, config.training_end)))
    training = type(panel)(
        tuple(panel.dates[i] for i in indices), panel.assets, panel.prices[indices], panel.metadata
    )
    trainer(training, config, output)
    repeat = load_bundle(output)
    original_tensors = reference.model.policy.state_dict()
    repeated_tensors = repeat.model.policy.state_dict()
    original_digest = tensor_digest(original_tensors)
    repeated_digest = tensor_digest(repeated_tensors)
    original_eval, original_actions = validation_replay(panel, reference, config)
    repeated_eval, repeated_actions = validation_replay(panel, repeat, config)
    checks = {
        "completed_requested_steps": (
            repeat.manifest["status"] == "completed"
            and repeat.manifest["actual_timesteps"]
            == job["actual_timesteps"]
            == config.total_timesteps
        ),
        "same_training_protocol": all(
            reference.manifest[key] == repeat.manifest[key]
            for key in (
                "configuration_sha256",
                "dataset_sha256",
                "data_mode",
                "dependencies",
                "device",
                "torch_threads",
                "training_start",
                "training_end",
                "normalization_fit_end",
            )
        ),
        "normalizer_exact": (
            reference.manifest["files"]["normalizer.json"]
            == repeat.manifest["files"]["normalizer.json"]
        ),
        "policy_tensors_exact": original_digest == repeated_digest,
        "validation_actions_exact": (
            original_actions.dtype == repeated_actions.dtype
            and np.array_equal(original_actions, repeated_actions)
        ),
        "validation_equity_exact": original_eval["equity"] == repeated_eval["equity"],
        "validation_allocations_exact": original_eval["allocations"]
        == repeated_eval["allocations"],
        "validation_metrics_match_smoke": (
            original_eval["metrics"] == repeated_eval["metrics"] == smoke["validation"][algorithm]
        ),
        "holdout_excluded": (
            repeat.manifest["holdout_2024_used"] is False
            and original_eval["manifest"]["evaluation"]["holdout_evaluated"] is False
            and repeated_eval["manifest"]["evaluation"]["holdout_evaluated"] is False
        ),
    }
    return {
        "reference_job_id": job_id,
        "repeat_artifact": output.relative_to(ROOT).as_posix(),
        "configuration_sha256": repeat.manifest["configuration_sha256"],
        "seed": config.seed,
        "timesteps": repeat.manifest["actual_timesteps"],
        "training_dates": [training.dates[0], training.dates[-1]],
        "training_rows": len(training),
        "policy_tensor_count": len(repeated_tensors),
        "policy_tensor_sha256": {"reference": original_digest, "repeat": repeated_digest},
        "validation": {
            **repeated_eval["manifest"]["evaluation"],
            "action_vectors": len(repeated_actions),
            "equity_points": len(repeated_eval["equity"]),
            "metrics": repeated_eval["metrics"],
        },
        "dependencies": repeat.manifest["dependencies"],
        "device": repeat.manifest["device"],
        "torch_threads": repeat.manifest["torch_threads"],
        "checks": checks,
    }


def main() -> None:
    from market_data import load_snapshot
    from portfolio_rl.common import write_json

    reference_bytes = SMOKE_REPORT.read_bytes()
    smoke = json.loads(reference_bytes)
    jobs = {job["configuration"]["algorithm"]: job for job in smoke["jobs"]}
    if (
        smoke["mode"] != "smoke"
        or smoke["status"] != "completed"
        or smoke["holdout_2024_evaluated"] is not False
        or len(smoke["jobs"]) != 2
        or set(jobs) != {"ppo", "ddpg"}
    ):
        raise ValueError("Expected a completed smoke report with one PPO and one DDPG job")

    panel = through(load_snapshot(RUNTIME / "datasets", smoke["dataset_id"]), VALIDATION_END)
    if (
        panel.metadata["kind"] != "HISTORICAL"
        or panel.metadata["sha256"] != smoke["dataset_sha256"]
    ):
        raise ValueError("Smoke reproducibility requires the recorded historical snapshot")

    runs_dir = RUNTIME / "stage3/reproducibility"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run = Path(mkdtemp(dir=runs_dir, prefix="run-"))
    results = {
        algorithm: reproduce(panel, job, smoke, run / algorithm) for algorithm, job in jobs.items()
    }
    success = all(all(result["checks"].values()) for result in results.values())
    write_json(
        EVIDENCE,
        {
            "schema_version": 1,
            "status": "passed" if success else "failed",
            "reference_report": SMOKE_REPORT.relative_to(ROOT).as_posix(),
            "reference_report_sha256": hashlib.sha256(reference_bytes).hexdigest(),
            "data_mode": panel.metadata["kind"],
            "dataset_id": smoke["dataset_id"],
            "dataset_sha256": smoke["dataset_sha256"],
            "holdout_2024_evaluated": False,
            "runs": results,
        },
    )
    print(EVIDENCE.relative_to(ROOT).as_posix())
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
