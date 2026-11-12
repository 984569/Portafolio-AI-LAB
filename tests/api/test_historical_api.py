"""Offline API doubles never register synthetic prices as a real dataset."""

import threading
import time

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from market_data import DataPipelineError
from portfolio_api import main
from portfolio_api.models import Dataset
from portfolio_core import PricePanel
from portfolio_research import run_historical_backtest

DATASET_ID = "historical-" + "b" * 64


@pytest.fixture
def offline_panel():
    dates = tuple(pd.bdate_range("2021-12-01", "2022-01-20").strftime("%Y-%m-%d"))
    rng = np.random.default_rng(29)
    prices = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.01, (len(dates), 2)), axis=0))
    metadata = {
        "id": DATASET_ID,
        "kind": "HISTORICAL",
        "source": "OFFLINE TEST DOUBLE",
        "sha256": "b" * 64,
        "assets": ["TEST_A", "TEST_B"],
        "start_date": dates[0],
        "end_date": dates[-1],
        "observations": len(dates),
        "provenance": {"provider": "offline test"},
        "quality_report": {"status": "passed", "scope": "synthetic test only"},
        "splits": {},
    }
    return PricePanel(dates, ("TEST_A", "TEST_B"), prices, metadata)


def wait_result(client, experiment_id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        run = client.get(f"/api/v1/experiments/{experiment_id}").json()
        if run["status"] in {"completed", "failed"}:
            return run
        time.sleep(0.01)
    pytest.fail("Offline test job did not finish")


@pytest.mark.parametrize("strategy", ["equal_weight", "markowitz"])
def test_historical_dispatch_typed_result_and_persistence(
    tmp_path, monkeypatch, offline_panel, strategy
):
    metadata = Dataset.model_validate(offline_panel.metadata)
    monkeypatch.setattr(main, "historical_datasets", lambda: [metadata])
    monkeypatch.setattr(main, "historical_panel", lambda dataset_id: offline_panel)
    path = tmp_path / "integration.sqlite3"
    with TestClient(main.create_app(path)) as client:
        datasets = client.get("/api/v1/datasets").json()["items"]
        assert datasets[0]["kind"] == "FIXTURE"
        assert datasets[1]["provenance"]["provider"] == "offline test"
        response = client.post(
            "/api/v1/experiments",
            json={
                "name": "OFFLINE TEST ONLY",
                "dataset_id": DATASET_ID,
                "strategy": strategy,
                "lookback": 5,
                "split": "validation",
            },
        )
        assert response.status_code == 202
        run = wait_result(client, response.json()["id"])
        assert run["status"] == "completed", run["error"]
        expected = run_historical_backtest(offline_panel, run["config"])
        assert run["result"]["metrics"] == pytest.approx(expected["metrics"])
        assert run["result"]["manifest"]["dataset_sha256"] == metadata.sha256
        assert run["result"]["manifest"]["evaluation"]["holdout_evaluated"] is False
        assert run["dataset"]["kind"] == "HISTORICAL"
    with TestClient(main.create_app(path)) as client:
        assert client.get(f"/api/v1/experiments/{run['id']}").json() == run


@pytest.mark.parametrize(
    "fields",
    [
        {"split": "final_test"},
        {"split": "2024"},
        {"lookback": True},
        {"lookback": 253},
        {"lookback": 1},
        {"risk_aversion": 0},
        {"risk_aversion": True},
        {"strategy": "markowitz", "dataset_id": "fixture-v1"},
        {"dataset_id": "historical-../../private"},
    ],
)
def test_holdout_and_incompatible_configs_rejected(tmp_path, fields):
    with TestClient(main.create_app(tmp_path / "validation.sqlite3")) as client:
        response = client.post("/api/v1/experiments", json={"name": "Invalid", **fields})
        assert response.status_code == 422
        assert client.get("/api/v1/experiments").json()["items"] == []


def test_missing_or_corrupt_registry_fails_without_synthetic_substitution(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "historical_datasets", lambda: [])
    with TestClient(main.create_app(tmp_path / "registry.sqlite3")) as client:
        assert (
            client.post(
                "/api/v1/experiments",
                json={
                    "name": "Missing",
                    "dataset_id": DATASET_ID,
                },
            ).status_code
            == 404
        )

        def broken():
            raise DataPipelineError("snapshot_integrity", "private-path-secret-marker")

        monkeypatch.setattr(main, "historical_datasets", broken)
        response = client.get("/api/v1/datasets")
        assert response.status_code == 503
        assert "secret-marker" not in response.text
        assert (
            client.post(
                "/api/v1/experiments",
                json={
                    "name": "Corrupt",
                    "dataset_id": DATASET_ID,
                },
            ).status_code
            == 503
        )
        assert client.get("/api/v1/experiments").json()["items"] == []


def test_worker_shutdown_waits_for_current_job_before_restart(tmp_path, monkeypatch):
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()
    original = main.run_backtest

    def blocked(config):
        entered.set()
        assert release.wait(timeout=12)
        return original(config)

    monkeypatch.setattr(main, "run_backtest", blocked)
    application = main.create_app(tmp_path / "shutdown.sqlite3")
    context = TestClient(application)
    client = context.__enter__()
    response = client.post("/api/v1/experiments", json={"name": "Ordered shutdown"})
    assert entered.wait(timeout=2)

    def close_context():
        context.__exit__(None, None, None)
        closed.set()

    closer = threading.Thread(target=close_context)
    closer.start()
    try:
        assert not closed.wait(timeout=5.2), "Worker outlived its owning lifespan"
    finally:
        release.set()
        closer.join(timeout=5)
    assert closed.is_set()
    assert not application.state.worker.thread.is_alive()
    with TestClient(main.create_app(application.state.store.path)) as restarted:
        result = restarted.get(f"/api/v1/experiments/{response.json()['id']}").json()
        assert result["status"] == "completed"


def test_normal_runtime_hides_and_rejects_synthetic_fixtures(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "historical_datasets", lambda: [])
    path = tmp_path / "research-mode.sqlite3"
    with TestClient(main.create_app(path)) as client:
        previous = client.post("/api/v1/experiments", json={"name": "Automation only"}).json()
        assert wait_result(client, previous["id"])["status"] == "completed"
        monkeypatch.setenv("ENABLE_TEST_FIXTURES", "false")
        assert client.get("/api/v1/datasets").json() == {"items": []}
        assert client.post("/api/v1/experiments", json={"name": "No fallback"}).status_code == 422
        assert client.get("/api/v1/experiments").json() == {"items": []}
        assert client.get(f"/api/v1/experiments/{previous['id']}").status_code == 404
        # The original persisted test evidence is preserved, not deleted.
        assert application_record_exists(client.app.state.store.path, previous["id"])


def application_record_exists(path, experiment_id):
    from portfolio_api.store import Store

    return Store(path).get(experiment_id) is not None
