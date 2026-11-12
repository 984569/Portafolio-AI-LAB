"""FastAPI entry point; run one process, bound to loopback."""

import os
import sqlite3
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from agent_desk.contracts import Provider
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from market_data import DataPipelineError
from portfolio_quant import fixture_metadata, run_backtest

from .datasets import historical_datasets, historical_panel
from .desk import DeskManager
from .desk import router as desk_router
from .models import (
    ComparisonReport,
    Dataset,
    DatasetList,
    Experiment,
    ExperimentConfig,
    ExperimentList,
    Health,
    ModelList,
    Ready,
    Result,
    TrainingJob,
    TrainingJobList,
    TrainingRequest,
)
from .provenance import runtime_provenance
from .store import QueueFullError, Store
from .training_jobs import TerminalTrainingError, TrainingManager

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_fixtures_enabled() -> bool:
    """Synthetic datasets are opt-in automation inputs, never a research fallback."""
    return os.getenv("ENABLE_TEST_FIXTURES", "false").lower() == "true"


class Worker:
    """One bounded research worker; numerical work never runs on the event loop."""

    def __init__(self, store: Store, training_manager: TrainingManager | None = None):
        self.store = store
        self.training_manager = training_manager
        self.stop = threading.Event()
        self.wakeup = threading.Event()
        self.failed = threading.Event()
        self.thread = threading.Thread(target=self.run, name="fixture-backtest", daemon=True)

    def run(self):
        while not self.stop.is_set():
            try:
                experiment = self.store.claim()
            except sqlite3.Error:
                self.failed.set()
                return
            if experiment is None:
                self.wakeup.wait(timeout=0.1)
                self.wakeup.clear()
                continue
            try:
                config = experiment.config.model_dump()
                model_id = config.pop("model_id", None)
                if experiment.dataset.kind == "FIXTURE":
                    if not test_fixtures_enabled():
                        raise ValueError("Synthetic fixtures are disabled outside automated tests")
                    fixture_config = {
                        key: value
                        for key, value in config.items()
                        if key
                        not in {
                            "split",
                            "lookback",
                            "risk_aversion",
                        }
                    }
                    payload = run_backtest(fixture_config)
                    actual_hash = payload["manifest"].get("fixture_sha256")
                else:
                    from portfolio_research import run_historical_backtest

                    panel = historical_panel(experiment.dataset.id)
                    actual_hash = panel.metadata["sha256"]
                    if experiment.config.strategy in {"ppo", "ddpg"}:
                        if self.training_manager is None or model_id is None:
                            raise ValueError("Trained model registry is unavailable")
                        payload = self.training_manager.replay(model_id, config)
                    else:
                        payload = run_historical_backtest(panel, config)
                if actual_hash != experiment.dataset.sha256:
                    raise ValueError("Dataset snapshot changed after submission")
                payload["manifest"]["runtime"] = runtime_provenance()
                result = Result.model_validate(payload)
            except Exception:
                # Do not persist provider, filesystem or internal exception messages.
                result = None
            try:
                self.store.finish(experiment, result)
            except sqlite3.Error:
                self.failed.set()
                return

    def close(self):
        self.stop.set()
        self.wakeup.set()
        # Do not let an old writer outlive lifespan and overwrite restart recovery.
        # This CPU-bounded worker must finish its current calculation before closing.
        self.thread.join()


def create_app(
    db_path: str | Path | None = None, *, desk_provider: Provider | None = None
) -> FastAPI:
    if os.getenv("APP_TRADING_MODE", "PAPER").upper() != "PAPER":
        raise RuntimeError("Only PAPER mode is supported.")
    if os.getenv("ENABLE_LIVE_TRADING", "false").lower() not in {"false", "0", "no", ""}:
        raise RuntimeError("Live trading cannot be enabled.")
    configured = Path(db_path or os.getenv("PORTFOLIO_DB_PATH", ".runtime/portfolio.sqlite3"))
    path = configured if configured.is_absolute() else REPOSITORY_ROOT / configured
    store = Store(path)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        store.initialize()
        training_manager = TrainingManager(store)
        training_manager.initialize()
        desk_manager = DeskManager(store, training_manager, desk_provider)
        application.state.desk_manager = desk_manager
        desk_manager.start()
        application.state.training_manager = training_manager
        training_manager.thread.start()
        worker = Worker(store, training_manager)
        application.state.worker = worker
        worker.thread.start()
        try:
            yield
        finally:
            desk_manager.close()
            worker.close()
            training_manager.close()

    application = FastAPI(title="Portfolio AI Lab API", version="0.1.0", lifespan=lifespan)
    application.include_router(desk_router)
    application.state.store = store

    @application.exception_handler(RequestValidationError)
    async def validation_error(_request, error: RequestValidationError):
        # Exclude raw input: non-finite JSON and secret-like extra fields must not echo.
        detail = [
            {"loc": list(item["loc"]), "msg": item["msg"], "type": item["type"]}
            for item in error.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": detail})

    @application.get("/health", response_model=Health)
    def health():
        return Health()

    @application.get("/ready", response_model=Ready)
    def ready():
        try:
            store.check()
        except sqlite3.Error:
            raise HTTPException(status_code=503, detail="Persistence is unavailable.") from None
        worker = application.state.worker
        if worker.failed.is_set() or not worker.thread.is_alive():
            raise HTTPException(status_code=503, detail="Worker is unavailable.")
        if not application.state.training_manager.thread.is_alive():
            raise HTTPException(status_code=503, detail="Training supervisor is unavailable.")
        return Ready()

    @application.get("/api/v1/datasets", response_model=DatasetList)
    def datasets():
        try:
            snapshots = historical_datasets()
        except (ValueError, OSError, DataPipelineError):
            raise HTTPException(
                status_code=503, detail="Historical dataset registry is invalid."
            ) from None
        fixtures = [Dataset.model_validate(fixture_metadata())] if test_fixtures_enabled() else []
        return DatasetList(items=[*fixtures, *snapshots])

    @application.get("/api/v1/experiments", response_model=ExperimentList)
    def experiments():
        items = store.latest()
        if not test_fixtures_enabled():
            items = [item for item in items if item.dataset.kind == "HISTORICAL"]
        return ExperimentList(items=items)

    @application.post("/api/v1/experiments", response_model=Experiment, status_code=202)
    def submit(config: ExperimentConfig):
        worker = application.state.worker
        if worker.failed.is_set() or not worker.thread.is_alive():
            raise HTTPException(status_code=503, detail="Worker is unavailable.")
        if config.dataset_id == "fixture-v1":
            if not test_fixtures_enabled():
                raise HTTPException(
                    status_code=422,
                    detail="Synthetic fixtures are test-only. Select a historical snapshot.",
                )
            dataset = Dataset.model_validate(fixture_metadata())
        else:
            try:
                dataset = next(
                    (item for item in historical_datasets() if item.id == config.dataset_id), None
                )
            except (ValueError, OSError, DataPipelineError):
                raise HTTPException(
                    status_code=503, detail="Historical dataset registry is invalid."
                ) from None
            if dataset is None:
                raise HTTPException(
                    status_code=404,
                    detail="Historical snapshot not found. Run the data pipeline first.",
                )
        try:
            if config.strategy in {"ppo", "ddpg"}:
                application.state.training_manager.validate_replay(
                    config.model_id, config.model_dump()
                )
            experiment = store.submit(config, dataset)
        except QueueFullError:
            raise HTTPException(
                status_code=429, detail="Job queue is full. Try again later."
            ) from None
        except sqlite3.Error:
            raise HTTPException(status_code=503, detail="Persistence is unavailable.") from None
        except (ValueError, OSError):
            raise HTTPException(
                status_code=422, detail="Model/data/economic settings do not match."
            ) from None
        worker.wakeup.set()
        return experiment

    @application.get("/api/v1/experiments/{experiment_id}", response_model=Experiment)
    def experiment_detail(experiment_id: str):
        experiment = store.get(experiment_id)
        if experiment is None or (
            experiment.dataset.kind == "FIXTURE" and not test_fixtures_enabled()
        ):
            raise HTTPException(status_code=404, detail="Experiment not found.")
        return experiment

    @application.get("/api/v1/training", response_model=TrainingJobList)
    def training_list():
        return TrainingJobList(items=application.state.training_manager.latest())

    @application.post("/api/v1/training", response_model=TrainingJob, status_code=202)
    def training_submit(request: TrainingRequest):
        try:
            dataset = next(
                (item for item in historical_datasets() if item.id == request.dataset_id), None
            )
            if dataset is None:
                raise HTTPException(
                    status_code=404, detail="Verified historical dataset not found."
                )
            return application.state.training_manager.submit(request, dataset)
        except QueueFullError:
            raise HTTPException(status_code=429, detail="Training queue is full.") from None
        except RuntimeError:
            raise HTTPException(
                status_code=503, detail="Training supervisor is unavailable."
            ) from None
        except (ValueError, OSError):
            raise HTTPException(
                status_code=422, detail="Training/checkpoint configuration is invalid."
            ) from None

    @application.get("/api/v1/training/{job_id}", response_model=TrainingJob)
    def training_detail(job_id: str):
        job = application.state.training_manager.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Training job not found.")
        return job

    @application.post("/api/v1/training/{job_id}/cancel", response_model=TrainingJob)
    def training_cancel(job_id: str):
        manager = application.state.training_manager
        try:
            job = manager.cancel(job_id)
        except TerminalTrainingError:
            raise HTTPException(
                status_code=409, detail="A terminal training cannot be cancelled."
            ) from None
        if job is None:
            raise HTTPException(status_code=404, detail="Training job not found.")
        return job

    @application.get("/api/v1/models", response_model=ModelList)
    def models_list():
        manager = application.state.training_manager
        items = []
        for job in manager.latest():
            if job.status == "completed" and job.manifest is not None:
                try:
                    items.append(manager.model(job.id))
                except (ValueError, OSError, KeyError, TypeError):
                    continue
        return ModelList(items=items)

    @application.post("/api/v1/training/{job_id}/evaluate", response_model=Result)
    def training_evaluate(job_id: str):
        if application.state.training_manager.get(job_id) is None:
            raise HTTPException(status_code=404, detail="Training job not found.")
        try:
            return application.state.training_manager.evaluate(job_id)
        except (ValueError, OSError, KeyError):
            raise HTTPException(
                status_code=422, detail="Model cannot be evaluated with this dataset."
            ) from None

    @application.post("/api/v1/training/{job_id}/compare", response_model=ComparisonReport)
    def training_compare(job_id: str):
        if application.state.training_manager.get(job_id) is None:
            raise HTTPException(status_code=404, detail="Training job not found.")
        try:
            return application.state.training_manager.comparison(job_id)
        except (ValueError, OSError, KeyError):
            raise HTTPException(
                status_code=422, detail="A completed comparable model is required."
            ) from None

    return application


app = create_app()
