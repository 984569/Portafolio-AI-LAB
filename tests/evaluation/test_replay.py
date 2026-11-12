"""Explicit synthetic prices test evaluation clocks and unchanged benchmark parity."""

from typing import Any

import numpy as np
import pandas as pd
import pytest
from portfolio_core import PricePanel
from portfolio_evaluation import (
    evaluate_baseline_window,
    evaluate_policy,
    evaluation_window,
)


@pytest.fixture
def synthetic_panel() -> PricePanel:
    dates = tuple(pd.bdate_range("2021-11-01", "2024-01-05").strftime("%Y-%m-%d"))
    generator = np.random.default_rng(137)
    prices = 100 * np.exp(np.cumsum(generator.normal(0.0003, 0.012, (len(dates), 2)), axis=0))
    return PricePanel(
        dates,
        ("SYNTHETIC_A", "SYNTHETIC_B"),
        prices,
        {"id": "evaluation-test-fixture", "kind": "FIXTURE", "sha256": "test-only-not-market"},
    )


def config(strategy: str = "ppo", **updates: Any) -> dict[str, Any]:
    return {
        "name": "Offline evaluation test",
        "strategy": strategy,
        "lookback": 5,
        "seed": 42,
        "initial_capital": 1000,
        "transaction_cost_bps": 10,
        **updates,
    }


def equal_policy(_observation: np.ndarray) -> np.ndarray:
    return np.zeros(2, dtype=np.float32)


def test_window_warmup_aligns_first_execution_without_warmup_pnl(synthetic_panel):
    window = evaluation_window(synthetic_panel, "2022-01-01", "2023-12-31", 5)
    assert window.dates[6] == "2022-01-03"
    assert window.dates[-1] == "2023-12-29"
    assert window.metadata["evaluation_window"]["warmup_closes"] == 6
    assert not window.prices.flags.writeable
    assert "evaluation_window" not in synthetic_panel.metadata


def test_zero_actions_match_unchanged_equal_weight_dates_fees_and_equity(synthetic_panel):
    policy = evaluate_policy(synthetic_panel, equal_policy, config(), train_end="2021-12-31")
    baseline = evaluate_baseline_window(
        synthetic_panel, config("equal_weight"), eval_start="2022-01-01", eval_end="2023-12-31"
    )
    assert policy["equity"] == baseline["equity"]
    assert policy["allocations"] == baseline["allocations"]
    assert policy["metrics"] == baseline["metrics"]
    assert policy["manifest"]["evaluation"]["intervals"] == len(policy["equity"]) - 1
    assert not policy["manifest"]["evaluation"]["holdout_evaluated"]
    assert policy["manifest"]["research_metrics"]["turnover_total"] > 0
    assert set(policy) == {"metrics", "equity", "allocations", "audit", "manifest"}


def test_reward_net_log_growth_does_not_subtract_fees_twice(synthetic_panel):
    result = evaluate_policy(synthetic_panel, equal_policy, config(), train_end="2021-12-31")
    reward_sum = result["manifest"]["learning_evaluation"]["reward_sum"]
    assert reward_sum == pytest.approx(np.log(result["metrics"]["final_equity"] / 1000))
    assert result["metrics"]["total_costs"] == pytest.approx(
        sum(allocation["cost"] for allocation in result["allocations"])
    )


def test_predictor_receives_raw_lagged_observation_and_cannot_mutate_state(synthetic_panel):
    observed = []

    def mutating_predictor(observation):
        observed.append(observation.copy())
        observation[:] = 99
        return equal_policy(observation)

    actual = evaluate_policy(synthetic_panel, mutating_predictor, config(), train_end="2021-12-31")
    expected = evaluate_policy(synthetic_panel, equal_policy, config(), train_end="2021-12-31")
    assert actual == expected
    assert observed[0].dtype == np.float32
    assert observed[0].shape == (12,)
    assert np.max(np.abs(observed[0][:10])) < 0.1
    assert observed[0][-2:].tolist() == [0, 0]


def test_future_prices_do_not_change_same_execution_or_prior_targets(synthetic_panel):
    def lagged_predictor(observation):
        return np.tanh(observation[:2] * 10).astype(np.float32)

    cut = synthetic_panel.dates.index("2022-06-01")
    prices = synthetic_panel.prices.copy()
    prices[cut:] *= np.array([2.0, 0.5])
    alternate = PricePanel(
        synthetic_panel.dates, synthetic_panel.assets, prices, synthetic_panel.metadata
    )
    first = evaluate_policy(synthetic_panel, lagged_predictor, config(), train_end="2021-12-31")
    second = evaluate_policy(alternate, lagged_predictor, config(), train_end="2021-12-31")
    for before, after in zip(first["allocations"], second["allocations"], strict=True):
        if before["date"] <= "2022-06-01":
            assert before["weights"] == after["weights"]
    assert [point for point in first["equity"] if point["date"] < "2022-06-01"] == [
        point for point in second["equity"] if point["date"] < "2022-06-01"
    ]


def test_2024_changes_cannot_change_validation_outputs(synthetic_panel):
    prices = synthetic_panel.prices.copy()
    prices[np.asarray(synthetic_panel.dates) >= "2024-01-01"] *= np.array([20.0, 0.1])
    alternate = PricePanel(
        synthetic_panel.dates, synthetic_panel.assets, prices, synthetic_panel.metadata
    )
    first = evaluate_policy(synthetic_panel, equal_policy, config(), train_end="2021-12-31")
    assert first == evaluate_policy(alternate, equal_policy, config(), train_end="2021-12-31")


@pytest.mark.parametrize(
    "start,end,lookback",
    [
        ("2024-01-01", "2024-12-31", 5),
        ("2022-01-01", "2024-01-01", 5),
        ("2023-01-01", "2022-01-01", 5),
        ("20220101", "2023-12-31", 5),
        ("2021-11-01", "2021-12-31", 5),
        ("2022-01-01", "2023-12-31", True),
        ("2022-01-01", "2023-12-31", 253),
        ("2023-12-29", "2023-12-29", 5),
    ],
)
def test_invalid_or_holdout_window_rejected(synthetic_panel, start, end, lookback):
    with pytest.raises(ValueError):
        evaluation_window(synthetic_panel, start, end, lookback)


@pytest.mark.parametrize(
    "train_end,eval_start",
    [
        ("2022-01-01", "2023-01-01"),
        ("2024-01-01", "2024-01-02"),
        ("2021-12-31", "2021-12-01"),
        ("2021-12-31", "2021-12-31"),
    ],
)
def test_evaluation_cannot_overlap_training(synthetic_panel, train_end, eval_start):
    with pytest.raises(ValueError):
        evaluate_policy(
            synthetic_panel, equal_policy, config(), train_end=train_end, eval_start=eval_start
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"initial_capital": 0},
        {"initial_capital": float("nan")},
        {"lookback": 1},
        {"seed": True},
        {"seed": -1},
        {"transaction_cost_bps": 101},
        {"risk_free_rate": -1},
        {"reward_mode": "unknown"},
        {"risk_penalty": -1},
        {"dataset_id": "not-the-panel"},
        {"split": "final_test"},
    ],
)
def test_invalid_policy_configuration_fails_closed(synthetic_panel, updates):
    with pytest.raises(ValueError):
        evaluate_policy(synthetic_panel, equal_policy, config(**updates), train_end="2021-12-31")


def test_invalid_action_not_presented_as_successful_evaluation(synthetic_panel):
    with pytest.raises(ValueError, match="Box"):
        evaluate_policy(
            synthetic_panel,
            lambda observation: np.array([10, 0], dtype=np.float32),
            config(),
            train_end="2021-12-31",
        )


def test_baseline_cannot_mix_training_and_validation_window(synthetic_panel):
    with pytest.raises(ValueError, match="cross"):
        evaluate_baseline_window(
            synthetic_panel,
            config("equal_weight"),
            eval_start="2021-12-01",
            eval_end="2022-12-31",
        )
