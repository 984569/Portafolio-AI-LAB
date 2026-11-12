"""Verify the Stage 0 scaffold without pretending application tests exist."""

import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    "AGENTS.md", "DESIGN.md", "README.md", ".gitignore", ".env.example",
    "docs/architecture.md", "docs/development-plan.md", "docs/AGENT-SWARM.md",
    "docs/environment-audit.md", "docs/STATUS.md", "docs/TEST-MATRIX.md",
]
for relative in required:
    assert (ROOT / relative).is_file(), relative
with (ROOT / "pyproject.toml").open("rb") as stream:
    tomllib.load(stream)
json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
assert sys.version_info[:2] == (3, 11), sys.version
assert "APP_TRADING_MODE=PAPER" in (ROOT / ".env.example").read_text()
print(f"Stage 0 scaffold verified: {len(required)} files, TOML/JSON valid, Python 3.11.")
