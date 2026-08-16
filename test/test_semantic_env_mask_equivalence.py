"""The action mask is a contract; making it faster must not change one bit.

`action_masks` costs 65.9 microseconds against the game tick's ~26, so the
wrapper is more expensive than the simulation it wraps. Nearly all of that is
redundant: `_path_station_indices` rebuilds a lookup over every station on each
call, and the mask loop calls it once per EXTEND/PREPEND entry -- 160 times per
mask, to produce four distinct answers.

Search is entirely simulation-bound (roughly 400 full games per episode of
training data), so this cost converts directly into how much search can be run.

Optimising a mask is exactly the kind of change that fails silently: a wrong mask
does not raise, it quietly offers or withholds actions and shows up much later as
a policy that will not learn. So this pins the mask against an independent,
deliberately naive recomputation across many real mid-game states, including ones
reached by random play where lines are odd shapes.
"""

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402

from rl.semantic_env import ACTION_TABLE, ActionKind, SemanticMetroEnv  # noqa: E402


def _reference_mask(env) -> np.ndarray:
    """A slow, obvious mask, written independently of the optimised one."""
    mediator = env._mediator
    stations = list(mediator.stations)
    paths = list(mediator.paths)
    purchasable = mediator.get_next_path_button_idx_to_purchase()
    can_buy = purchasable is not None and mediator.can_purchase_path_button_idx(
        purchasable
    )
    can_connect = len(stations) >= 2 and len(paths) < mediator.get_unlocked_num_paths()

    mask = np.zeros(len(ACTION_TABLE), dtype=bool)
    for index, (kind, first, second) in enumerate(ACTION_TABLE):
        if kind == ActionKind.WAIT:
            mask[index] = True
        elif kind == ActionKind.CONNECT:
            mask[index] = can_connect and second < len(stations)
        elif kind == ActionKind.ASSIGN_LOCOMOTIVE:
            mask[index] = first < len(paths) and mediator.can_assign_locomotive(
                paths[first]
            )
        elif kind == ActionKind.ATTACH_CARRIAGE:
            mask[index] = first < len(paths) and mediator.can_attach_carriage(
                paths[first]
            )
        elif kind == ActionKind.PURCHASE_LINE:
            mask[index] = can_buy
        elif kind == ActionKind.REMOVE_LINE:
            mask[index] = (
                first < len(paths)
                and env._line_age(mediator, first) >= env.remove_min_age
            )
        else:
            if first >= len(paths) or second >= len(stations):
                mask[index] = False
            else:
                on_line = [
                    position
                    for position, station in enumerate(stations)
                    if any(station is other for other in paths[first].stations)
                ]
                mask[index] = second not in on_line
    return mask


class MaskEquivalenceTest(unittest.TestCase):
    def _compare_along_an_episode(self, seed: int, chooser, steps: int) -> int:
        env = SemanticMetroEnv()
        env.reset(seed=seed)
        checked = 0
        try:
            for _ in range(steps):
                produced = env.action_masks()
                expected = _reference_mask(env)
                if not np.array_equal(produced, expected):
                    differing = np.flatnonzero(produced != expected)
                    entries = [
                        (
                            int(i),
                            ActionKind(ACTION_TABLE[i][0]).name,
                            ACTION_TABLE[i][1:],
                        )
                        for i in differing[:5]
                    ]
                    self.fail(
                        f"seed {seed}, step {checked}: the mask disagrees with an "
                        f"independent recomputation on {len(differing)} of "
                        f"{len(ACTION_TABLE)} actions, first few {entries}; a wrong "
                        "mask silently offers or withholds actions and surfaces "
                        "later as a policy that will not learn"
                    )
                checked += 1
                _, _, terminated, truncated, _ = env.step(chooser(env))
                if terminated or truncated:
                    break
        finally:
            env.close()
        return checked

    def test_it_matches_a_naive_recomputation_under_competent_play(self):
        from rl.heuristic import choose

        checked = self._compare_along_an_episode(9000, choose, 900)

        self.assertGreater(checked, 100, "the episode ended before enough states")

    def test_it_matches_under_random_play_which_builds_odd_lines(self):
        """Random play reaches line shapes the heuristic never produces."""
        rng = np.random.default_rng(3)

        def chooser(env):
            return int(rng.choice(np.flatnonzero(env.action_masks())))

        checked = self._compare_along_an_episode(11, chooser, 400)

        self.assertGreater(checked, 50, "the episode ended before enough states")


if __name__ == "__main__":
    unittest.main()
