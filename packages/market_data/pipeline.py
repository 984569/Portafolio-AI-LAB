"""Public Yahoo chart snapshots with strict validation and local provenance.

Yahoo's provider Close is retained verbatim; it is not asserted to be an
unadjusted executable quote. Adjusted Close is a retrospectively revised vendor
series. Relative adjusted returns include corporate-action adjustments; never
add the stored dividends or splits to those returns a second time.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path
from typing import Any
from uuid import uuid4

import exchange_calendars as xcals
import numpy as np
import pandas as pd
from portfolio_core import PricePanel

UNIVERSE = ("AAPL", "MSFT", "JPM", "JNJ", "XOM", "PG", "KO", "WMT", "SPY", "GLD")
START = "2015-01-01"
END = "2024-12-31"
PROVIDER_END = "2025-01-01"
SOURCE = "Yahoo Finance public chart HTTP API; exact JSON responses retained"
LIMITATIONS = [
    "Public unofficial endpoint: availability, throttling and revisions are not guaranteed.",
    "Personal educational/research use; provider terms do not imply redistribution rights.",
    "Adjusted history is retrospectively revised, not a point-in-time vintage database.",
    "Provider Close may already include split adjustments; it is not an unadjusted quote.",
    "Corporate-action fields are vendor assertions, not independently reconciled evidence.",
    "XNYS is the common US equity-session proxy, including Nasdaq-listed instruments.",
    "The fixed current universe creates a disclosed survivorship/selection limitation.",
    "No fills, synthetic replacements, dividend double-counting or test-period tuning.",
]
_ID = re.compile(r"historical-[a-f0-9]{12,64}\Z")
_BAR_COLUMNS = (
    "open",
    "high",
    "low",
    "close",
    "adjusted_close",
    "volume",
    "dividends",
    "stock_splits",
)


class DataPipelineError(RuntimeError):
    """A provider, validation or immutable-snapshot failure with a stable code."""

    def __init__(self, code: str, message: str, report: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.report = report or {}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _provider_url(symbol: str) -> str:
    if symbol not in UNIVERSE:
        raise DataPipelineError("invalid_symbol", "Only the academic universe is supported")
    params = urllib.parse.urlencode(
        {
            "period1": 1420070400,
            "period2": 1735689600,
            "interval": "1d",
            "events": "div,splits",
            "includeAdjustedClose": "true",
        }
    )
    return f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{params}"


def _fetch_chart(symbol: str) -> tuple[bytes, dict[str, Any]]:
    url = _provider_url(symbol)
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": "PortfolioAILab/0.2 research"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            # Daily ten-year series should be far smaller than this bounded response.
            raw = response.read(8_000_001)
            if len(raw) > 8_000_000:
                raise DataPipelineError("response_too_large", f"{symbol}: response limit exceeded")
    except urllib.error.HTTPError as exc:
        # No retry or endpoint rotation on throttling. Keep an honest failure.
        raise DataPipelineError(
            "provider_http_error",
            f"{symbol}: Yahoo HTTP {exc.code}",
            {"symbol": symbol, "http_status": exc.code, "url": url},
        ) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise DataPipelineError(
            "provider_unavailable",
            f"{symbol}: Yahoo request failed or timed out",
            {"symbol": symbol, "url": url},
        ) from None
    return raw, {
        "symbol": symbol,
        "url": url,
        "fetched_at": _utc_now(),
        "sha256": _sha(raw),
        "duration_seconds": round(time.monotonic() - started, 3),
        "http_status": 200,
    }


def _number(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DataPipelineError("invalid_provider_data", f"{label}: missing/non-numeric value")
    number = float(value)
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise DataPipelineError("invalid_provider_data", f"{label}: invalid numeric value")
    return number


def _local_date(timestamp: Any) -> str:
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        raise DataPipelineError("invalid_timestamp", "Provider timestamp must be numeric")
    try:
        return str(
            pd.Timestamp(timestamp, unit="s", tz="UTC").tz_convert("America/New_York").date()
        )
    except (ValueError, TypeError, OverflowError):
        raise DataPipelineError("invalid_timestamp", "Provider timestamp is invalid") from None


def _normalize_chart(symbol: str, raw: bytes) -> pd.DataFrame:
    try:
        payload = json.loads(raw)
        chart = payload["chart"]
        if chart.get("error") is not None or not chart["result"]:
            raise DataPipelineError(
                "provider_response_error", f"{symbol}: no price series returned"
            )
        result = chart["result"][0]
        if result["meta"]["symbol"] != symbol or result["meta"]["currency"] != "USD":
            raise DataPipelineError(
                "provider_identity_error", f"{symbol}: symbol/currency mismatch"
            )
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        adjusted = result["indicators"]["adjclose"][0]["adjclose"]
        series = {key: quotes[key] for key in ("open", "high", "low", "close", "volume")}
        series["adjusted_close"] = adjusted
        if not timestamps or any(len(values) != len(timestamps) for values in series.values()):
            raise DataPipelineError(
                "provider_shape_error", f"{symbol}: nonrectangular price arrays"
            )
        dates = [_local_date(stamp) for stamp in timestamps]
        if len(set(dates)) != len(dates):
            raise DataPipelineError("duplicate_sessions", f"{symbol}: duplicate provider sessions")
        if dates != sorted(dates):
            raise DataPipelineError(
                "unsorted_sessions", f"{symbol}: provider sessions are not sorted"
            )
        data = {
            key: [_number(value, f"{symbol}.{key}", positive=key != "volume") for value in values]
            for key, values in series.items()
        }
        frame = pd.DataFrame(data, index=pd.Index(dates, name="date"))
        dividends = dict.fromkeys(dates, 0.0)
        stock_splits = dict.fromkeys(dates, 0.0)
        events = result.get("events", {})
        if not isinstance(events, dict):
            raise DataPipelineError("invalid_actions", f"{symbol}: invalid corporate-action object")
        for event in events.get("dividends", {}).values():
            stamp = _local_date(event["date"])
            if stamp not in frame.index:
                raise DataPipelineError(
                    "invalid_actions", f"{symbol}: dividend outside price sessions"
                )
            dividends[stamp] += _number(event["amount"], f"{symbol}.dividend")
        for event in events.get("splits", {}).values():
            stamp = _local_date(event["date"])
            if stamp not in frame.index:
                raise DataPipelineError(
                    "invalid_actions", f"{symbol}: split outside price sessions"
                )
            numerator = _number(event["numerator"], f"{symbol}.split", positive=True)
            denominator = _number(event["denominator"], f"{symbol}.split", positive=True)
            if stock_splits[stamp] != 0:
                raise DataPipelineError("duplicate_actions", f"{symbol}: duplicate split session")
            stock_splits[stamp] = numerator / denominator
        frame["dividends"] = [dividends[stamp] for stamp in dates]
        frame["stock_splits"] = [stock_splits[stamp] for stamp in dates]
        return frame.loc[:, list(_BAR_COLUMNS)]
    except DataPipelineError:
        raise
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        raise DataPipelineError(
            "invalid_provider_schema", f"{symbol}: provider payload does not match the chart schema"
        ) from None


@lru_cache(maxsize=4)
def _expected_sessions(start: str = START, end: str = END) -> tuple[str, ...]:
    calendar = xcals.get_calendar("XNYS", start=start, end=end)
    # The requested start may be a holiday, before the calendar's first session.
    # Slice sessions directly instead of asking its bounded parser for that holiday.
    sessions = calendar.sessions
    selected = sessions[(sessions >= pd.Timestamp(start)) & (sessions <= pd.Timestamp(end))]
    return tuple(str(stamp.date()) for stamp in selected)


def _split_report(dates: tuple[str, ...]) -> dict[str, Any]:
    ranges = {
        "train": ("2015-01-01", "2021-12-31"),
        "validation": ("2022-01-01", "2023-12-31"),
        "final_test": ("2024-01-01", "2024-12-31"),
    }
    result: dict[str, dict[str, Any]] = {}
    for label, (start, end) in ranges.items():
        selected = [stamp for stamp in dates if start <= stamp <= end]
        if not selected:
            raise DataPipelineError("empty_split", f"The {label} chronological split is empty")
        result[label] = {
            "start_date": selected[0],
            "end_date": selected[-1],
            "observations": len(selected),
            "locked": label == "final_test",
        }
    if sum(item["observations"] for item in result.values()) != len(dates):
        raise DataPipelineError("invalid_splits", "Chronological partitions do not cover the panel")
    return result


def _validate_frames(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    if set(frames) != set(UNIVERSE):
        raise DataPipelineError("incomplete_universe", "All ten academic instruments are required")
    expected = _expected_sessions()
    expected_set = set(expected)
    assets = []
    for symbol in UNIVERSE:
        frame = frames[symbol]
        if frame.index.has_duplicates:
            raise DataPipelineError("duplicate_sessions", f"{symbol}: duplicate sessions")
        dates = tuple(str(stamp) for stamp in frame.index)
        if dates != tuple(sorted(dates)):
            raise DataPipelineError("unsorted_sessions", f"{symbol}: sessions are not sorted")
        missing = sorted(expected_set - set(dates))
        extra = sorted(set(dates) - expected_set)
        if missing or extra:
            raise DataPipelineError(
                "calendar_coverage",
                f"{symbol}: calendar coverage mismatch",
                {
                    "symbol": symbol,
                    "missing_sessions": missing,
                    "unexpected_sessions": extra,
                    "expected_observations": len(expected),
                    "observed": len(frame),
                },
            )
        if any(column not in frame for column in _BAR_COLUMNS):
            raise DataPipelineError(
                "missing_columns", f"{symbol}: required provider fields missing"
            )
        values = frame.loc[:, list(_BAR_COLUMNS)].to_numpy(dtype=np.float64)
        if not np.isfinite(values).all():
            raise DataPipelineError("invalid_prices", f"{symbol}: missing/nonfinite provider cells")
        if (frame[["open", "high", "low", "close", "adjusted_close"]] <= 0).any().any():
            raise DataPipelineError("invalid_prices", f"{symbol}: nonpositive prices")
        if (frame[["volume", "dividends", "stock_splits"]] < 0).any().any():
            raise DataPipelineError(
                "invalid_actions", f"{symbol}: negative volume/corporate actions"
            )
        if (frame["high"] + 1e-8 < frame[["open", "close", "low"]].max(axis=1)).any() or (
            frame["low"] - 1e-8 > frame[["open", "close", "high"]].min(axis=1)
        ).any():
            raise DataPipelineError("invalid_ohlc", f"{symbol}: inconsistent high/low prices")
        factor = frame["adjusted_close"] / frame["close"]
        if not np.isfinite(factor).all() or (factor <= 0).any():
            raise DataPipelineError("invalid_adjustments", f"{symbol}: invalid adjustment factors")
        assets.append(
            {
                "symbol": symbol,
                "observations": len(frame),
                "missing_sessions": 0,
                "duplicate_sessions": 0,
                "invalid_price_cells": 0,
                "dividend_events": int((frame["dividends"] > 0).sum()),
                "split_events": int((frame["stock_splits"] > 0).sum()),
                "adjustment_factor_min": float(factor.min()),
                "adjustment_factor_max": float(factor.max()),
                "adjustment_policy": "Vendor adjusted close; events retained, not double-added",
            }
        )
    return {
        "status": "passed",
        "calendar": "XNYS",
        "start_date": expected[0],
        "end_date": expected[-1],
        "observations": len(expected),
        "assets": assets,
        "missing_data_policy": "Reject; no fill, interpolation or session dropping",
        "corporate_action_verification": (
            "Schema/numeric consistency only; vendor not independently reconciled"
        ),
        "limitations": LIMITATIONS,
    }


def _cache_payload(root: Path, symbol: str) -> tuple[bytes, dict[str, Any]]:
    cache = root / "provider-cache"
    cache.mkdir(parents=True, exist_ok=True)
    raw_path, info_path = cache / f"{symbol}.json", cache / f"{symbol}.meta.json"
    if raw_path.exists() or info_path.exists():
        try:
            raw = raw_path.read_bytes()
            info = json.loads(info_path.read_text(encoding="utf-8"))
            if not isinstance(info, dict):
                raise ValueError("Cache metadata must be an object")
        except (OSError, ValueError, TypeError):
            raise DataPipelineError(
                "cache_integrity", f"{symbol}: cached response/metadata is incomplete or invalid"
            ) from None
        if info.get("sha256") != _sha(raw) or info.get("url") != _provider_url(symbol):
            raise DataPipelineError(
                "cache_integrity", f"{symbol}: cached response hash/request mismatch"
            )
        return raw, {**info, "retrieval": "reused_verified_local_response"}
    raw, info = _fetch_chart(symbol)
    _normalize_chart(symbol, raw)
    raw_path.write_bytes(raw)
    _write_json(info_path, info)
    return raw, {**info, "retrieval": "downloaded"}


def download_snapshot(root: Path) -> dict[str, Any]:
    """Download/validate all ten histories, then atomically register a Parquet snapshot.

    Successful raw responses are cached with request/hash/fetch metadata so a
    resumed run does not repeat successful requests. A failed batch never creates
    a usable historical dataset. 2024 is ingested/quality-checked only, not tuned.
    """
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    raw_payloads: dict[str, bytes] = {}
    provenance: dict[str, Any] = {}
    failures = []
    progress: dict[str, Any] = {"started_at": _utc_now(), "status": "downloading", "symbols": {}}
    with ThreadPoolExecutor(max_workers=3) as executor:
        jobs = {executor.submit(_cache_payload, root, symbol): symbol for symbol in UNIVERSE}
        for future in as_completed(jobs):
            symbol = jobs[future]
            try:
                raw, info = future.result()
                raw_payloads[symbol] = raw
                provenance[symbol] = info
                progress["symbols"][symbol] = {"status": "downloaded", **info}
            except DataPipelineError as exc:
                failure = {"symbol": symbol, "code": exc.code, "message": str(exc), **exc.report}
                failures.append(failure)
                progress["symbols"][symbol] = {"status": "failed", **failure}
            except Exception:
                failure = {
                    "symbol": symbol,
                    "code": "unexpected_provider_error",
                    "message": "Provider/cache operation failed",
                }
                failures.append(failure)
                progress["symbols"][symbol] = {"status": "failed", **failure}
            _write_json(root / "download-progress.json", progress)
    if failures:
        progress.update(status="failed", finished_at=_utc_now(), failures=failures)
        _write_json(root / "download-progress.json", progress)
        raise DataPipelineError(
            "download_incomplete",
            "Historical download incomplete; no snapshot registered",
            progress,
        )
    frames = {symbol: _normalize_chart(symbol, raw_payloads[symbol]) for symbol in UNIVERSE}
    try:
        quality = _validate_frames(frames)
    except DataPipelineError as exc:
        progress.update(status="failed_quality", code=exc.code, message=str(exc), report=exc.report)
        _write_json(root / "download-progress.json", progress)
        raise
    metadata = _persist_snapshot(root, frames, raw_payloads, provenance, quality)
    progress.update(status="completed", finished_at=_utc_now(), dataset_id=metadata["id"])
    _write_json(root / "download-progress.json", progress)
    return metadata


def _persist_snapshot(
    root: Path,
    frames: dict[str, pd.DataFrame],
    raw_payloads: dict[str, bytes],
    provenance: dict[str, Any],
    quality: dict[str, Any],
) -> dict[str, Any]:
    root = root.resolve()
    stage = root / f".staging-{uuid4().hex}"
    stage.mkdir()
    adjusted = pd.DataFrame({symbol: frames[symbol]["adjusted_close"] for symbol in UNIVERSE})
    adjusted.index.name = "date"
    adjusted.to_parquet(stage / "prices.parquet", engine="pyarrow", compression="zstd", index=True)
    checksum = _sha((stage / "prices.parquet").read_bytes())
    dataset_id = f"historical-{checksum}"
    dates = tuple(str(stamp) for stamp in adjusted.index)
    splits = _split_report(dates)
    metadata = {
        "id": dataset_id,
        "kind": "HISTORICAL",
        "source": SOURCE,
        "sha256": checksum,
        "assets": list(UNIVERSE),
        "start_date": dates[0],
        "end_date": dates[-1],
        "observations": len(dates),
        "provenance": {
            "provider": "Yahoo Finance chart HTTP",
            "retrieved_at": _utc_now(),
            "price_basis": "vendor_adjusted_close",
            "currency": "USD",
            "start_inclusive": START,
            "end_exclusive": PROVIDER_END,
            "parameters": {"interval": "1d", "events": "div,splits", "includeAdjustedClose": True},
            "packages": {
                name: version(name) for name in ("pandas", "numpy", "pyarrow", "exchange-calendars")
            },
            "limitations": LIMITATIONS,
        },
        "quality_report": quality,
        "splits": splits,
    }
    raw_directory = stage / "raw"
    raw_directory.mkdir()
    for symbol in UNIVERSE:
        (raw_directory / f"{symbol}.json").write_bytes(raw_payloads[symbol])
    bars = pd.concat([frames[symbol].assign(symbol=symbol).reset_index() for symbol in UNIVERSE])
    bars.to_parquet(
        stage / "provider-bars.parquet", engine="pyarrow", compression="zstd", index=False
    )
    _write_json(stage / "quality-report.json", quality)
    _write_json(
        stage / "manifest.json",
        {
            "schema_version": 1,
            "metadata": metadata,
            "provider_requests": provenance,
            "files": {
                "prices.parquet": checksum,
                "provider-bars.parquet": _sha((stage / "provider-bars.parquet").read_bytes()),
                "quality-report.json": _sha((stage / "quality-report.json").read_bytes()),
                **{f"raw/{symbol}.json": _sha(raw_payloads[symbol]) for symbol in UNIVERSE},
            },
        },
    )
    destination = root / dataset_id
    if stage.resolve().parent != root or destination.resolve().parent != root:
        raise DataPipelineError("snapshot_path", "Staging/destination must remain within data root")
    if destination.exists():
        # Do not overwrite an immutable snapshot; verify it before reusing.
        existing = load_snapshot(root, dataset_id)
        shutil.rmtree(stage)
        return dict(existing.metadata)
    stage.rename(destination)
    return metadata


def _read_manifest(root: Path, dataset_id: str) -> tuple[Path, dict[str, Any]]:
    if not _ID.fullmatch(dataset_id):
        raise DataPipelineError("invalid_dataset_id", "Historical dataset ID is malformed")
    root = root.resolve()
    directory = (root / dataset_id).resolve()
    if directory.parent != root or not directory.is_dir():
        raise DataPipelineError("snapshot_missing", "Historical snapshot is unavailable")
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        metadata = manifest["metadata"]
        if metadata["id"] != dataset_id or metadata["kind"] != "HISTORICAL":
            raise DataPipelineError("snapshot_identity", "Snapshot manifest identity mismatch")
        if (
            metadata["source"] != SOURCE
            or metadata["provenance"]["provider"] != "Yahoo Finance chart HTTP"
            or metadata["provenance"]["price_basis"] != "vendor_adjusted_close"
            or metadata["provenance"]["currency"] != "USD"
        ):
            raise DataPipelineError("snapshot_provenance", "Snapshot provider identity mismatch")
        if dataset_id != f"historical-{metadata['sha256']}":
            raise DataPipelineError(
                "snapshot_identity", "Snapshot ID does not match its content hash"
            )
        required_files = {"prices.parquet", "provider-bars.parquet", "quality-report.json"}
        required_files.update(f"raw/{symbol}.json" for symbol in UNIVERSE)
        if set(manifest["files"]) != required_files:
            raise DataPipelineError("snapshot_integrity", "Snapshot file manifest is incomplete")
        for relative, checksum in manifest["files"].items():
            path = (directory / relative).resolve()
            if (
                directory not in path.parents
                or not path.is_file()
                or _sha(path.read_bytes()) != checksum
            ):
                raise DataPipelineError(
                    "snapshot_integrity", "Snapshot file hash mismatch or missing file"
                )
        if manifest["files"]["prices.parquet"] != metadata["sha256"]:
            raise DataPipelineError("snapshot_integrity", "Snapshot price hash metadata mismatch")
        if metadata["quality_report"]["status"] != "passed":
            raise DataPipelineError("snapshot_quality", "Snapshot quality report is not passed")
        quality = json.loads((directory / "quality-report.json").read_text(encoding="utf-8"))
        if quality != metadata["quality_report"]:
            raise DataPipelineError(
                "snapshot_quality", "Stored and advertised quality reports differ"
            )
        if set(manifest["provider_requests"]) != set(UNIVERSE):
            raise DataPipelineError("snapshot_provenance", "Provider request manifest incomplete")
        for symbol, info in manifest["provider_requests"].items():
            if (
                info["url"] != _provider_url(symbol)
                or info["http_status"] != 200
                or info["sha256"] != manifest["files"][f"raw/{symbol}.json"]
            ):
                raise DataPipelineError("snapshot_provenance", "Provider request/raw hash mismatch")
            parsed = datetime.fromisoformat(info["fetched_at"].replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise DataPipelineError(
                    "snapshot_provenance", "Provider retrieval time lacks timezone"
                )
        return directory, manifest
    except DataPipelineError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        raise DataPipelineError(
            "snapshot_integrity", "Snapshot manifest cannot be verified"
        ) from None


def list_snapshots(root: Path) -> list[dict[str, Any]]:
    """List only valid registered snapshots; malformed/corrupted entries are rejected."""
    if not root.exists():
        return []
    snapshots = []
    for directory in sorted(root.iterdir()):
        if directory.is_dir() and _ID.fullmatch(directory.name):
            _, manifest = _read_manifest(root, directory.name)
            snapshots.append(manifest["metadata"])
    return snapshots


def load_snapshot(root: Path, dataset_id: str) -> PricePanel:
    """Verify immutable storage hashes and load an adjusted-close research panel."""
    directory, manifest = _read_manifest(root, dataset_id)
    try:
        frame = pd.read_parquet(directory / "prices.parquet", engine="pyarrow")
        metadata = manifest["metadata"]
        dates = tuple(str(stamp) for stamp in frame.index)
        if tuple(frame.columns) != UNIVERSE or metadata["assets"] != list(UNIVERSE):
            raise DataPipelineError("snapshot_universe", "Snapshot universe mismatch")
        if (
            len(frame) != metadata["observations"]
            or dates[0] != metadata["start_date"]
            or dates[-1] != metadata["end_date"]
        ):
            raise DataPipelineError("snapshot_coverage", "Snapshot dates/count metadata mismatch")
        if dates != _expected_sessions() or metadata["splits"] != _split_report(dates):
            raise DataPipelineError(
                "snapshot_coverage", "Snapshot calendar/split metadata mismatch"
            )
        return PricePanel(dates, UNIVERSE, frame.to_numpy(dtype=np.float64), metadata)
    except DataPipelineError:
        raise
    except (OSError, ValueError, TypeError, IndexError):
        raise DataPipelineError("snapshot_integrity", "Snapshot Parquet cannot be loaded") from None
