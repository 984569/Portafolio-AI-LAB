"""Run the real-data pipeline from any working directory, without credentials."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
os.chdir(ROOT)

from market_data.__main__ import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
