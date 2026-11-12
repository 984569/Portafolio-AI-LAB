"""Fixed development folds and exactly aligned out-of-sample observation windows."""

from datetime import date
from typing import Any

from portfolio_core import PricePanel

WALK_FORWARD_FOLDS: tuple[dict[str, str], ...] = (
    {
        "fold_id": "wf_2019",
        "train_start": "2015-01-01",
        "train_end": "2018-12-31",
        "eval_start": "2019-01-01",
        "eval_end": "2019-12-31",
    },
    {
        "fold_id": "wf_2021",
        "train_start": "2015-01-01",
        "train_end": "2020-12-31",
        "eval_start": "2021-01-01",
        "eval_end": "2021-12-31",
    },
)


def canonical_date(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be an ISO date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise ValueError(f"{label} must be an ISO date") from None
    if parsed.isoformat() != value:
        raise ValueError(f"{label} must use YYYY-MM-DD")
    return value


def evaluation_window(panel: PricePanel, start: str, end: str, lookback: int) -> PricePanel:
    """Include exactly W+1 warmup closes, then the requested evaluation closes.

    PortfolioEnv's first execution index is W+1, so the first eligible evaluation
    close is the same one used by the unchanged Stage2 benchmarks. No warmup PnL
    is recorded. End2024 is forbidden even when the source snapshot contains it.
    """
    start, end = canonical_date(start, "start"), canonical_date(end, "end")
    if not "2015-01-01" <= start <= end < "2024-01-01":
        raise ValueError("Evaluation must remain in development history2015–2023")
    if isinstance(lookback, bool) or not isinstance(lookback, int) or not 2 <= lookback <= 252:
        raise ValueError("lookback must be an integer between2 and252")
    eligible = [index for index, stamp in enumerate(panel.dates) if start <= stamp <= end]
    if len(eligible) < 2:
        raise ValueError("Evaluation requires at least two eligible closes")
    first, last = eligible[0], eligible[-1]
    if first < lookback + 1:
        raise ValueError("Evaluation lacks W+1 closes of prior warmup history")
    prefix = first - lookback - 1
    metadata = dict(panel.metadata)
    metadata["evaluation_window"] = {
        "requested_start": start,
        "requested_end": end,
        "first_execution": panel.dates[first],
        "last_valuation": panel.dates[last],
        "warmup_closes": lookback + 1,
    }
    return PricePanel(
        panel.dates[prefix : last + 1], panel.assets, panel.prices[prefix : last + 1], metadata
    )
