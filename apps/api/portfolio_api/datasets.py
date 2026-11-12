"""Verified local snapshot registry; HTTP never downloads or substitutes prices."""

import os
from pathlib import Path

from .models import Dataset

ROOT = Path(__file__).resolve().parents[3]


def data_root() -> Path:
    path = Path(os.getenv("MARKET_DATA_ROOT", ".runtime/datasets"))
    return path if path.is_absolute() else ROOT / path


def historical_datasets() -> list[Dataset]:
    from market_data import list_snapshots

    return [Dataset.model_validate(metadata) for metadata in list_snapshots(data_root())]


def historical_panel(dataset_id: str):
    from market_data import load_snapshot

    return load_snapshot(data_root(), dataset_id)
