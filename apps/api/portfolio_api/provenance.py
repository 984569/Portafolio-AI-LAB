"""Read-only runtime provenance; never reads Git remotes or credentials."""

import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .store import timestamp

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def runtime_provenance() -> dict:
    runtime = {
        "git_commit": None,
        "git_dirty": None,
        "recorded_at": timestamp(),
        "dependency_versions": {},
    }
    for package in (
        "fastapi", "pydantic", "numpy", "scipy", "pandas", "pyarrow",
        "exchange-calendars", "gymnasium", "stable-baselines3", "torch",
    ):
        try:
            runtime["dependency_versions"][package] = version(package)
        except PackageNotFoundError:
            runtime["dependency_versions"][package] = None
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=REPOSITORY_ROOT,
            capture_output=True, text=True, timeout=2, check=False,
        )
        if commit.returncode == 0:
            runtime["git_commit"] = commit.stdout.strip()
        else:
            runtime["git_reason"] = "No readable HEAD commit."
        status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=REPOSITORY_ROOT,
            capture_output=True, text=True, timeout=2, check=False,
        )
        if status.returncode == 0:
            runtime["git_dirty"] = bool(status.stdout.strip())
        else:
            runtime["git_reason"] = "Git working-tree status unavailable."
    except (OSError, subprocess.TimeoutExpired):
        runtime["git_reason"] = "Git command unavailable or timed out."
    return runtime
