"""Durable bounded scheduler supervising one CPU training subprocess at a time."""

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import psutil
from portfolio_rl.config import TrainingConfig

from .datasets import data_root, historical_panel
from .models import Dataset, ModelInfo, TrainingJob, TrainingRequest
from .store import QueueFullError, Store, timestamp

ROOT = Path(__file__).resolve().parents[3]


class TerminalTrainingError(Exception):
    """The job completed or failed before its cancellation could be applied."""


def sample_resources(root: psutil.Process) -> tuple[float, float]:
    """Include the real interpreter behind the Windows virtualenv launcher."""
    try:
        processes = [root, *root.children(recursive=True)]
    except psutil.Error:
        return 0.0, 0.0
    rss = cpu = 0.0
    for process in processes:
        try:
            rss += process.memory_info().rss / 2**20
            cpu += sum(process.cpu_times()[:2])
        except psutil.Error:
            continue
    return rss, cpu


def terminate_children(root: psutil.Process) -> None:
    try:
        children = root.children(recursive=True)
    except psutil.Error:
        return
    for child in reversed(children):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            continue


class TrainingManager:
    def __init__(self, store: Store):
        self.store = store
        configured = Path(os.getenv("TRAINING_ROOT", ".runtime/training"))
        self.root = configured if configured.is_absolute() else ROOT / configured
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, name="training-supervisor", daemon=True)

    def directory(self, job_id: str) -> Path:
        if re.fullmatch(r"[a-f0-9-]{36}", job_id) is None:
            raise ValueError("Invalid model/job identifier")
        path = (self.root / job_id).resolve()
        if path.parent != self.root.resolve():
            raise ValueError("Artifact path must stay inside training root")
        return path

    def initialize(self) -> None:
        with self.store.connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS training_jobs "
                "(id TEXT PRIMARY KEY,status TEXT NOT NULL,payload TEXT NOT NULL)"
            )
            rows = db.execute(
                "SELECT payload FROM training_jobs WHERE status IN ('pending','running')"
            ).fetchall()
            for (payload,) in rows:
                job = TrainingJob.model_validate_json(payload)
                job.status, job.finished_at = "failed", timestamp()
                job.error = (
                    "Training interrupted by API restart; resume explicitly from a checkpoint."
                )
                self.save(db, job)

    @staticmethod
    def save(db: Any, job: TrainingJob) -> None:
        db.execute(
            "UPDATE training_jobs SET status=?,payload=? WHERE id=?",
            (job.status, job.model_dump_json(), job.id),
        )

    def get(self, job_id: str) -> TrainingJob | None:
        with self.store.connection() as db:
            row = db.execute("SELECT payload FROM training_jobs WHERE id=?", (job_id,)).fetchone()
        return TrainingJob.model_validate_json(row[0]) if row else None

    def latest(self) -> list[TrainingJob]:
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT payload FROM training_jobs ORDER BY rowid DESC LIMIT 100"
            ).fetchall()
        return [TrainingJob.model_validate_json(row[0]) for row in rows]

    def submit(self, request: TrainingRequest, dataset: Dataset) -> TrainingJob:
        if self.stop.is_set() or not self.thread.is_alive():
            raise RuntimeError("Training supervisor is unavailable")
        config = TrainingConfig.model_validate(request.model_dump(exclude={"resume_from_job_id"}))
        if request.resume_from_job_id:
            from portfolio_rl.common import compatibility_signature, verify_artifact

            manifest = verify_artifact(self.resume_directory(request.resume_from_job_id))
            if manifest["compatibility_signature"] != compatibility_signature(config):
                raise ValueError("Resume configuration does not match checkpoint")
        job = TrainingJob(
            id=str(uuid4()),
            status="pending",
            created_at=timestamp(),
            config=config,
            dataset=dataset,
            resume_from_job_id=request.resume_from_job_id,
        )
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            count = db.execute(
                "SELECT count(*) FROM training_jobs WHERE status IN ('pending','running')"
            ).fetchone()[0]
            if count >= 4:
                raise QueueFullError
            db.execute(
                "INSERT INTO training_jobs VALUES(?,?,?)",
                (job.id, job.status, job.model_dump_json()),
            )
        return job

    def claim(self) -> TrainingJob | None:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload FROM training_jobs WHERE status='pending' ORDER BY rowid LIMIT 1"
            ).fetchone()
            if not row:
                return None
            job = TrainingJob.model_validate_json(row[0])
            job.status, job.started_at = "running", timestamp()
            self.save(db, job)
            return job

    def cancel(self, job_id: str) -> TrainingJob | None:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM training_jobs WHERE id=?", (job_id,)).fetchone()
            if row is None:
                return None
            job = TrainingJob.model_validate_json(row[0])
            if job.status in {"completed", "failed"}:
                raise TerminalTrainingError
            if job.status == "pending":
                job.status, job.finished_at = "cancelled", timestamp()
            if job.status in {"running", "cancelled"}:
                job.cancel_requested = True
                directory = self.directory(job.id)
                directory.mkdir(parents=True, exist_ok=True)
                (directory / "cancel.requested").touch()
            self.save(db, job)
            return job

    def run(self) -> None:
        while not self.stop.is_set():
            job = self.claim()
            if job is None:
                self.stop.wait(0.2)
                continue
            try:
                self.execute(job)
            except Exception:
                with self.store.connection() as db:
                    db.execute("BEGIN IMMEDIATE")
                    row = db.execute(
                        "SELECT payload FROM training_jobs WHERE id=?", (job.id,)
                    ).fetchone()
                    current = TrainingJob.model_validate_json(row[0])
                    current.status = "cancelled" if current.cancel_requested else "failed"
                    current.finished_at = timestamp()
                    current.error = (
                        None if current.cancel_requested else "Training process could not complete."
                    )
                    self.save(db, current)

    def resume_directory(self, job_id: str) -> Path:
        from portfolio_rl.common import verify_artifact

        previous = self.get(job_id)
        if previous is None or previous.status not in {"completed", "cancelled", "failed"}:
            raise ValueError("Resume requires a terminal job with a verified local checkpoint")
        directory = self.directory(job_id)
        candidates = [directory, *sorted((directory / "checkpoints").glob("step-*"), reverse=True)]
        for candidate in candidates:
            if candidate.resolve() != directory and directory not in candidate.resolve().parents:
                continue
            try:
                verify_artifact(candidate)
                return candidate
            except (OSError, ValueError, KeyError, TypeError):
                continue
        raise ValueError("No verified resumable checkpoint is available")

    def update_progress(self, job_id: str, progress: dict[str, Any]) -> None:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM training_jobs WHERE id=?", (job_id,)).fetchone()
            if row:
                current = TrainingJob.model_validate_json(row[0])
                current.progress = progress
                self.save(db, current)

    def execute(self, job: TrainingJob) -> None:
        directory = self.directory(job.id)
        directory.mkdir(parents=True, exist_ok=True)
        request = {
            "config": job.config.model_dump(),
            "data_root": str(data_root()),
            "output_dir": str(directory),
            "resume_from": str(self.resume_directory(job.resume_from_job_id))
            if job.resume_from_job_id
            else None,
        }
        (directory / "request.json").write_text(json.dumps(request), encoding="utf-8")
        started, peak, cpu_peak = time.monotonic(), 0.0, 0.0
        error: str | None = None
        cancel_started: float | None = None
        with (directory / "process.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "scripts/train_job.py"),
                    "--request",
                    str(directory / "request.json"),
                ],
                cwd=ROOT,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                resource = psutil.Process(process.pid)
                while process.poll() is None:
                    if self.stop.is_set():
                        (directory / "cancel.requested").touch()
                    cancelled = (directory / "cancel.requested").exists()
                    if cancelled and cancel_started is None:
                        cancel_started = time.monotonic()
                    rss, cpu_seconds = sample_resources(resource)
                    peak = max(peak, rss)
                    cpu_peak = max(cpu_peak, cpu_seconds)
                    if (
                        rss > job.config.max_memory_mb
                        or time.monotonic() - started > job.config.max_seconds + 30
                    ):
                        error = "Training exceeded the configured resource budget."
                        terminate_children(resource)
                        process.terminate()
                        break
                    if cancel_started and time.monotonic() - cancel_started > 15:
                        terminate_children(resource)
                        process.terminate()
                        break
                    try:
                        progress = json.loads(
                            (directory / "progress.json").read_text(encoding="utf-8")
                        )
                    except (OSError, ValueError):
                        progress = {}
                    progress.update(
                        peak_rss_mb=peak,
                        elapsed_seconds=time.monotonic() - started,
                        cpu_seconds=cpu_peak,
                    )
                    self.update_progress(job.id, progress)
                    time.sleep(0.2)
                process.wait(timeout=10)
            finally:
                if process.poll() is None:
                    terminate_children(psutil.Process(process.pid))
                    process.kill()
                    process.wait(timeout=10)
        current = self.get(job.id) or job
        current.finished_at = timestamp()
        current.progress.update(peak_rss_mb=peak, elapsed_seconds=time.monotonic() - started)
        if error:
            current.status, current.error = "failed", error
        elif current.cancel_requested or self.stop.is_set():
            current.status = "cancelled"
        elif process.returncode == 0:
            try:
                from portfolio_rl.common import verify_artifact

                manifest = verify_artifact(directory)
                current.status = manifest["status"]
                current.manifest = manifest
            except Exception:
                current.status, current.error = (
                    "failed",
                    "Training artifact failed integrity validation.",
                )
        else:
            current.status, current.error = (
                "failed",
                "Training process failed. Inspect the local process log.",
            )
        if current.status == "cancelled":
            try:
                from portfolio_rl.common import verify_artifact

                current.manifest = verify_artifact(directory)
            except Exception:
                current.manifest = None
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM training_jobs WHERE id=?", (job.id,)).fetchone()
            latest = TrainingJob.model_validate_json(row[0])
            if latest.cancel_requested or (directory / "cancel.requested").exists():
                current.cancel_requested, current.status = True, "cancelled"
                current.error = None
            self.save(db, current)

    def close(self) -> None:
        self.stop.set()
        self.thread.join()

    def model(self, model_id: str) -> ModelInfo:
        job = self.get(model_id)
        if job is None or job.status != "completed" or job.manifest is None:
            raise ValueError("A completed trained model is required")
        from portfolio_rl.common import verify_artifact

        manifest = verify_artifact(self.directory(model_id))
        return ModelInfo(
            id=job.id,
            algorithm=job.config.algorithm,
            dataset_id=job.config.dataset_id,
            seed=job.config.seed,
            timesteps=manifest["actual_timesteps"],
            training_end=manifest["training_end"],
            lookback=job.config.lookback,
            initial_capital=job.config.initial_capital,
            transaction_cost_bps=job.config.transaction_cost_bps,
            risk_free_rate=job.config.risk_free_rate,
            validation_metrics=job.evaluation.get("metrics") if job.evaluation else None,
        )

    def evaluate(self, model_id: str) -> dict[str, Any]:
        self.model(model_id)
        job = self.get(model_id)
        assert job is not None
        from portfolio_evaluation import evaluate_policy
        from portfolio_rl.common import load_bundle

        bundle = load_bundle(self.directory(model_id))
        panel = historical_panel(job.config.dataset_id)
        config = job.config.model_dump()
        config["strategy"] = job.config.algorithm
        result = evaluate_policy(
            panel, bundle.predict, config, train_end=bundle.manifest["training_end"]
        )
        job.evaluation = result
        with self.store.connection() as db:
            self.save(db, job)
        return result

    def validate_replay(self, model_id: str | None, config: dict[str, Any]) -> None:
        if model_id is None:
            raise ValueError("A trained model is required")
        self.model(model_id)
        job = self.get(model_id)
        assert job is not None
        if job.config.algorithm != config["strategy"]:
            raise ValueError("Algorithm/model mismatch")
        for key in (
            "dataset_id",
            "lookback",
            "initial_capital",
            "transaction_cost_bps",
            "risk_free_rate",
        ):
            if getattr(job.config, key) != config[key]:
                raise ValueError("Replay must preserve the trained economic assumptions")

    def replay(self, model_id: str, config: dict[str, Any]) -> dict[str, Any]:
        self.validate_replay(model_id, config)
        from portfolio_evaluation import evaluate_policy
        from portfolio_rl.common import load_bundle

        job = self.get(model_id)
        assert job is not None
        bundle = load_bundle(self.directory(model_id))
        effective = {**job.config.model_dump(), **config}
        result = evaluate_policy(
            historical_panel(job.config.dataset_id),
            bundle.predict,
            effective,
            train_end=bundle.manifest["training_end"],
        )
        result["manifest"]["model_id"] = model_id
        result["manifest"]["model_files"] = bundle.manifest["files"]
        return result

    def comparison(self, model_id: str) -> dict[str, Any]:
        self.model(model_id)
        reference = self.get(model_id)
        assert reference is not None
        if reference.evaluation is None:
            self.evaluate(model_id)
        from portfolio_evaluation import evaluate_baseline_window

        fields = (
            "dataset_id",
            "lookback",
            "initial_capital",
            "transaction_cost_bps",
            "risk_free_rate",
        )
        items = []
        for job in self.latest():
            if job.status != "completed" or job.evaluation is None:
                continue
            if any(getattr(job.config, key) != getattr(reference.config, key) for key in fields):
                continue
            items.append(
                {
                    "algorithm": job.config.algorithm,
                    "model_id": job.id,
                    "seed": job.config.seed,
                    "timesteps": job.manifest["actual_timesteps"] if job.manifest else None,
                    "metrics": job.evaluation["metrics"],
                    "research_metrics": job.evaluation["manifest"]["research_metrics"],
                }
            )
        panel = historical_panel(reference.config.dataset_id)
        for algorithm in ("markowitz", "equal_weight"):
            config = {**reference.config.model_dump(), "strategy": algorithm, "risk_aversion": 5}
            result = evaluate_baseline_window(
                panel, config, eval_start="2022-01-01", eval_end="2023-12-31"
            )
            items.append(
                {
                    "algorithm": algorithm,
                    "model_id": None,
                    "seed": None,
                    "timesteps": None,
                    "metrics": result["metrics"],
                    "research_metrics": result["manifest"]["research_metrics"],
                }
            )
        return {
            "items": items,
            "holdout_2024_evaluated": False,
            "methodology": "All evaluated matching models shown; no best-seed selection. "
            "Same2022–2023 dates, assets, capital and fees. Learning budgets shown per model.",
        }
