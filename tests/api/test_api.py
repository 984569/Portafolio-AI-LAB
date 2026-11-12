import sqlite3
import threading
import time

import pytest
from fastapi.testclient import TestClient
from portfolio_api import main, provenance
from portfolio_api.models import Dataset, ExperimentConfig
from portfolio_api.store import Store
from portfolio_quant import fixture_metadata


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "portfolio.sqlite3"


@pytest.fixture
def client(db_path):
    with TestClient(main.create_app(db_path)) as connection:
        yield connection


def wait_finished(client, experiment_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/experiments/{experiment_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"completed", "failed"}:
            return payload
        time.sleep(0.01)
    pytest.fail("Fixture job did not finish within five seconds")


def test_health_ready_fixture_and_missing(client):
    assert client.get("/health").json() == {
        "status": "ok", "service": "portfolio-ai-lab-api", "mode": "PAPER",
    }
    assert client.get("/ready").json() == {"status": "ready", "mode": "PAPER"}
    dataset = client.get("/api/v1/datasets").json()["items"][0]
    assert dataset["kind"] == "FIXTURE"
    assert dataset["id"] == "fixture-v1"
    assert len(dataset["sha256"]) == 64
    assert client.get("/api/v1/experiments").json() == {"items": []}
    assert client.get("/api/v1/experiments/missing").status_code == 404


@pytest.mark.parametrize("fields", [
    {"name": ""}, {"name": "   "}, {"name": "x" * 81},
    {"strategy": "ppo"}, {"dataset_id": "live"},
    {"initial_capital": 0}, {"initial_capital": 1000000001},
    {"transaction_cost_bps": -1}, {"transaction_cost_bps": 101},
    {"risk_free_rate": -1}, {"risk_free_rate": 1.01},
    {"seed": -1}, {"seed": 2147483648}, {"seed": 2.5},
    {"initial_capital": True}, {"initial_capital": "10000"},
    {"transaction_cost_bps": False}, {"risk_free_rate": "0.01"},
    {"live_trading": "secret-marker"},
])
def test_invalid_config(client, fields):
    response = client.post("/api/v1/experiments", json={"name": "Validation", **fields})
    assert response.status_code == 422
    assert "secret-marker" not in response.text
    assert client.get("/api/v1/experiments").json()["items"] == []


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_values_are_clean_422(client, value):
    response = client.post(
        "/api/v1/experiments",
        content='{"name":"Nonfinite","initial_capital":' + value + '}',
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]


def test_job_completed_atomically_and_persisted(db_path):
    with TestClient(main.create_app(db_path)) as client:
        response = client.post("/api/v1/experiments", json={"name": "Persistence"})
        assert response.status_code == 202
        submitted = response.json()
        assert submitted["status"] == "queued"
        assert submitted["result"] is None
        finished = wait_finished(client, submitted["id"])
        assert finished["status"] == "completed"
        assert finished["error"] is None
        assert finished["completed_at"].endswith("Z")
        assert finished["result"]["equity"][0]["equity"] == 10000
        runtime = finished["result"]["manifest"]["runtime"]
        assert runtime["git_commit"] is None or len(runtime["git_commit"]) in {40, 64}
        assert runtime["git_dirty"] in {True, False, None}
        assert runtime["dependency_versions"]["fastapi"]
        assert runtime["dependency_versions"]["pydantic"]
        assert runtime["recorded_at"].endswith("Z")
        with sqlite3.connect(db_path) as database:
            status, payload = database.execute(
                "SELECT status, payload FROM experiments WHERE id=?", (submitted["id"],)
            ).fetchone()
            assert status == "completed"
            assert '"result":{' in payload
            assert database.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
    with TestClient(main.create_app(db_path)) as restarted:
        assert restarted.get(f"/api/v1/experiments/{submitted['id']}").json() == finished


def test_restart_marks_queued_and_running_failed(db_path):
    store = Store(db_path)
    store.initialize()
    dataset = Dataset.model_validate(fixture_metadata())
    first = store.submit(ExperimentConfig(name="Running"), dataset)
    assert store.claim().id == first.id
    second = store.submit(ExperimentConfig(name="Queued"), dataset)
    with TestClient(main.create_app(db_path)) as client:
        for experiment_id in (first.id, second.id):
            payload = client.get(f"/api/v1/experiments/{experiment_id}").json()
            assert payload["status"] == "failed"
            assert payload["result"] is None
            assert "restart" in payload["error"]
            assert payload["completed_at"]


def test_job_exception_is_redacted_and_worker_recovers(client, monkeypatch):
    original = main.run_backtest

    def broken(_config):
        raise RuntimeError("secret-marker in stack /private/path")

    monkeypatch.setattr(main, "run_backtest", broken)
    experiment_id = client.post("/api/v1/experiments", json={"name": "Fails"}).json()["id"]
    payload = wait_finished(client, experiment_id)
    assert payload["status"] == "failed"
    assert payload["result"] is None
    assert "secret-marker" not in str(payload)
    monkeypatch.setattr(main, "run_backtest", original)
    experiment_id = client.post("/api/v1/experiments", json={"name": "Recovers"}).json()["id"]
    assert wait_finished(client, experiment_id)["status"] == "completed"
    assert client.get("/ready").status_code == 200


def test_queue_is_bounded_and_worker_off_request_thread(db_path, monkeypatch):
    entered = threading.Event()
    release = threading.Event()
    worker_names = []
    original = main.run_backtest

    def blocked(config):
        worker_names.append(threading.current_thread().name)
        entered.set()
        assert release.wait(timeout=5)
        return original(config)

    monkeypatch.setattr(main, "run_backtest", blocked)
    with TestClient(main.create_app(db_path)) as client:
        try:
            first = client.post("/api/v1/experiments", json={"name": "Blocked"})
            assert first.status_code == 202
            assert entered.wait(timeout=2)
            for number in range(15):
                assert client.post(
                    "/api/v1/experiments", json={"name": f"Queued {number}"},
                ).status_code == 202
            response = client.post("/api/v1/experiments", json={"name": "Overflow"})
            assert response.status_code == 429
            assert len(client.get("/api/v1/experiments").json()["items"]) == 16
            assert client.get("/health").status_code == 200
            assert worker_names == ["fixture-backtest"]
        finally:
            release.set()
        assert wait_finished(client, first.json()["id"])["status"] == "completed"


@pytest.mark.parametrize("environment", [
    {"APP_TRADING_MODE": "LIVE"}, {"ENABLE_LIVE_TRADING": "true"},
])
def test_live_mode_is_rejected(db_path, monkeypatch, environment):
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(RuntimeError, match="PAPER|Live"):
        main.create_app(db_path)


def test_db_path_relative_to_repository_not_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PORTFOLIO_DB_PATH", ".runtime/relative-check.sqlite3")
    application = main.create_app()
    assert application.state.store.path == main.REPOSITORY_ROOT / ".runtime/relative-check.sqlite3"


def test_openapi_contains_complete_result_contract(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {
        "ExperimentConfig", "Dataset", "Experiment", "Result", "Metrics", "EquityPoint",
        "Allocation", "AuditEvent", "ExperimentList", "DatasetList", "Health",
    } <= schemas.keys()
    assert schemas["Experiment"]["additionalProperties"] is False


@pytest.mark.parametrize("operation", ["claim", "finish"])
def test_database_worker_failure_is_unready_and_shutdown_clean(db_path, monkeypatch, operation):
    application = main.create_app(db_path)

    def broken(*_args):
        raise sqlite3.OperationalError("secret-marker")

    monkeypatch.setattr(application.state.store, operation, broken)
    with TestClient(application) as client:
        if operation == "finish":
            response = client.post("/api/v1/experiments", json={"name": "DB failure"})
            assert response.status_code == 202
        application.state.worker.thread.join(timeout=2)
        assert not application.state.worker.thread.is_alive()
        response = client.get("/ready")
        assert response.status_code == 503
        assert "secret-marker" not in response.text
        assert client.get("/health").status_code == 200
        before = client.get("/api/v1/experiments").json()["items"]
        response = client.post("/api/v1/experiments", json={"name": "Worker unavailable"})
        assert response.status_code == 503
        assert client.get("/api/v1/experiments").json()["items"] == before
    assert not application.state.worker.thread.is_alive()


def test_runtime_provenance_missing_git_is_explicit(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise FileNotFoundError("secret-marker")

    monkeypatch.setattr(provenance.subprocess, "run", unavailable)
    runtime = provenance.runtime_provenance()
    assert runtime["git_commit"] is None
    assert runtime["git_dirty"] is None
    assert "unavailable" in runtime["git_reason"]
    assert "secret-marker" not in str(runtime)


def test_worker_rejects_result_from_changed_dataset(client, monkeypatch):
    metadata = fixture_metadata()
    metadata["sha256"] = "0" * 64
    monkeypatch.setattr(main, "fixture_metadata", lambda: metadata)
    response = client.post("/api/v1/experiments", json={"name": "Changed fixture"})
    assert response.status_code == 202
    payload = wait_finished(client, response.json()["id"])
    assert payload["status"] == "failed"
    assert payload["result"] is None
    assert payload["error"] == "Backtest failed. No result was saved."
    assert payload["dataset"]["sha256"] == "0" * 64


def test_list_is_newest_first_and_limited_to_100(db_path):
    store = Store(db_path)
    store.initialize()
    dataset = Dataset.model_validate(fixture_metadata())
    for number in range(101):
        experiment = store.submit(ExperimentConfig(name=f"Run {number}"), dataset)
        store.finish(experiment, None)
    with TestClient(main.create_app(db_path)) as client:
        items = client.get("/api/v1/experiments").json()["items"]
        assert len(items) == 100
        assert items[0]["name"] == "Run 100"
        assert items[-1]["name"] == "Run 1"
