"""Run a fixture demonstration: python -m portfolio_quant."""

import json
import os

from . import run_backtest

if os.getenv("ENABLE_TEST_FIXTURES", "false").lower() != "true":
    raise SystemExit("Synthetic fixtures are restricted to automated test mode.")

print(json.dumps(run_backtest({"name": "CLI synthetic fixture"}), indent=2, allow_nan=False))
