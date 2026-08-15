"""Decide by lookahead: simulate each candidate action to the end, keep the best.

Four learned policies have now landed in the same 170-195 band -- cloning,
cloning plus anchored PPO, a pointer architecture, and DAgger -- while the
scripted heuristic reaches ~262 from the identical action space and observation.
Imitation raised fidelity without raising score, so the missing ingredient is not
a better fit to the teacher.

The nearest published domain agrees. Across the transit-network literature a pure
neural policy is never the best method; the winners embed a policy inside a
search. This game makes that unusually cheap, because it serialises exactly -- a
candidate can be *tried* rather than guessed at.

Two measurements shape the design, and the first one killed the obvious version.

**Decisions are far apart.** On seed 9000 the heuristic acts at decisions
0-7, 459, 1702, 3411, 3412, 5444 and 7681, out of 8244. The gaps run 450 to 2200
decisions, so a fixed short horizon cannot even reach the next decision point. A
150-step horizon scored 144 against the heuristic's 262 precisely because it saw
each action's immediate cost and none of its delayed payoff, so WAIT won by
default and search systematically under-acted. Rollouts therefore run to episode
end -- no horizon, no truncation bias.

**Rollouts are reproducible.** Three rollouts from one snapshot returned 13.0
deliveries every time, so the RNG state survives serialisation. One rollout per
candidate gives the exact future under the default policy and no averaging is
needed. This is exact rollout policy improvement, which is at least as good as
its default policy whenever the comparison is exact -- and here it is.
"""

from __future__ import annotations

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import numpy as np

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from rl.heuristic import choose  # noqa: E402
from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402
from save_game import serialize_game  # noqa: E402
from save_load import deserialize_game  # noqa: E402

# Kinds worth spending a search on. WAIT is always included as the baseline
# candidate, since "not yet" is frequently the right answer.
STRUCTURAL = (
    ActionKind.CONNECT,
    ActionKind.EXTEND_LINE,
    ActionKind.PREPEND_LINE,
    ActionKind.PURCHASE_LINE,
    ActionKind.ASSIGN_LOCOMOTIVE,
    ActionKind.ATTACH_CARRIAGE,
)


def _restore(env, document, decision: int) -> None:
    """Rebuild the env's game from a snapshot, at the same decision count.

    `_decision` is restored rather than reset because the difficulty ramp and
    several observation features read it -- a rollout that believed it was at
    decision 0 would be simulating an easier game than the real one.
    """
    env._mediator = deserialize_game(document)
    env._decision = decision
    env._last_deliveries = env._mediator.deliveries
    env._line_born = {}


def _rollout(env, document, decision: int, action: int, cap: int) -> float:
    """Apply one candidate, then let the default policy play to the end."""
    _restore(env, document, decision)
    total = 0.0
    _, reward, terminated, truncated, _ = env.step(action)
    total += float(reward)
    if terminated or truncated:
        return total
    for _ in range(cap):
        _, reward, terminated, truncated, _ = env.step(choose(env))
        total += float(reward)
        if terminated or truncated:
            break
    return total


def _signature(mask) -> frozenset:
    """Which structural KINDS are currently available.

    Searching at all ~56 points where any structural action is legal costs four
    times what it buys, because most of those points differ only in which station
    pair is offered. A change in this signature means a new *capability* arrived
    -- a line slot, a locomotive, a carriage -- which is exactly when the
    heuristic's fixed priority order is most likely to be wrong.
    """
    return frozenset(
        ACTION_TABLE[i][0]
        for i in np.flatnonzero(mask)
        if ACTION_TABLE[i][0] in STRUCTURAL
    )


def play(seed: int, candidates: int, cap: int) -> dict:
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    delivered = 0.0
    decisions = searches = overrides = 0
    last_signature: frozenset | None = None

    while True:
        mask = env.action_masks()
        structural = [
            i for i in np.flatnonzero(mask) if ACTION_TABLE[i][0] in STRUCTURAL
        ]
        preferred = choose(env)
        signature = _signature(mask)
        worth_searching = structural and (preferred != 0 or signature != last_signature)

        if not worth_searching:
            action = preferred
        else:
            last_signature = signature
            # Rank by the heuristic's own preference so the candidate set stays
            # small and sensible, then add WAIT as the do-nothing baseline.
            shortlist = [preferred] if preferred != 0 else []
            shortlist += [i for i in structural if i != preferred][: candidates - 1]
            if 0 not in shortlist:
                shortlist.append(0)

            document = serialize_game(env._mediator)
            at = env._decision
            scored = [
                (_rollout(env, document, at, candidate, cap), candidate)
                for candidate in shortlist
            ]
            _restore(env, document, at)
            searches += 1
            best = max(scored)[1]
            overrides += int(best != preferred)
            action = best

        _, reward, terminated, truncated, _ = env.step(action)
        delivered += float(reward)
        decisions += 1
        if terminated or truncated:
            break

    mediator = env._mediator
    result = {
        "seed": seed,
        "deliveries": int(delivered),
        "decisions": decisions,
        "searches": searches,
        "overrode_heuristic": overrides,
        "lines": len(mediator.paths),
        "longest_line": max((len(p.stations) for p in mediator.paths), default=0),
        "stations": len(mediator.stations),
    }
    env.close()
    return result


def baseline(seed: int) -> int:
    """The default policy on the same seed, so the comparison is paired."""
    env = SemanticMetroEnv()
    env.reset(seed=seed)
    total = 0.0
    while True:
        _, reward, terminated, truncated, _ = env.step(choose(env))
        total += float(reward)
        if terminated or truncated:
            break
    env.close()
    return int(total)


def _one(job):
    seed, candidates, cap = job
    return play(seed, candidates, cap), baseline(seed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes", type=int, default=8)
    parser.add_argument("--seed", type=int, default=9000)
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--cap", type=int, default=20_000)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args(argv)

    print(
        f"lookahead: {args.candidates} candidates rolled to episode end, "
        f"heuristic as the default policy, {args.workers} workers"
    )
    jobs = [(args.seed + i, args.candidates, args.cap) for i in range(args.episodes)]
    searched, control = [], []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result, default in pool.map(_one, jobs):
            searched.append(result["deliveries"])
            control.append(default)
            print(
                f"  seed {result['seed']}: search {result['deliveries']:5d} vs "
                f"heuristic {default:5d}  "
                f"({result['deliveries'] - default:+5d})   "
                f"{result['searches']:3d} searches, "
                f"{result['overrode_heuristic']:3d} overrode, "
                f"line of {result['longest_line']}/{result['stations']}",
                flush=True,
            )

    search_array = np.array(searched, dtype=float)
    base_array = np.array(control, dtype=float)
    gap = search_array - base_array
    stderr = gap.std(ddof=1) / np.sqrt(len(gap)) if len(gap) > 1 else 0.0
    print(f"\nsearch:    mean {search_array.mean():7.2f}  max {search_array.max():.0f}")
    print(f"heuristic: mean {base_array.mean():7.2f}  max {base_array.max():.0f}")
    print(
        f"paired gap: {gap.mean():+.2f} +/-{1.96 * stderr:.2f}  "
        f"(search won {int((gap > 0).sum())}/{len(gap)}, "
        f"tied {int((gap == 0).sum())})"
    )
    print(
        "\nSearch BEATS its own default policy."
        if gap.mean() - 1.96 * stderr > 0
        else "\nSearch does NOT beat its own default policy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
