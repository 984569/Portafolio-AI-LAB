"""Real historical data ingestion; no synthetic fallback or network at import time."""

from .pipeline import (
    UNIVERSE,
    DataPipelineError,
    download_snapshot,
    list_snapshots,
    load_snapshot,
)

__all__ = [
    "UNIVERSE",
    "DataPipelineError",
    "download_snapshot",
    "list_snapshots",
    "load_snapshot",
]
