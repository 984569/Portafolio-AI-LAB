"""Offline synthetic provider responses test ingestion; never used as market data."""

import copy
import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from market_data import (
    DataPipelineError,
    download_snapshot,
    list_snapshots,
    load_snapshot,
    pipeline,
)


@pytest.fixture(scope="module")
def dates():
    return pipeline._expected_sessions()


def chart_payload(symbol, dates):
    timestamps = [
        int(pd.Timestamp(f"{stamp}T16:00:00", tz="America/New_York").timestamp()) for stamp in dates
    ]
    size = len(dates)
    return {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {"symbol": symbol, "currency": "USD"},
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0] * size,
                                "high": [101.0] * size,
                                "low": [99.0] * size,
                                "close": [100.0] * size,
                                "volume": [1000] * size,
                            }
                        ],
                        "adjclose": [{"adjclose": [90.0] * size}],
                    },
                    "events": {},
                }
            ],
        }
    }


@pytest.fixture(scope="module")
def payloads(dates):
    return {
        symbol: json.dumps(chart_payload(symbol, dates)).encode() for symbol in pipeline.UNIVERSE
    }


@pytest.fixture(scope="module")
def frames(payloads):
    return {symbol: pipeline._normalize_chart(symbol, raw) for symbol, raw in payloads.items()}


def test_academic_calendar_and_splits_are_exact_and_disjoint(dates):
    assert dates[0] == "2015-01-02"
    assert dates[-1] == "2024-12-31"
    assert len(dates) == 2516
    assert "2022-06-20" not in dates  # Juneteenth exchange holiday.
    splits = pipeline._split_report(dates)
    assert splits["train"]["end_date"] == "2021-12-31"
    assert splits["validation"]["start_date"] == "2022-01-03"
    assert splits["validation"]["end_date"] == "2023-12-29"
    assert splits["final_test"]["start_date"] == "2024-01-02"
    assert splits["final_test"]["locked"] is True
    assert sum(split["observations"] for split in splits.values()) == len(dates)


def test_provider_normalization_retains_adjusted_close_and_actions():
    payload = chart_payload("AAPL", ["2020-08-28", "2020-08-31"])
    result = payload["chart"]["result"][0]
    stamp = result["timestamp"][1]
    result["events"] = {
        "dividends": {"d": {"date": stamp, "amount": 0.2}},
        "splits": {"s": {"date": stamp, "numerator": 4.0, "denominator": 1.0}},
    }
    frame = pipeline._normalize_chart("AAPL", json.dumps(payload).encode())
    assert frame.loc["2020-08-31", "dividends"] == 0.2
    assert frame.loc["2020-08-31", "stock_splits"] == 4
    assert frame["adjusted_close"].tolist() == [90, 90]
    assert frame["close"].tolist() == [100, 100]


@pytest.mark.parametrize(
    "mutation,code",
    [
        (lambda result: result["meta"].update(currency="EUR"), "provider_identity_error"),
        (lambda result: result["meta"].update(symbol="WRONG"), "provider_identity_error"),
        (lambda result: result["indicators"].pop("adjclose"), "invalid_provider_schema"),
        (lambda result: result["indicators"]["quote"][0]["close"].pop(), "provider_shape_error"),
        (
            lambda result: result["indicators"]["quote"][0]["close"].__setitem__(0, None),
            "invalid_provider_data",
        ),
        (
            lambda result: result["indicators"]["quote"][0]["open"].__setitem__(0, 0),
            "invalid_provider_data",
        ),
        (
            lambda result: result["timestamp"].__setitem__(1, result["timestamp"][0]),
            "duplicate_sessions",
        ),
        (lambda result: result["timestamp"].reverse(), "unsorted_sessions"),
    ],
)
def test_corrupt_provider_data_fails_closed(mutation, code):
    payload = chart_payload("AAPL", ["2015-01-02", "2015-01-05"])
    mutation(payload["chart"]["result"][0])
    with pytest.raises(DataPipelineError) as caught:
        pipeline._normalize_chart("AAPL", json.dumps(payload).encode())
    assert caught.value.code == code


@pytest.mark.parametrize("value", [-1, None, float("inf"), True])
def test_invalid_corporate_action_is_not_replaced_with_zero(value):
    payload = chart_payload("AAPL", ["2015-01-02", "2015-01-05"])
    result = payload["chart"]["result"][0]
    result["events"] = {"dividends": {"d": {"date": result["timestamp"][0], "amount": value}}}
    with pytest.raises(DataPipelineError):
        pipeline._normalize_chart("AAPL", json.dumps(payload).encode())


def test_missing_day_is_reported_instead_of_forward_filled(frames):
    changed = {**frames, "AAPL": frames["AAPL"].drop("2020-01-02")}
    with pytest.raises(DataPipelineError) as caught:
        pipeline._validate_frames(changed)
    assert caught.value.code == "calendar_coverage"
    assert caught.value.report["missing_sessions"] == ["2020-01-02"]
    assert len(changed["AAPL"]) == 2515


@pytest.mark.parametrize(
    "case,code",
    [
        ("duplicate", "duplicate_sessions"),
        ("unsorted", "unsorted_sessions"),
        ("invalid_price", "invalid_prices"),
        ("missing_price", "invalid_prices"),
        ("invalid_volume", "invalid_actions"),
        ("invalid_ohlc", "invalid_ohlc"),
        ("holiday", "calendar_coverage"),
        ("column", "missing_columns"),
    ],
)
def test_quality_failures_are_explicit(frames, case, code):
    frame = frames["AAPL"].copy()
    if case == "duplicate":
        frame = pd.concat([frame, frame.iloc[:1]])
    elif case == "unsorted":
        frame = frame.iloc[::-1]
    elif case == "invalid_price":
        frame.loc["2020-01-02", "close"] = -1
    elif case == "missing_price":
        frame.loc["2020-01-02", "adjusted_close"] = np.nan
    elif case == "invalid_volume":
        frame.loc["2020-01-02", "volume"] = -1
    elif case == "invalid_ohlc":
        frame.loc["2020-01-02", "high"] = 98
    elif case == "holiday":
        frame.loc["2020-01-01"] = frame.iloc[0]
        frame = frame.sort_index()
    else:
        frame = frame.drop(columns="dividends")
    with pytest.raises(DataPipelineError) as caught:
        pipeline._validate_frames({**frames, "AAPL": frame})
    assert caught.value.code == code


def test_incomplete_universe_rejected(frames):
    with pytest.raises(DataPipelineError, match="ten"):
        pipeline._validate_frames(
            {symbol: frame for symbol, frame in frames.items() if symbol != "GLD"}
        )


def install_provider(monkeypatch, payloads):
    calls = []

    def fetch(symbol):
        calls.append(symbol)
        raw = payloads[symbol]
        return raw, {
            "symbol": symbol,
            "url": pipeline._provider_url(symbol),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "fetched_at": "2026-11-10T00:00:00Z",
            "http_status": 200,
            "duration_seconds": 0,
        }

    monkeypatch.setattr(pipeline, "_fetch_chart", fetch)
    return calls


def test_snapshot_roundtrip_exact_raw_bytes_hashes_and_reproducibility(
    tmp_path, monkeypatch, payloads
):
    calls = install_provider(monkeypatch, payloads)
    metadata = download_snapshot(tmp_path)
    assert set(calls) == set(pipeline.UNIVERSE)
    assert metadata["kind"] == "HISTORICAL"
    assert metadata["id"] == "historical-" + metadata["sha256"]
    assert metadata["quality_report"]["status"] == "passed"
    assert metadata["observations"] == 2516
    panel = load_snapshot(tmp_path, metadata["id"])
    assert panel.assets == pipeline.UNIVERSE
    assert panel.prices.shape == (2516, 10)
    assert not panel.prices.flags.writeable
    assert (tmp_path / metadata["id"] / "raw/AAPL.json").read_bytes() == payloads["AAPL"]
    assert list_snapshots(tmp_path) == [metadata]
    again = download_snapshot(tmp_path)
    assert again == metadata
    assert len(calls) == 10  # All later requests reuse verified originals, not new network.
    assert not list(tmp_path.glob(".staging-*"))


@pytest.mark.parametrize(
    "relative", ["prices.parquet", "provider-bars.parquet", "raw/MSFT.json", "quality-report.json"]
)
def test_tampered_snapshot_fails_integrity(tmp_path, monkeypatch, payloads, relative):
    install_provider(monkeypatch, payloads)
    metadata = download_snapshot(tmp_path)
    path = tmp_path / metadata["id"] / relative
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(DataPipelineError) as caught:
        load_snapshot(tmp_path, metadata["id"])
    assert caught.value.code == "snapshot_integrity"


def test_provider_failure_preserves_progress_and_never_registers_snapshot(
    tmp_path, monkeypatch, payloads
):
    fetch = install_provider(monkeypatch, payloads)
    original = pipeline._fetch_chart

    def unavailable(symbol):
        if symbol == "GLD":
            raise DataPipelineError(
                "provider_http_error", "GLD: Yahoo HTTP 429", {"http_status": 429}
            )
        return original(symbol)

    monkeypatch.setattr(pipeline, "_fetch_chart", unavailable)
    with pytest.raises(DataPipelineError) as caught:
        download_snapshot(tmp_path)
    assert caught.value.code == "download_incomplete"
    assert list_snapshots(tmp_path) == []
    assert len(fetch) == 9
    progress = json.loads((tmp_path / "download-progress.json").read_text())
    assert progress["status"] == "failed"
    assert progress["symbols"]["GLD"]["http_status"] == 429
    assert (tmp_path / "provider-cache/AAPL.json").exists()


@pytest.mark.parametrize(
    "dataset_id", ["../outside", "historical-../outside", "fixture-v1", "historical-zzzz"]
)
def test_dataset_paths_cannot_escape_root(tmp_path, dataset_id):
    with pytest.raises(DataPipelineError) as caught:
        load_snapshot(tmp_path, dataset_id)
    assert caught.value.code == "invalid_dataset_id"


def test_request_cache_hash_is_checked_before_reuse(tmp_path, monkeypatch, payloads):
    calls = install_provider(monkeypatch, payloads)
    download_snapshot(tmp_path)
    path = tmp_path / "provider-cache/AAPL.json"
    path.write_bytes(b"unexpected replacement")
    with pytest.raises(DataPipelineError) as caught:
        download_snapshot(tmp_path)
    assert caught.value.report["symbols"]["AAPL"]["code"] == "cache_integrity"
    assert len(calls) == 10  # Corruption is rejected, not silently overwritten.


@pytest.mark.parametrize("case", ["path", "provider", "request", "quality"])
def test_manifest_path_and_provenance_tampering_rejected(tmp_path, monkeypatch, payloads, case):
    install_provider(monkeypatch, payloads)
    metadata = download_snapshot(tmp_path)
    path = tmp_path / metadata["id"] / "manifest.json"
    manifest = json.loads(path.read_text())
    corrupted = copy.deepcopy(manifest)
    if case == "path":
        corrupted["files"]["../../outside"] = "0" * 64
    elif case == "provider":
        corrupted["metadata"]["provenance"]["provider"] = "unverified replacement"
    elif case == "request":
        corrupted["provider_requests"]["AAPL"]["sha256"] = "0" * 64
    else:
        corrupted["metadata"]["quality_report"]["observations"] = 1
    path.write_text(json.dumps(corrupted))
    with pytest.raises(DataPipelineError):
        load_snapshot(tmp_path, metadata["id"])


def test_empty_registry_is_not_a_synthetic_dataset(tmp_path):
    assert list_snapshots(tmp_path / "absent") == []
    assert list_snapshots(tmp_path) == []


def test_incomplete_cache_is_not_overwritten_with_a_new_download(tmp_path, monkeypatch):
    cache = tmp_path / "provider-cache"
    cache.mkdir()
    (cache / "AAPL.json").write_bytes(b"original incomplete response")

    def forbidden(_symbol):
        pytest.fail("Incomplete cache must be rejected before any new provider request")

    monkeypatch.setattr(pipeline, "_fetch_chart", forbidden)
    with pytest.raises(DataPipelineError) as caught:
        pipeline._cache_payload(tmp_path, "AAPL")
    assert caught.value.code == "cache_integrity"
