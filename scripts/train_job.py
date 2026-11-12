"""One resource-bounded subprocess training request; never runs in an HTTP handler."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))


def main() -> None:
    from market_data import load_snapshot
    from portfolio_core import PricePanel
    from portfolio_rl.common import write_json
    from portfolio_rl.config import TrainingConfig
    from portfolio_rl.ddpg import train_ddpg
    from portfolio_rl.ppo import train_ppo

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, type=Path)
    args = parser.parse_args()
    request = json.loads(args.request.read_text(encoding="utf-8"))
    config = TrainingConfig.model_validate(request["config"])
    output = Path(request["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    panel = load_snapshot(Path(request["data_root"]), config.dataset_id)
    indices = [i for i, stamp in enumerate(panel.dates) if stamp <= config.training_end]
    training = PricePanel(
        tuple(panel.dates[i] for i in indices), panel.assets, panel.prices[indices], panel.metadata
    )

    def progress(value: dict) -> None:
        write_json(output / "progress.json", value)
        with (output / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, allow_nan=False) + "\n")

    trainer = train_ppo if config.algorithm == "ppo" else train_ddpg
    result = trainer(
        training,
        config,
        output,
        progress=progress,
        cancelled=lambda: (output / "cancel.requested").exists(),
        resume_from=Path(request["resume_from"]) if request.get("resume_from") else None,
    )
    write_json(output / "outcome.json", {"status": result["status"]})


if __name__ == "__main__":
    main()
