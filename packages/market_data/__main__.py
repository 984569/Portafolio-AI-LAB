"""Download the real academic universe; failures never become synthetic data."""

import argparse
import json
from pathlib import Path

from . import DataPipelineError, download_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(".runtime/datasets"))
    args = parser.parse_args()
    try:
        metadata = download_snapshot(args.root)
    except DataPipelineError as exc:
        print(
            json.dumps(
                {"status": "failed", "code": exc.code, "message": str(exc), "report": exc.report},
                indent=2,
            )
        )
        return 1
    print(json.dumps({"status": "completed", "dataset": metadata}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
