import json
from pathlib import Path

import pytest
from portfolio_rl.common import write_json
from portfolio_rl.config import TrainingConfig


def test_atomic_progress_retries_transient_windows_read_lock(tmp_path, monkeypatch):
    destination = tmp_path / "progress.json"
    destination.write_text('{"old":true}', encoding="utf-8")
    replace = Path.replace
    attempts = []

    def transient(self, target):
        attempts.append(1)
        if len(attempts) < 3:
            assert json.loads(destination.read_text()) == {"old": True}
            raise PermissionError("Windows reader has target open")
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", transient)
    write_json(destination, {"progress": 0.5})
    assert json.loads(destination.read_text()) == {"progress": 0.5}
    assert len(attempts) == 3


def test_resource_and_holdout_configs_are_bounded():
    with pytest.raises(ValueError):
        TrainingConfig(algorithm="ppo", dataset_id="offline-test", training_end="2024-01-01")
    with pytest.raises(ValueError):
        TrainingConfig(
            algorithm="ppo",
            dataset_id="offline-test",
            total_timesteps=262144,
            checkpoint_frequency=32,
        )
