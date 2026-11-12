"""Training control-plane checks; subprocess doubles are explicitly offline-only."""

import os
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from portfolio_api import main
from portfolio_api import training_jobs as module
from portfolio_api.models import Dataset

DATASET_ID = "historical-" + "c" * 64
MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def offline_metadata() -> Dataset:
    return Dataset(
        id=DATASET_ID,
        kind="HISTORICAL",
        source="OFFLINE TRAINING API TEST DOUBLE; not market observations",
        sha256="c" * 64,
        assets=["TEST_A", "TEST_B"],
        start_date="2015-01-02",
        end_date="2024-12-31",
        observations=100,
        provenance={"provider": "offline test only"},
    )


@pytest.fixture
def application(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, offline_metadata: Dataset,
) -> Any:
    monkeypatch.setenv("TRAINING_ROOT", str(tmp_path / "models"))
    monkeypatch.setenv("MARKET_DATA_ROOT", str(tmp_path / "unregistered-test-inputs"))
    monkeypatch.setattr(main, "historical_datasets", lambda: [offline_metadata])
    return main.create_app(tmp_path / "training.sqlite3")


def request(**changes: Any) -> dict[str, Any]:
    return {
        "name": "Offline control-plane test",
        "algorithm": "ppo",
        "dataset_id": DATASET_ID,
        "total_timesteps": 256,
        "checkpoint_frequency": 256,
        **changes,
    }


def await_status(client: TestClient, job_id: str, desired: set[str]) -> dict[str, Any]:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/training/{job_id}")
        assert response.status_code == 200
        value = response.json()
        if value["status"] in desired:
            return value
        time.sleep(0.02)
    pytest.fail(f"Training job never reached {sorted(desired)}")


def test_pending_job_is_persisted_listed_and_cancelled_without_running(
    application: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module.TrainingManager, "claim", lambda _self: None)
    with TestClient(application) as client:
        response = client.post("/api/v1/training", json=request())
        assert response.status_code == 202
        submitted = response.json()
        assert submitted["status"] == "pending"
        assert submitted["manifest"] is None
        assert submitted["dataset"]["source"].startswith("OFFLINE")
        assert client.get("/api/v1/training").json()["items"][0]["id"] == submitted["id"]
        assert client.get(f"/api/v1/training/{submitted['id']}").json() == submitted
        cancelled = client.post(f"/api/v1/training/{submitted['id']}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
        assert cancelled.json()["cancel_requested"] is True
        assert cancelled.json()["finished_at"]
        assert client.get("/api/v1/models").json() == {"items": []}


@pytest.mark.parametrize(
    "changes",
    [
        {"algorithm": "llm"},
        {"dataset_id": "fixture-v1"},
        {"dataset_id": "../../private"},
        {"training_end": "2022-01-01"},
        {"training_end": "2024-01-01"},
        {"training_end": "20210101"},
        {"seed": True},
        {"total_timesteps": 257},
        {"net_arch": [1000000]},
        {"ppo": {"n_steps": 256, "batch_size": 63}},
        {"algorithm": "ddpg", "ddpg": {"learning_starts": 256}},
        {"max_memory_mb": 0},
        {"max_seconds": 100000},
        {"resume_from_job_id": "../../private"},
        {"openrouter_api_key": "secret-marker"},
    ],
)
def test_invalid_or_temporally_forbidden_training_is_422_without_job(
    application: Any, changes: dict[str, Any],
) -> None:
    with TestClient(application) as client:
        response = client.post("/api/v1/training", json=request(**changes))
        assert response.status_code == 422
        assert "secret-marker" not in response.text
        assert client.get("/api/v1/training").json() == {"items": []}


def test_missing_training_model_and_dataset_are_not_substituted(
    application: Any,
) -> None:
    with TestClient(application) as client:
        assert client.get(f"/api/v1/training/{MISSING_ID}").status_code == 404
        assert client.post(f"/api/v1/training/{MISSING_ID}/cancel").status_code == 404
        assert client.post(f"/api/v1/training/{MISSING_ID}/evaluate").status_code == 404
        assert client.post(
            "/api/v1/training", json=request(dataset_id="historical-" + "d" * 64),
        ).status_code == 404
        assert client.get("/api/v1/training").json() == {"items": []}


def test_queue_cap_is_four_unfinished_training_jobs(
    application: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module.TrainingManager, "claim", lambda _self: None)
    with TestClient(application) as client:
        for index in range(4):
            assert client.post(
                "/api/v1/training", json=request(name=f"Pending offline test {index}"),
            ).status_code == 202
        assert client.post("/api/v1/training", json=request()).status_code == 429
        assert len(client.get("/api/v1/training").json()["items"]) == 4
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 200


def test_subprocess_launch_failure_finishes_job_and_supervisor_remains_available(
    application: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_launch(*_args: Any, **_kwargs: Any) -> Any:
        raise OSError("secret-marker /private/path offline launch failure")

    monkeypatch.setattr(module.subprocess, "Popen", fail_launch)
    with TestClient(application) as client:
        response = client.post("/api/v1/training", json=request())
        assert response.status_code == 202
        failed = await_status(client, response.json()["id"], {"failed"})
        assert failed["finished_at"]
        assert "secret-marker" not in str(failed)
        assert failed["manifest"] is None
        assert client.post(f"/api/v1/training/{failed['id']}/cancel").status_code == 409
        assert application.state.training_manager.thread.is_alive()
        again = client.post("/api/v1/training", json=request(name="Next offline failure"))
        assert again.status_code == 202
        assert await_status(client, again.json()["id"], {"failed"})["status"] == "failed"


def test_stopped_supervisor_rejects_new_training_before_persistence(
    application: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module.TrainingManager, "claim", lambda _self: None)
    with TestClient(application) as client:
        manager = application.state.training_manager
        manager.stop.set()
        manager.thread.join(timeout=2)
        assert not manager.thread.is_alive()
        assert client.post("/api/v1/training", json=request()).status_code == 503
        assert client.get("/api/v1/training").json() == {"items": []}


def test_unknown_resume_is_rejected_without_new_job(application: Any) -> None:
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/training", json=request(resume_from_job_id=MISSING_ID),
        )
        assert response.status_code in {404, 422}
        assert client.get("/api/v1/training").json() == {"items": []}


def test_running_cancellation_reaches_cancelled_not_completed(
    application: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OfflineProcess:
        """No learning or child process: completion follows the cancellation marker."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.pid = os.getpid()
            self.returncode: int | None = None

        def poll(self) -> int | None:
            if list(application.state.training_manager.root.glob("*/cancel.requested")):
                self.returncode = 0
            return self.returncode

        def wait(self, timeout: float | None = None) -> int:
            return self.returncode if self.returncode is not None else 0

        def terminate(self) -> None:
            self.returncode = -15

        def kill(self) -> None:
            self.returncode = -9

    monkeypatch.setattr(module.subprocess, "Popen", OfflineProcess)
    with TestClient(application) as client:
        response = client.post("/api/v1/training", json=request())
        assert response.status_code == 202
        job_id = response.json()["id"]
        await_status(client, job_id, {"running"})
        assert client.post(f"/api/v1/training/{job_id}/cancel").status_code == 200
        result = await_status(client, job_id, {"cancelled"})
        assert result["cancel_requested"] is True
        assert result["manifest"] is None
        assert client.get("/api/v1/models").json() == {"items": []}


def test_progress_update_cannot_erase_cancellation_or_terminal_status(
    application: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module.TrainingManager, "claim", lambda _self: None)
    with TestClient(application) as client:
        job_id = client.post("/api/v1/training", json=request()).json()["id"]
        manager = application.state.training_manager
        cancelled = manager.cancel(job_id)
        assert cancelled is not None and cancelled.cancel_requested
        manager.update_progress(job_id, {"timesteps": 32, "progress": 0.125})
        saved = manager.get(job_id)
        assert saved is not None
        assert saved.status == "cancelled"
        assert saved.cancel_requested is True
        assert saved.progress["timesteps"] == 32
        assert saved.finished_at == cancelled.finished_at


def test_restart_marks_unfinished_training_failed_and_preserves_records(
    application: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module.TrainingManager, "claim", lambda _self: None)
    with TestClient(application) as client:
        job_id = client.post("/api/v1/training", json=request()).json()["id"]
        assert client.get(f"/api/v1/training/{job_id}").json()["status"] == "pending"
    with TestClient(main.create_app(application.state.store.path)) as restarted:
        response = restarted.get(f"/api/v1/training/{job_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "failed"
        assert response.json()["manifest"] is None
        assert "restart" in response.json()["error"]


@pytest.mark.parametrize("identifier", ["../outside", "/absolute", "a/../../b", ""])
def test_training_artifact_path_cannot_escape_root(
    application: Any, identifier: str,
) -> None:
    with TestClient(application):
        manager = application.state.training_manager
        with pytest.raises(ValueError, match="identifier|path"):
            manager.directory(identifier)
