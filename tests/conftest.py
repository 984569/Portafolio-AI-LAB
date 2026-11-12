"""Keep legacy fixture checks isolated to automated test processes."""

import pytest


@pytest.fixture(autouse=True)
def automated_fixture_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_TEST_FIXTURES", "true")
    monkeypatch.setenv("TRAINING_ROOT", str(tmp_path / "training"))
