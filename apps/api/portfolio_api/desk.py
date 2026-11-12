"""Bounded Agent Desk worker and append-only SQLite audit."""

import threading
from typing import Literal
from uuid import uuid4

from agent_desk.contracts import DeskEvent, DeskOutcome, DeskRequest, Provider, ProviderError
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .datasets import historical_panel
from .store import QueueFullError, Store, timestamp
from .training_jobs import TrainingManager


class DeskAvailability(BaseModel):
    enabled: bool
    provider: Literal["openrouter", "mock"] | None = None
    model: str | None = None
    endpoint_provider: str | None = None
    code: str


class RecordedEvent(BaseModel):
    sequence: int
    recorded_at: str
    event: DeskEvent


class DeskRun(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "blocked"]
    mode: Literal["PAPER"] = "PAPER"
    scope: Literal["llm_exploratory_historical"] = "llm_exploratory_historical"
    created_at: str
    finished_at: str | None = None
    request: DeskRequest
    provider: DeskAvailability
    outcome: DeskOutcome | None = None
    events: list[RecordedEvent] = Field(default_factory=list)


class DeskRunList(BaseModel):
    items: list[DeskRun]


class DeskManager:
    def __init__(
        self, store: Store, training: TrainingManager, injected_provider: Provider | None
    ) -> None:
        from agent_desk.provider import provider_from_env

        self.store = store
        self.training = training
        code = "provider_not_configured"
        try:
            self.provider = (
                injected_provider if injected_provider is not None else provider_from_env()
            )
        except ProviderError:
            self.provider = None
            code = "provider_configuration"
        self.availability = (
            DeskAvailability(
                enabled=True,
                provider=self.provider.provider,
                model=self.provider.model,
                endpoint_provider=self.provider.endpoint_provider,
                code="configured",
            )
            if self.provider is not None
            else DeskAvailability(enabled=False, code=code)
        )
        self.stop = threading.Event()
        self.wakeup = threading.Event()
        self.thread = threading.Thread(target=self.work, name="agent-desk", daemon=True)

    def start(self) -> None:
        with self.store.connection() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS desk_runs "
                "(id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS desk_events "
                "(sequence INTEGER PRIMARY KEY, run_id TEXT NOT NULL, "
                "recorded_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS desk_events_run ON desk_events(run_id, sequence)"
            )
            for (payload,) in db.execute(
                "SELECT payload FROM desk_runs WHERE status IN ('queued','running')"
            ).fetchall():
                run = DeskRun.model_validate_json(payload)
                self.append(
                    db,
                    run.id,
                    DeskEvent(
                        stage="final",
                        status="blocked",
                        code="interrupted",
                    ),
                )
                self.finish(db, run, DeskOutcome(decision="blocked", code="interrupted"))
        if self.provider is not None:
            self.thread.start()

    def close(self) -> None:
        self.stop.set()
        self.wakeup.set()
        if self.thread.ident is not None:
            self.thread.join()

    def submit(self, config: DeskRequest) -> DeskRun:
        if self.stop.is_set() or not self.thread.is_alive():
            raise RuntimeError("Desk provider is unavailable")
        run = DeskRun(
            id=str(uuid4()),
            status="queued",
            created_at=timestamp(),
            request=config,
            provider=self.availability,
        )
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            pending = db.execute(
                "SELECT count(*) FROM desk_runs WHERE status IN ('queued','running')"
            ).fetchone()[0]
            if pending >= 4:
                raise QueueFullError
            db.execute(
                "INSERT INTO desk_runs VALUES (?,?,?)",
                (
                    run.id,
                    run.status,
                    run.model_dump_json(),
                ),
            )
        self.wakeup.set()
        return run

    def claim(self) -> DeskRun | None:
        with self.store.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload FROM desk_runs WHERE status='queued' ORDER BY rowid LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            run = DeskRun.model_validate_json(row[0])
            run.status = "running"
            self.save(db, run)
            return run

    @staticmethod
    def save(db, run: DeskRun) -> None:
        db.execute(
            "UPDATE desk_runs SET status=?, payload=? WHERE id=?",
            (
                run.status,
                run.model_dump_json(),
                run.id,
            ),
        )

    @classmethod
    def finish(cls, db, run: DeskRun, outcome: DeskOutcome) -> None:
        run.status = "blocked" if outcome.decision == "blocked" else "completed"
        run.outcome, run.finished_at = outcome, timestamp()
        cls.save(db, run)

    @staticmethod
    def append(db, run_id: str, event: DeskEvent) -> None:
        db.execute(
            "INSERT INTO desk_events(run_id, recorded_at, payload) VALUES (?,?,?)",
            (run_id, timestamp(), event.model_dump_json()),
        )

    def get(self, run_id: str) -> DeskRun | None:
        with self.store.connection() as db:
            db.execute("BEGIN")
            row = db.execute("SELECT payload FROM desk_runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                return None
            run = DeskRun.model_validate_json(row[0])
            run.events = [
                RecordedEvent(
                    sequence=index, recorded_at=at, event=DeskEvent.model_validate_json(p)
                )
                for index, at, p in db.execute(
                    "SELECT sequence, recorded_at, payload FROM desk_events "
                    "WHERE run_id=? ORDER BY sequence",
                    (run_id,),
                )
            ]
            return run

    def latest(self) -> list[DeskRun]:
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT payload FROM desk_runs ORDER BY rowid DESC LIMIT 50"
            ).fetchall()
        return [DeskRun.model_validate_json(row[0]) for row in rows]

    def work(self) -> None:
        provider = self.provider
        assert provider is not None
        while not self.stop.is_set():
            run = self.claim()
            if run is None:
                self.wakeup.wait(0.2)
                self.wakeup.clear()
                continue

            self.run_job(run, provider)

    def run_job(self, run: DeskRun, provider: Provider) -> None:
        from agent_desk.workflow import run_workflow

        def emit(event: DeskEvent) -> None:
            if event.stage == "final":
                # Terminal event and final outcome are committed together.
                terminal.append(event)
            else:
                with self.store.connection() as db:
                    self.append(db, run.id, event)

        terminal: list[DeskEvent] = []
        try:
            panel = historical_panel(run.request.dataset_id)
            model_id = run.request.model_id
            bundle = None
            if model_id is not None:
                from portfolio_rl.common import load_bundle

                model = self.training.model(model_id)
                if model.dataset_id != run.request.dataset_id:
                    raise ValueError("Model snapshot mismatch")
                bundle = load_bundle(self.training.directory(model_id))
            outcome = run_workflow(run.request, panel, provider, emit, bundle=bundle)
        except Exception:
            outcome = DeskOutcome(decision="blocked", code="desk_input_unavailable")
            terminal = [DeskEvent(stage="final", status="blocked", code=outcome.code)]
        with self.store.connection() as db:
            for event in terminal:
                self.append(db, run.id, event)
            self.finish(db, run, outcome)


router = APIRouter(prefix="/api/v1/agent-desk")


@router.get("/status", response_model=DeskAvailability)
def desk_status(request: Request) -> DeskAvailability:
    manager: DeskManager = request.app.state.desk_manager
    if manager.availability.enabled and not manager.thread.is_alive():
        return manager.availability.model_copy(
            update={"enabled": False, "code": "worker_unavailable"}
        )
    return manager.availability


@router.post("/runs", response_model=DeskRun, status_code=202)
def submit_run(config: DeskRequest, request: Request) -> DeskRun:
    manager: DeskManager = request.app.state.desk_manager
    try:
        return manager.submit(config)
    except QueueFullError:
        raise HTTPException(status_code=429, detail="Agent Desk queue is full.") from None
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Agent Desk provider is unavailable.") from None


@router.get("/runs", response_model=DeskRunList)
def desk_runs(request: Request) -> DeskRunList:
    return DeskRunList(items=request.app.state.desk_manager.latest())


@router.get("/runs/{run_id}", response_model=DeskRun)
def desk_run(run_id: str, request: Request) -> DeskRun:
    manager: DeskManager = request.app.state.desk_manager
    run = manager.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Agent Desk run not found.")
    return run
