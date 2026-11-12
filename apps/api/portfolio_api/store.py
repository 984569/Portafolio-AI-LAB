"""Bounded SQLite job queue, owned by one local API process."""

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .models import Dataset, Experiment, ExperimentConfig, Result

MAX_PENDING = 16


def timestamp() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class QueueFullError(Exception):
    """The bounded unfinished-job capacity has been reached."""


class Store:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.execute("PRAGMA busy_timeout=5000")
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS experiments "
                "(id TEXT PRIMARY KEY, status TEXT NOT NULL, payload TEXT NOT NULL)"
            )
            rows = connection.execute(
                "SELECT payload FROM experiments WHERE status IN ('queued', 'running')"
            ).fetchall()
            for (payload,) in rows:
                experiment = Experiment.model_validate_json(payload)
                experiment.status = "failed"
                experiment.completed_at = timestamp()
                experiment.error = "Interrupted by API restart. Submit a new experiment."
                experiment.result = None
                self.save(connection, experiment)

    @staticmethod
    def save(connection, experiment: Experiment):
        connection.execute(
            "UPDATE experiments SET status=?, payload=? WHERE id=?",
            (experiment.status, experiment.model_dump_json(), experiment.id),
        )

    def check(self):
        with self.connection() as connection:
            connection.execute("SELECT COUNT(*) FROM experiments").fetchone()

    def submit(self, config: ExperimentConfig, dataset: Dataset) -> Experiment:
        experiment = Experiment(
            id=str(uuid4()), name=config.name, status="queued", created_at=timestamp(),
            completed_at=None, config=config, dataset=dataset, result=None, error=None,
        )
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            pending = connection.execute(
                "SELECT COUNT(*) FROM experiments WHERE status IN ('queued', 'running')"
            ).fetchone()[0]
            if pending >= MAX_PENDING:
                raise QueueFullError
            connection.execute(
                "INSERT INTO experiments(id, status, payload) VALUES (?, ?, ?)",
                (experiment.id, experiment.status, experiment.model_dump_json()),
            )
        return experiment

    def claim(self) -> Experiment | None:
        with self.connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT payload FROM experiments WHERE status='queued' ORDER BY rowid LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            experiment = Experiment.model_validate_json(row[0])
            experiment.status = "running"
            self.save(connection, experiment)
            return experiment

    def finish(self, experiment: Experiment, result: Result | None):
        experiment.status = "completed" if result is not None else "failed"
        experiment.result = result
        experiment.error = None if result is not None else "Backtest failed. No result was saved."
        experiment.completed_at = timestamp()
        with self.connection() as connection:
            self.save(connection, experiment)

    def get(self, experiment_id: str) -> Experiment | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT payload FROM experiments WHERE id=?", (experiment_id,)
            ).fetchone()
        return Experiment.model_validate_json(row[0]) if row else None

    def latest(self) -> list[Experiment]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT payload FROM experiments ORDER BY rowid DESC LIMIT 100"
            ).fetchall()
        return [Experiment.model_validate_json(row[0]) for row in rows]
