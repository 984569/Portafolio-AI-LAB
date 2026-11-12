"""Chronological policy evaluation and bounded research comparisons."""

from .replay import evaluate_baseline_window, evaluate_policy
from .statistics import extra_metrics, paired_block_bootstrap, seed_summary, select_candidate
from .temporal import WALK_FORWARD_FOLDS, evaluation_window

__all__ = [
    "WALK_FORWARD_FOLDS",
    "evaluate_baseline_window",
    "evaluate_policy",
    "evaluation_window",
    "extra_metrics",
    "paired_block_bootstrap",
    "seed_summary",
    "select_candidate",
]
