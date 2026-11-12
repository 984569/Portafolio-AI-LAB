"""Execute the bounded predeclared CPU study using the same durable training scheduler."""

import argparse
import hashlib
import json
import socket
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "apps/api")]


def main() -> None:
    from market_data import list_snapshots, load_snapshot
    from portfolio_api.models import Dataset, TrainingRequest
    from portfolio_api.store import Store
    from portfolio_api.training_jobs import TrainingManager
    from portfolio_evaluation import (
        WALK_FORWARD_FOLDS,
        evaluate_baseline_window,
        evaluate_policy,
        paired_block_bootstrap,
        seed_summary,
        select_candidate,
    )
    from portfolio_rl.common import load_bundle, write_json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke", "study"], default="smoke")
    parser.add_argument(
        "--continue-study",
        action="store_true",
        help="Reuse verified completed jobs from an interrupted study with the same protocol",
    )
    args = parser.parse_args()
    if args.continue_study and args.mode != "study":
        parser.error("--continue-study requires --mode study")
    try:
        with socket.create_connection(("127.0.0.1", 8000), timeout=0.2):
            raise RuntimeError(
                "Stop the API first; this CLI owns the same local scheduler/database."
            )
    except OSError:
        pass
    protocol_file = ROOT / "experiments/stage3-protocol.json"
    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    datasets = list_snapshots(ROOT / ".runtime/datasets")
    if not datasets:
        raise RuntimeError("Run the real historical pipeline first")
    dataset = Dataset.model_validate(datasets[-1])
    panel = load_snapshot(ROOT / ".runtime/datasets", dataset.id)
    output = ROOT / ".runtime/stage3"
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "protocol": protocol,
        "protocol_sha256": hashlib.sha256(protocol_file.read_bytes()).hexdigest(),
        "dataset_id": dataset.id,
        "dataset_sha256": dataset.sha256,
        "mode": args.mode,
        "jobs": [],
        "holdout_2024_evaluated": False,
    }
    report_path = output / f"{args.mode}-report.json"
    if args.continue_study:
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        for key in ("mode", "protocol_sha256", "dataset_id", "dataset_sha256"):
            if previous[key] != report[key]:
                raise ValueError(f"Previous study differs in {key}")
        if previous["holdout_2024_evaluated"] is not False:
            raise ValueError("Previous study violated the holdout lock")
        report = previous
    store = Store(ROOT / ".runtime/portfolio.sqlite3")
    store.initialize()
    manager = TrainingManager(store)
    manager.initialize()
    manager.thread.start()

    def run(config: dict[str, Any]) -> tuple[Any, Any]:
        request = TrainingRequest.model_validate(config)
        if args.continue_study:
            expected = request.model_dump(exclude={"resume_from_job_id"})
            for record in report["jobs"]:
                if record["configuration"] != expected:
                    continue
                current = manager.get(record["job_id"])
                if current is None or current.status != "completed":
                    raise RuntimeError("Recorded completed job is unavailable")
                if current.config.model_dump() != expected or current.manifest is None:
                    raise RuntimeError("Recorded job configuration does not match")
                bundle = load_bundle(manager.directory(current.id))
                if bundle.manifest["files"] != record["files"]:
                    raise RuntimeError("Recorded artifact hashes do not match")
                print(json.dumps({"event": "reused", "id": current.id}), flush=True)
                return current, bundle
        job = manager.submit(request, dataset)
        print(
            json.dumps(
                {
                    "event": "submitted",
                    "id": job.id,
                    "name": config["name"],
                    "algorithm": config["algorithm"],
                    "steps": config["total_timesteps"],
                }
            ),
            flush=True,
        )
        while True:
            current = manager.get(job.id)
            assert current is not None
            if current.status in {"completed", "failed", "cancelled"}:
                break
            if not manager.thread.is_alive():
                raise RuntimeError("Training supervisor stopped")
            time.sleep(0.3)
        if current.status != "completed":
            raise RuntimeError(f"{current.id}: {current.status}: {current.error}")
        assert current.manifest is not None
        record = {
            "job_id": current.id,
            "configuration": current.config.model_dump(),
            "actual_timesteps": current.manifest["actual_timesteps"],
            "training_seconds": current.manifest["duration_seconds"],
            "resources": current.progress,
            "files": current.manifest["files"],
            "learning_metrics": current.manifest["learning_metrics"],
        }
        report["jobs"].append(record)
        write_json(report_path, report)
        print(
            json.dumps(
                {
                    "event": "completed",
                    "id": current.id,
                    "seconds": current.manifest["duration_seconds"],
                }
            ),
            flush=True,
        )
        return current, load_bundle(manager.directory(current.id))

    def base(algorithm: str, name: str, steps: int, seed: int) -> dict[str, Any]:
        return {
            key: protocol[key]
            for key in (
                "lookback",
                "initial_capital",
                "transaction_cost_bps",
                "risk_free_rate",
                "reward_mode",
                "risk_penalty",
                "normalize_observations",
            )
        } | {
            "name": name,
            "algorithm": algorithm,
            "dataset_id": dataset.id,
            "seed": seed,
            "total_timesteps": steps,
            "checkpoint_frequency": protocol["checkpoint_frequency"],
            "max_seconds": protocol["max_seconds_per_job"],
            "max_memory_mb": protocol["max_memory_mb"],
        }

    try:
        if args.mode == "smoke":
            for algorithm in ("ppo", "ddpg"):
                config = base(algorithm, f"Smoke historical {algorithm}", 256, 42)
                config.update(net_arch=[32, 32], checkpoint_frequency=256)
                if algorithm == "ppo":
                    config["ppo"] = {"n_steps": 64, "batch_size": 32, "n_epochs": 2}
                else:
                    config["ddpg"] = {"learning_starts": 32, "buffer_size": 1024, "batch_size": 32}
                job, bundle = run(config)
                result = evaluate_policy(
                    panel,
                    bundle.predict,
                    {**config, "strategy": algorithm},
                    train_end=job.manifest["training_end"],
                )
                report.setdefault("validation", {})[algorithm] = result["metrics"]
                write_json(report_path, report)
        else:
            smoke_file = output / "smoke-report.json"
            if not smoke_file.exists():
                raise RuntimeError("Run --mode smoke first to measure the complete pipeline")
            smoke = json.loads(smoke_file.read_text(encoding="utf-8"))
            estimate = sum(
                item["training_seconds"]
                / 256
                * protocol["initial_timesteps"][item["configuration"]["algorithm"]]
                * 4
                for item in smoke["jobs"]
            ) * len(protocol["final_seeds"])
            report["preflight"] = {
                "estimated_final_training_seconds_conservative": estimate,
                "walk_forward_models": 8,
                "final_models": 6,
                "estimated_artifact_disk_mb_upper": 2048,
                "cpu_threads_per_child": 1,
                "concurrent_children": 1,
            }
            import shutil

            if shutil.disk_usage(ROOT).free < 4 * 2**30:
                raise RuntimeError("At least4GiB free disk is required for this bounded study")
            write_json(report_path, report)
            report["selection"] = {}
            for algorithm in ("ppo", "ddpg"):
                rows = []
                for learning_rate in protocol["candidates"][algorithm]:
                    for fold in WALK_FORWARD_FOLDS:
                        config = base(
                            algorithm,
                            f"WF {algorithm} {learning_rate} {fold['fold_id']}",
                            protocol["walk_forward_timesteps"],
                            protocol["development_seed"],
                        )
                        config["training_end"] = fold["train_end"]
                        config["checkpoint_frequency"] = 2048
                        config[algorithm] = {"learning_rate": learning_rate}
                        if algorithm == "ddpg":
                            config[algorithm]["buffer_size"] = 4096
                        job, bundle = run(config)
                        result = evaluate_policy(
                            panel,
                            bundle.predict,
                            {**config, "strategy": algorithm},
                            train_end=job.manifest["training_end"],
                            eval_start=fold["eval_start"],
                            eval_end=fold["eval_end"],
                        )
                        rows.append(
                            {
                                "candidate_id": str(learning_rate),
                                "fold_id": fold["fold_id"],
                                "result": result,
                                "job_id": job.id,
                            }
                        )
                report["selection"][algorithm] = select_candidate(rows)
                report.setdefault("walk_forward", {})[algorithm] = rows
                write_json(report_path, report)
            report["validation"] = {}
            for algorithm in ("ppo", "ddpg"):
                selected = report["selection"][algorithm]["selected_candidate"]
                if selected is None:
                    raise RuntimeError("No valid walk-forward candidate; final selection blocked")
                results = []
                for seed in protocol["final_seeds"]:
                    config = base(
                        algorithm,
                        f"Initial {algorithm} seed{seed}",
                        protocol["initial_timesteps"][algorithm],
                        seed,
                    )
                    config[algorithm] = {"learning_rate": float(selected)}
                    job, bundle = run(config)
                    result = (
                        job.evaluation if job.evaluation is not None else manager.evaluate(job.id)
                    )
                    results.append(result)
                report["validation"][algorithm] = results
                report.setdefault("seed_summaries", {})[algorithm] = seed_summary(results)
                write_json(report_path, report)
            report["baselines"] = {}
            for strategy in ("equal_weight", "markowitz"):
                config = {
                    **base("ppo", f"Comparison {strategy}", 1024, 42),
                    "strategy": strategy,
                    "risk_aversion": 5,
                }
                report["baselines"][strategy] = evaluate_baseline_window(
                    panel, config, eval_start="2022-01-01", eval_end="2023-12-31"
                )
            report["paired_bootstrap"] = {
                algorithm: paired_block_bootstrap(
                    report["validation"][algorithm][1], report["baselines"]["equal_weight"], seed=42
                )
                for algorithm in ("ppo", "ddpg")
            }
        report["status"] = "completed"
        write_json(report_path, report)
        print(json.dumps({"status": "completed", "report": str(report_path)}), flush=True)
    finally:
        manager.close()


if __name__ == "__main__":
    main()
