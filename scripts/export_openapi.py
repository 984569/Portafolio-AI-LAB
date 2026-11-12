"""Export the API's authoritative schema for TypeScript generation."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps/api"), str(ROOT / "packages")]

from portfolio_api.main import app  # noqa: E402

destination = ROOT / "packages/contracts/openapi.json"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(destination.relative_to(ROOT))
