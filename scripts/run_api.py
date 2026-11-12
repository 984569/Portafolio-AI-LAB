"""Start the local-only API from any working directory."""

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "apps/api"), str(ROOT / "packages")]
os.chdir(ROOT)

if __name__ == "__main__":
    uvicorn.run("portfolio_api.main:app", host="127.0.0.1", port=8000)
