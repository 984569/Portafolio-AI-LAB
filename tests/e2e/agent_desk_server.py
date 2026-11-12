"""Explicit test-only provider for browser integration; uses the real local snapshot."""

import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "apps/api")]


def main() -> None:
    from agent_desk.provider import MockProvider
    from portfolio_api.main import create_app

    provider = MockProvider(
        {
            "analyst": {
                "trend": "up",
                "regime": "low",
                "evidence": ["market_return", "market_volatility"],
            },
            "judge": {
                "verdict": "approve",
                "reason": "aligned",
                "evidence": ["weights", "portfolio_volatility"],
            },
        }
    )
    uvicorn.run(create_app(desk_provider=provider), host="127.0.0.1", port=8124)


if __name__ == "__main__":
    main()
