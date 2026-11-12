"""Synthetic result artifacts exercise statistics; no claimed market performance."""

import copy

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest
from portfolio_core import financial_metrics
from portfolio_evaluation import (
    WALK_FORWARD_FOLDS,
    extra_metrics,
    paired_block_bootstrap,
    seed_summary,
    select_candidate,
)


def result(
    returns=None,
    *,
    dates=None,
    seed=42,
    strategy="ppo",
    capital=1000,
    lookback=60,
):
    if returns is None:
        returns = np.random.default_rng(81).normal(0.0005, 0.01, size=79)
    returns = np.asarray(returns, dtype=float)
    if dates is None:
        dates = tuple(pd.bdate_range("2022-01-03", periods=len(returns) + 1).strftime("%Y-%m-%d"))
    values = capital * np.cumprod(np.concatenate([[1], 1 + returns]))
    equity = [{"date": dates[0], "equity": float(values[0]), "net_return": 0.0}]
    equity.extend(
        {"date": stamp, "equity": float(value), "net_return": float(net_return)}
        for stamp, value, net_return in zip(dates[1:], values[1:], returns, strict=True)
    )
    return {
        "metrics": financial_metrics(values),
        "equity": equity,
        "allocations": [
            {
                "date": stamp,
                "weights": {"SYNTHETIC_A": 0.5, "SYNTHETIC_B": 0.5},
                "turnover": 1.0 if index == 0 else 0.02,
                "cost": 0.0,
            }
            for index, stamp in enumerate(dates[:-1])
        ],
        "audit": [],
        "manifest": {
            "data_mode": "FIXTURE",
            "configuration": {
                "strategy": strategy,
                "seed": seed,
                "dataset_id": "test-only",
                "lookback": lookback,
                "initial_capital": capital,
                "transaction_cost_bps": 0,
                "risk_free_rate": 0,
            },
        },
    }


def test_extra_metrics_cagr_turnover_weights_have_known_values():
    artifact = result(np.full(252, 0.001))
    extras = extra_metrics(artifact)
    assert extras["annualized_return"] == pytest.approx(1.001**252 - 1)
    assert extras["turnover_total"] == pytest.approx(1 + 251 * 0.02)
    assert extras["turnover_mean"] == pytest.approx((1 + 251 * 0.02) / 252)
    assert extras["transaction_costs"] == 0
    assert extras["weight_distribution"]["SYNTHETIC_A"] == {
        "mean": 0.5,
        "std_across_dates": 0,
        "min": 0.5,
        "max": 0.5,
        "last_target": 0.5,
    }


@pytest.mark.parametrize(
    "case",
    [
        "nonfinite_equity",
        "duplicate_dates",
        "holdout",
        "fake_return",
        "missing_allocation",
        "allocation_date",
        "negative_weight",
        "different_universe",
        "nonfinite_turnover",
        "negative_cost",
    ],
)
def test_inconsistent_statistics_inputs_are_rejected(case):
    artifact = result()
    if case == "nonfinite_equity":
        artifact["equity"][-1]["equity"] = float("nan")
    elif case == "duplicate_dates":
        artifact["equity"][-1]["date"] = artifact["equity"][-2]["date"]
    elif case == "holdout":
        artifact["equity"][-1]["date"] = "2024-01-02"
    elif case == "fake_return":
        artifact["equity"][1]["net_return"] = 0.99
    elif case == "missing_allocation":
        artifact["allocations"].pop()
    elif case == "allocation_date":
        artifact["allocations"][0]["date"] = "2021-12-31"
    elif case == "negative_weight":
        artifact["allocations"][0]["weights"] = {"SYNTHETIC_A": -0.1, "SYNTHETIC_B": 1.1}
    elif case == "different_universe":
        artifact["allocations"][0]["weights"] = {"SYNTHETIC_OTHER": 1}
    elif case == "nonfinite_turnover":
        artifact["allocations"][0]["turnover"] = float("inf")
    else:
        artifact["allocations"][0]["cost"] = -1
    with pytest.raises(ValueError):
        extra_metrics(artifact)


def test_seed_summary_reports_every_seed_and_does_not_select_best():
    first = result(seed=7)
    second = result(np.random.default_rng(123).normal(-0.0001, 0.012, 79), seed=42)
    third = result(np.random.default_rng(321).normal(0.0004, 0.01, 79), seed=123)
    report = seed_summary([first, second, third])
    assert report["seeds"] == [7, 42, 123]
    assert report["n_runs"] == 3
    assert not report["best_seed_selected"]
    expected = [item["metrics"]["cumulative_return"] for item in (first, second, third)]
    assert report["metrics"]["cumulative_return"]["mean"] == pytest.approx(np.mean(expected))
    assert report["metrics"]["cumulative_return"]["std"] == pytest.approx(np.std(expected, ddof=1))
    assert seed_summary([first])["metrics"]["cumulative_return"]["std"] is None


@pytest.mark.parametrize(
    "case", ["empty", "duplicate_seed", "mixed_strategy", "dates", "economics"]
)
def test_seed_summary_cannot_mix_or_cherry_pick_incompatible_runs(case):
    first, second = result(seed=7), result(seed=42)
    if case == "empty":
        inputs = []
    else:
        inputs = [first, second]
        if case == "duplicate_seed":
            second["manifest"]["configuration"]["seed"] = 7
        elif case == "mixed_strategy":
            second["manifest"]["configuration"]["strategy"] = "ddpg"
        elif case == "dates":
            second["equity"][-1]["date"] = "2023-12-29"
        else:
            second["manifest"]["configuration"]["transaction_cost_bps"] = 20
    with pytest.raises(ValueError):
        seed_summary(inputs)


def test_paired_bootstrap_identical_portfolios_zero_interval_reproducible():
    artifact = result()
    report = paired_block_bootstrap(artifact, copy.deepcopy(artifact), seed=17)
    assert report["status"] == "computed"
    assert report["estimate"] == report["lower"] == report["upper"] == 0
    assert report["p_value"] is None
    assert report == paired_block_bootstrap(artifact, artifact, seed=17)
    assert report["limitations"]


def test_paired_bootstrap_known_constant_difference_is_paired_not_independent():
    rng = np.random.default_rng(100)
    base = rng.normal(0.001, 0.01, 79)
    report = paired_block_bootstrap(result(base + 0.001), result(base), seed=9)
    assert report["estimate"] == pytest.approx(0.252, abs=1e-10)
    assert report["lower"] == pytest.approx(0.252, abs=1e-10)
    assert report["upper"] == pytest.approx(0.252, abs=1e-10)
    short = paired_block_bootstrap(result(base[:3]), result(base[:3]))
    assert short["status"] == "insufficient_data"
    assert short["lower"] is None and short["upper"] is None


@pytest.mark.parametrize(
    "fields",
    [
        {"seed": True},
        {"block_length": 0},
        {"block_length": 253},
        {"resamples": 99},
        {"resamples": 10001},
        {"confidence": 1},
        {"confidence": float("nan")},
    ],
)
def test_bootstrap_resource_and_statistic_limits(fields):
    with pytest.raises(ValueError):
        paired_block_bootstrap(result(), result(), **fields)


def test_bootstrap_requires_identical_dates():
    first, second = result(), result()
    second["equity"][-1]["date"] = "2023-12-29"
    with pytest.raises(ValueError, match="dates"):
        paired_block_bootstrap(first, second)


def test_bootstrap_rejects_different_cost_assumptions():
    first, second = result(), result()
    second["manifest"]["configuration"]["transaction_cost_bps"] = 20
    with pytest.raises(ValueError, match="economic"):
        paired_block_bootstrap(first, second)


def test_edited_financial_metric_cannot_enter_comparison_or_selection():
    artifact = result()
    artifact["metrics"]["sharpe_ratio"] = 99
    with pytest.raises(ValueError, match="canonical"):
        paired_block_bootstrap(artifact, result())
    rows = fold_reports()
    rows[0]["result"]["metrics"]["sharpe_ratio"] = 99
    with pytest.raises(ValueError, match="canonical"):
        select_candidate(rows)


def fold_reports(flat=False):
    rows = []
    for fold in WALK_FORWARD_FOLDS:
        calendar = xcals.get_calendar("XNYS", start=fold["eval_start"], end=fold["eval_end"])
        dates = tuple(str(stamp.date()) for stamp in calendar.sessions)
        dates = tuple(stamp for stamp in dates if fold["eval_start"] <= stamp <= fold["eval_end"])
        returns = (
            np.zeros(len(dates) - 1)
            if flat
            else np.random.default_rng(91).normal(0.0001, 0.01, len(dates) - 1)
        )
        for candidate in ("candidate_a", "candidate_b"):
            artifact = result(
                returns + (0.001 if candidate == "candidate_b" and not flat else 0), dates=dates
            )
            artifact["manifest"].update(
                training_end=fold["train_end"],
                requested_evaluation={"start": fold["eval_start"], "end": fold["eval_end"]},
            )
            rows.append({"candidate_id": candidate, "fold_id": fold["fold_id"], "result": artifact})
    return rows


def test_candidate_selection_uses_complete_fixed_development_folds_only():
    selected = select_candidate(fold_reports())
    assert selected["selected_candidate"] == "candidate_b"
    assert selected["selection_metric"] == "mean_predeclared_fold_sharpe"
    assert len(selected["scores"]) == 2
    assert not selected["validation_2022_2023_used"]
    assert not selected["holdout_evaluated"]
    assert select_candidate(fold_reports(flat=True))["selected_candidate"] is None


def test_tied_candidates_use_predeclared_lexicographic_order_not_later_returns():
    rows = fold_reports()
    for fold in WALK_FORWARD_FOLDS:
        same_fold = [row for row in rows if row["fold_id"] == fold["fold_id"]]
        same_fold[1]["result"] = copy.deepcopy(same_fold[0]["result"])
    assert select_candidate(list(reversed(rows)))["selected_candidate"] == "candidate_a"


@pytest.mark.parametrize(
    "case",
    [
        "missing_fold",
        "duplicate_fold",
        "unknown_fold",
        "later_training",
        "2022_selection",
        "partial_fold",
        "different_seed",
        "different_algorithm",
    ],
)
def test_candidate_selection_rejects_incomplete_or_leaking_reports(case):
    rows = fold_reports()
    if case == "missing_fold":
        rows.pop()
    elif case == "duplicate_fold":
        rows.append(copy.deepcopy(rows[0]))
    elif case == "unknown_fold":
        rows[0]["fold_id"] = "validation_2022"
    elif case == "later_training":
        rows[0]["result"]["manifest"]["training_end"] = "2022-12-31"
    elif case == "2022_selection":
        rows[0]["result"]["manifest"]["requested_evaluation"]["end"] = "2022-12-31"
    elif case == "partial_fold":
        artifact = rows[0]["result"]
        artifact["equity"] = artifact["equity"][:30]
        artifact["allocations"] = artifact["allocations"][:29]
    elif case == "different_seed":
        rows[0]["result"]["manifest"]["configuration"]["seed"] = 17
    else:
        rows[0]["result"]["manifest"]["configuration"]["strategy"] = "ddpg"
    with pytest.raises(ValueError):
        select_candidate(rows)
