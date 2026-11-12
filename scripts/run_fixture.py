"""Run the same deterministic fixture used by the API without a web server."""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))

from portfolio_quant import run_backtest  # noqa: E402

if __name__ == "__main__":
    if os.getenv("ENABLE_TEST_FIXTURES", "false").lower() != "true":
        raise SystemExit("Synthetic fixtures are restricted to automated test mode.")
    result = run_backtest({"name": "CLI fixture verification"})
    print(json.dumps(result, indent=2, allow_nan=False))
