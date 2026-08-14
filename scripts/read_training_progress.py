"""Read training curves straight from TensorBoard event files.

Training stdout is often buffered or lost, but the event files are written
continuously, so this reads progress from disk without touching a live run.
"""

from __future__ import annotations

import argparse
from pathlib import Path

TAGS = ("rollout/ep_rew_mean", "rollout/ep_len_mean", "eval/mean_reward", "time/fps")


def read_run(run_dir: Path) -> dict[str, list[tuple[int, float]]]:
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    series: dict[str, list[tuple[int, float]]] = {}
    for events in sorted(run_dir.rglob("events.out.tfevents.*")):
        accumulator = EventAccumulator(str(events.parent))
        accumulator.Reload()
        for tag in accumulator.Tags().get("scalars", []):
            if tag in TAGS:
                series.setdefault(tag, []).extend(
                    (scalar.step, scalar.value) for scalar in accumulator.Scalars(tag)
                )
    return {tag: sorted(points) for tag, points in series.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dirs", nargs="+", type=Path)
    parser.add_argument("--last", type=int, default=6)
    args = parser.parse_args(argv)

    for run_dir in args.run_dirs:
        series = read_run(run_dir)
        steps = max((points[-1][0] for points in series.values() if points), default=0)
        print(f"\n=== {run_dir}  (latest step {steps:,}) ===")
        if not series:
            print("  no scalars yet")
            continue
        for tag in TAGS:
            points = series.get(tag)
            if not points:
                continue
            tail = points[-args.last :]
            rendered = "  ".join(f"{step:>8,}:{value:>9.2f}" for step, value in tail)
            print(f"  {tag:22} {rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
