"""Immutable validated adjusted-price panel; no provider or temporal split policy."""

from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class PricePanel:
    dates: tuple[str, ...]
    assets: tuple[str, ...]
    prices: NDArray[np.float64]
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        dates, assets = tuple(self.dates), tuple(self.assets)
        if (
            not assets
            or len(set(assets)) != len(assets)
            or any(not isinstance(asset, str) or not asset.strip() for asset in assets)
        ):
            raise ValueError("Asset identifiers must be nonempty and unique")
        if len(dates) < 2:
            raise ValueError("A panel requires at least two dated observations")
        try:
            parsed = [date.fromisoformat(stamp) for stamp in dates]
        except (TypeError, ValueError) as exc:
            raise ValueError("Panel dates must be canonical ISO dates") from exc
        if any(day.isoformat() != stamp for day, stamp in zip(parsed, dates, strict=True)):
            raise ValueError("Panel dates must be canonical ISO dates")
        if any(first >= second for first, second in zip(parsed, parsed[1:], strict=False)):
            raise ValueError("Panel dates must be strictly increasing and unique")
        prices = np.array(self.prices, dtype=np.float64, copy=True)
        if prices.shape != (len(dates), len(assets)):
            raise ValueError("Prices must have one row per date and one column per asset")
        if not np.isfinite(prices).all() or (prices <= 0).any():
            raise ValueError("Prices must be finite and positive")
        prices.flags.writeable = False
        object.__setattr__(self, "dates", dates)
        object.__setattr__(self, "assets", assets)
        object.__setattr__(self, "prices", prices)
        object.__setattr__(self, "metadata", deepcopy(self.metadata))

    @property
    def n_assets(self) -> int:
        return len(self.assets)

    def __len__(self) -> int:
        return len(self.dates)
