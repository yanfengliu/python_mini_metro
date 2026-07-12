# Initial overdue-passenger threshold baseline

Purpose: directional evidence for the smallest correction to the one-overdue-passenger game-over cliff. This is not a final balance benchmark.

Environment: current baseline commit `7d5304ad79b6054f85a1c48f3c1bc0b2475bf9fd`, `py313`, seeds `0..11`, one non-looping route through initial stations `[0, 1, 2]`, no further actions, deterministic 60 Hz cadence `(17, 17, 16)` milliseconds, and a five-simulated-minute safety horizon of 18,000 updates.

Reproduction command from the repository root:

```powershell
@'
import statistics
import sys

sys.path.insert(0, "src")

from env import MiniMetroEnv

for threshold in (1, 2, 3):
    rows = []
    for seed in range(12):
        env = MiniMetroEnv()
        env.reset(seed=seed)
        env.mediator.max_waiting_passengers = threshold
        _, _, done, _ = env.step(
            {"type": "create_path", "stations": [0, 1, 2], "loop": False},
            dt_ms=0,
        )
        step = 0
        while not done and step < 18_000:
            _, _, done, _ = env.step(
                {"type": "noop"},
                dt_ms=(17, 17, 16)[step % 3],
            )
            step += 1
        rows.append(
            (
                env.mediator.total_travels_handled,
                env.mediator.time_ms / 1000,
                done,
            )
        )
    deliveries = [row[0] for row in rows]
    durations = [row[1] for row in rows]
    print({
        "threshold": threshold,
        "seeds": len(rows),
        "game_overs": sum(row[2] for row in rows),
        "median_deliveries": statistics.median(deliveries),
        "mean_deliveries": round(statistics.fmean(deliveries), 2),
        "median_seconds": round(statistics.median(durations), 2),
        "mean_seconds": round(statistics.fmean(durations), 2),
        "min_max_deliveries": (min(deliveries), max(deliveries)),
    })
'@ | C:\Users\38909\miniconda3\envs\py313\python.exe -u -
```

Independently reproduced output:

```text
{'threshold': 1, 'seeds': 12, 'game_overs': 12, 'median_deliveries': 16.0, 'mean_deliveries': 16.42, 'median_seconds': 95.47, 'mean_seconds': 95.82, 'min_max_deliveries': (14, 18)}
{'threshold': 2, 'seeds': 12, 'game_overs': 12, 'median_deliveries': 19.5, 'mean_deliveries': 18.5, 'median_seconds': 108.15, 'mean_seconds': 107.39, 'min_max_deliveries': (15, 21)}
{'threshold': 3, 'seeds': 12, 'game_overs': 12, 'median_deliveries': 22.5, 'mean_deliveries': 20.75, 'median_seconds': 118.61, 'mean_seconds': 119.26, 'min_max_deliveries': (15, 24)}
```

Interpretation: threshold two is the minimum tested change that removes single-passenger failure, raises median delivery and survival outcomes, and still ends every scripted run naturally. The fixed route does not exercise human rerouting, fleet management, later progression, or learned policy behavior; GM-11 must retest the final game before balance promotion.

## GM-01c candidate verification

The same command was rerun after making threshold `2` the repository default, with the assignment changed to the canonical `overdue_passenger_threshold` field. All three 12-seed aggregates reproduced exactly. A second 12-seed pass omitted the threshold assignment entirely and compared each final `(deliveries, simulated seconds, game-over flag, update count)` tuple with the explicit-threshold-2 row; all 12 matched.

```text
{'threshold': 1, 'seeds': 12, 'game_overs': 12, 'median_deliveries': 16.0, 'mean_deliveries': 16.42, 'median_seconds': 95.47, 'mean_seconds': 95.82, 'min_max_deliveries': (14, 18)}
{'threshold': 2, 'seeds': 12, 'game_overs': 12, 'median_deliveries': 19.5, 'mean_deliveries': 18.5, 'median_seconds': 108.15, 'mean_seconds': 107.39, 'min_max_deliveries': (15, 21)}
{'threshold': 3, 'seeds': 12, 'game_overs': 12, 'median_deliveries': 22.5, 'mean_deliveries': 20.75, 'median_seconds': 118.61, 'mean_seconds': 119.26, 'min_max_deliveries': (15, 24)}
{'default_threshold': 2, 'matches_explicit_two': True, 'matching_seeds': 12, 'seeds': 12}
```

This confirms implementation equivalence and the original directional comparison; it does not broaden the balance claim beyond the fixed scripted route.
