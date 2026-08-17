"""Score several players on identical seeds and report the paired difference.

Every number this project has had to retract was retracted for one of two
reasons: too few episodes, or arms measured on different boards. The delivery
distribution spans roughly 110 to 800, so five episodes have a minimum
detectable effect near +/-190 -- larger than the entire gap between the scripted
heuristic and a policy that cannot see. A "new best" chosen that way is a
lottery ticket, and several were.

So this harness does three things and refuses to do anything else:

* **Paired.** Every arm plays the same seeds. The statistic is the per-seed
  difference, whose standard deviation is far below the per-episode one because
  board luck cancels.
* **Powered.** It prints the minimum detectable effect for the n actually run,
  beside the result, always. A gap smaller than the MDE is reported as "not
  distinguishable", never as a win.
* **Parallel.** An episode is ~7,600 simulation decisions and about 11 seconds,
  so n=200 across three arms is 110 minutes on one core and about four on
  thirty-two. Power that costs an afternoon does not get run.

Players are named on the command line:

    heuristic   the scripted policy in `rl.heuristic` -- the bar
    wait        never acts; what the simulation scores by itself
    random      uniform over legal actions
    defer       the gate's DEFER action, which must equal `heuristic` exactly
    model:PATH  a saved MaskablePPO/PPO policy, sampled or greedy
    variant:NAME  a one-rule change to the heuristic, from
                  `scripts/heuristic_variants.py` -- the headroom probe

`defer` exists as a self-check: it goes through the learned-policy plumbing but
must return the heuristic's score to the delivery, so a non-zero gap means the
gate or the wrapper is broken rather than the policy being good.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

# 95% normal quantile. The paired difference is a mean over independent seeds,
# so the CLT applies to it even though a single episode is bimodal.
Z95 = 1.959963985

# The 80%-power minimum detectable effect, z(0.975) + z(0.80). This is what
# `blind_control.py` and the MDE(80%) column of `docs/rl-experiments.md` have
# always meant by MDE, and it is 1.43x the half-width of the 95% interval --
# an effect between those two is significant and under-powered at the same
# time. Reporting the interval under the name MDE understated the bar in the
# very harness built to stop under-powered claims.
MDE80 = 2.801585

_MODEL_CACHE: dict[str, object] = {}


def _load_model(path: str):
    """Load once per worker process; SB3 load is slow and the pool is reused."""
    if path not in _MODEL_CACHE:
        from rl.dependencies import require_rl_dependencies

        require_rl_dependencies()
        from sb3_contrib import MaskablePPO

        _MODEL_CACHE[path] = MaskablePPO.load(path, device="cpu")
    return _MODEL_CACHE[path]


def _make_env(spec: dict):
    from rl.event_gate import EventGatedSemanticEnv
    from rl.semantic_env import SemanticMetroEnv

    if spec["gated"]:
        return EventGatedSemanticEnv(
            defer=spec["defer"],
            proposal_features=spec["proposal"],
            wait_backstop=spec["backstop"],
            deviation_scope=spec["scope"],
            max_decisions=spec["max_decisions"],
        )
    return SemanticMetroEnv(max_decisions=spec["max_decisions"])


def _masks(env) -> np.ndarray:
    return env.action_masks()


def play(arm: str, seed: int, spec: dict) -> dict:
    """One episode of one player on one board."""
    from rl.heuristic import choose
    from rl.semantic_env import ACTION_TABLE

    env = _make_env(spec)
    obs, _ = env.reset(seed=seed)
    inner = getattr(env, "inner", env)
    # Seeded from the arm's NAME BYTES, not `hash(arm)`: `hash` on a str is
    # salted by PYTHONHASHSEED, every pool worker is a fresh interpreter
    # under Windows spawn, and the same (arm, seed) therefore drew a
    # different stream in every worker and every rerun. Measured: five
    # distinct salts inside one run.
    rng = np.random.default_rng(
        (seed << 8) ^ (int.from_bytes(arm.encode(), "little") & 0xFF)
    )
    model = _load_model(arm[len("model:") :]) if arm.startswith("model:") else None
    variant = None
    if arm.startswith("variant:"):
        from heuristic_variants import VARIANTS

        name = arm[len("variant:") :]
        if name.startswith("learned"):
            # `variant:learned` or `variant:learned:<path>` -- the weights
            # `learn_end_rule.py` settled on, played through the same
            # harness as every other arm.
            from heuristic_variants import load_learned

            _, _, where = name.partition(":")
            variant = load_learned(where or "output/endrule/best.json")
        elif name not in VARIANTS:
            raise ValueError(
                f"unknown variant {name!r}; scripts/heuristic_variants.py defines "
                f"{sorted(VARIANTS)}"
            )
        else:
            variant = VARIANTS[name]
    total = 0.0
    queries = 0
    deviations = 0
    actions: list[tuple[int, int]] = []
    try:
        while True:
            mask = _masks(env)
            if arm == "heuristic":
                action = choose(inner)
            elif variant is not None:
                action = variant(inner)
            elif arm == "wait":
                action = 0
            elif arm == "random":
                # Uniform over the legal TABLE, never over DEFER. DEFER is
                # appended to the mask, so sampling the mask made the null
                # play the scripted heuristic -- measured at 24% of decisions
                # under scope=all and 92% under scope=kind, where the offered
                # set is about two entries. A null that plays the bar is not
                # a null.
                table = mask[: len(ACTION_TABLE)]
                action = int(rng.choice(np.flatnonzero(table)))
            elif arm == "defer":
                action = env.DEFER
            elif model is not None:
                action, _ = model.predict(
                    obs, action_masks=mask, deterministic=spec["deterministic"]
                )
                action = int(np.asarray(action).ravel()[0])
            else:
                raise ValueError(
                    f"unknown player {arm!r}; expected one of heuristic, wait, "
                    "random, defer, or model:<path-to-a-saved-policy>"
                )
            if action != 0:
                actions.append((int(getattr(env, "decisions", queries)), int(action)))
            obs, reward, terminated, truncated, info = env.step(action)
            deviations += int(info.get("deviated", False))
            total += float(reward)
            queries += 1
            if terminated or truncated:
                break
    finally:
        env.close()
    return {
        "arm": arm,
        "seed": seed,
        "score": total,
        # Persisted per seed, not just averaged. An equivalence claim is
        # about the trajectory, and a dump of scores alone cannot check one.
        "actions": actions,
        "queries": queries,
        "deviations": deviations,
        "decisions": getattr(env, "decisions", queries),
    }


def _work(job):
    arm, seed, spec = job
    return play(arm, seed, spec)


def summarise(scores: dict[str, dict[int, float]], reference: str, seeds) -> list[dict]:
    """Paired statistics against `reference`, with the MDE stated."""
    rows = []
    base = np.array([scores[reference][s] for s in seeds], dtype=float)
    for arm, per_seed in scores.items():
        values = np.array([per_seed[s] for s in seeds], dtype=float)
        diff = values - base
        n = len(seeds)
        sd = float(np.std(values, ddof=1)) if n > 1 else 0.0
        diff_sd = float(np.std(diff, ddof=1)) if n > 1 else 0.0
        half = Z95 * diff_sd / math.sqrt(n) if n > 1 else float("inf")
        rows.append(
            {
                "arm": arm,
                "n": n,
                "mean": float(values.mean()),
                "sd": sd,
                "vs_reference": float(diff.mean()),
                "ci95": half,
                # The smallest true paired gap this n could detect 80% of the
                # time -- NOT the interval half-width, which is 1.43x smaller.
                "mde": MDE80 * diff_sd / math.sqrt(n) if n > 1 else float("inf"),
                "won": int(np.sum(diff > 0)),
                "lost": int(np.sum(diff < 0)),
                "tied": int(np.sum(diff == 0)),
            }
        )
    return rows


def _print_table(rows: list[dict], reference: str) -> None:
    print(
        f"\n{'arm':<28}{'n':>5}{'mean':>9}{'sd':>8}"
        f"{'vs ' + reference:>14}{'95% CI':>10}{'W/L/T':>14}"
    )
    for row in rows:
        verdict = ""
        if row["arm"] != reference:
            if abs(row["vs_reference"]) <= row["ci95"]:
                verdict = "  not distinguishable"
            elif abs(row["vs_reference"]) < row["mde"]:
                # Significant but under-powered by this repo's own standard.
                verdict = "  under-powered"
            elif row["vs_reference"] > 0:
                verdict = "  BETTER"
            else:
                verdict = "  worse"
        print(
            f"{row['arm']:<28}{row['n']:>5}{row['mean']:>9.2f}{row['sd']:>8.2f}"
            f"{row['vs_reference']:>+14.2f}{row['ci95']:>10.2f}"
            f"{f'{row["won"]}/{row["lost"]}/{row["tied"]}':>14}{verdict}"
        )
    # Per arm, not the maximum across arms. The old headline reported the
    # noisiest arm's spread -- run a model beside `random` and the printed MDE
    # belonged to `random`.
    print("\nMDE(80% power) per arm, the bar this n can actually clear:")
    for row in rows:
        if row["arm"] != reference and row["mde"] < 1e9:
            print(f"  {row['arm']:<28}+/-{row['mde']:.2f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", required=True)
    parser.add_argument("--reference", default="heuristic")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--seed-base", type=int, default=90_000)
    parser.add_argument("--workers", type=int, default=min(30, os.cpu_count() or 4))
    parser.add_argument("--plain", action="store_true", help="bypass the event gate")
    parser.add_argument("--defer", action="store_true", help="offer the DEFER action")
    parser.add_argument("--proposal-features", action="store_true")
    parser.add_argument("--backstop", type=int, default=200)
    parser.add_argument("--deviation-scope", choices=("all", "kind"), default="all")
    parser.add_argument("--max-decisions", type=int, default=200_000)
    parser.add_argument("--deterministic", action="store_true")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    if "defer" in args.arms and not args.defer:
        parser.error("the 'defer' arm needs --defer, which is what adds the action")
    if args.plain:
        # --plain bypasses the gate entirely, so every gate-shaped flag would
        # be accepted and dropped -- and the `defer` arm would then die inside
        # a pool worker with a bare AttributeError on env.DEFER.
        ignored = [
            name
            for name, value in (
                ("--defer", args.defer),
                ("--proposal-features", args.proposal_features),
                ("--deviation-scope", args.deviation_scope != "all"),
                ("--backstop", args.backstop != parser.get_default("backstop")),
            )
            if value
        ]
        if ignored:
            parser.error(
                f"--plain bypasses the event gate, so {', '.join(ignored)} "
                "would be accepted and ignored. Drop --plain to use them, or "
                "drop them to measure the ungated environment."
            )
    if args.reference not in args.arms:
        parser.error(
            f"--reference {args.reference!r} is not among --arms {args.arms}; "
            "the paired difference is taken against it, so it has to be run"
        )

    spec = {
        "gated": not args.plain,
        "defer": args.defer,
        "proposal": args.proposal_features,
        "backstop": args.backstop,
        "scope": args.deviation_scope,
        "max_decisions": args.max_decisions,
        "deterministic": args.deterministic,
    }
    seeds = [args.seed_base + i for i in range(args.episodes)]
    jobs = [(arm, seed, spec) for arm in args.arms for seed in seeds]
    print(
        f"{len(jobs)} episodes: {len(args.arms)} arms x {len(seeds)} seeds "
        f"on {args.workers} workers, "
        f"{'gated' if spec['gated'] else 'plain'} env",
        flush=True,
    )

    scores: dict[str, dict[int, float]] = {arm: {} for arm in args.arms}
    traces: dict[str, dict[int, list]] = {arm: {} for arm in args.arms}
    extra: dict[str, list[dict]] = {arm: [] for arm in args.arms}
    done = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(_work, jobs, chunksize=1):
            scores[result["arm"]][result["seed"]] = result["score"]
            traces[result["arm"]][result["seed"]] = result.pop("actions")
            extra[result["arm"]].append(result)
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)

    rows = summarise(scores, args.reference, seeds)
    _print_table(rows, args.reference)
    for arm in args.arms:
        runs = extra[arm]
        print(
            f"{arm:<28} queries/ep {np.mean([r['queries'] for r in runs]):8.1f}"
            f"  decisions/ep {np.mean([r['decisions'] for r in runs]):9.1f}"
            f"  deviations/ep {np.mean([r['deviations'] for r in runs]):7.2f}"
        )
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "rows": rows,
                    "scores": scores,
                    "traces": traces,
                    "spec": spec,
                    "seeds": seeds,
                },
                handle,
                indent=2,
            )
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
