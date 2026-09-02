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
# The restore-behind-the-cache gate below imports `search_policy`, which lives
# in scripts/. Without this line that import resolved only because some OTHER
# test module had already appended the same path during discovery, so running
# this file on its own raised ModuleNotFoundError and the gate reported an error
# instead of guarding the cache -- and a gate whose reach depends on discovery
# order is not a gate.
sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../scripts")

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
                    # Compare the TERMINAL state too. Breaking here without
                    # this let a real defect through: `is_game_over` was absent
                    # from the cache fingerprint, so a finished game kept
                    # advertising ASSIGN_LOCOMOTIVE and ATTACH_CARRIAGE, and no
                    # comparison ever ran on the one state where it mattered.
                    produced = env.action_masks()
                    expected = _reference_mask(env)
                    if not np.array_equal(produced, expected):
                        differing = np.flatnonzero(produced != expected)
                        self.fail(
                            f"seed {seed}: the mask on the TERMINAL state "
                            f"disagrees on {len(differing)} actions "
                            f"{[int(i) for i in differing[:5]]}"
                        )
                    checked += 1
                    break
        finally:
            env.close()
        return checked

    def test_it_matches_a_naive_recomputation_under_competent_play(self):
        from rl.heuristic import choose

        checked = self._compare_along_an_episode(9000, choose, 900)

        self.assertGreater(checked, 100, "the episode ended before enough states")

    def test_it_matches_when_the_remove_age_gate_is_actually_live(self):
        """With the default `remove_min_age` of 0 that gate never varies.

        The fingerprint carries a per-line "old enough to remove" flag, and at
        the default it is a constant tuple of True -- so the branch was present
        in every test and exercised by none.
        """
        from rl.heuristic import choose

        env = SemanticMetroEnv(remove_min_age=25)
        env.reset(seed=9000)
        checked = 0
        try:
            for _ in range(600):
                produced = env.action_masks()
                expected = _reference_mask(env)
                if not np.array_equal(produced, expected):
                    differing = np.flatnonzero(produced != expected)
                    self.fail(
                        f"with remove_min_age=25 the mask disagrees at step "
                        f"{checked} on {len(differing)} actions "
                        f"{[int(i) for i in differing[:5]]}"
                    )
                checked += 1
                _, _, terminated, truncated, _ = env.step(choose(env))
                if terminated or truncated:
                    break
        finally:
            env.close()

        self.assertGreater(checked, 100, "the episode ended before enough states")

    def test_it_matches_after_a_line_is_rerouted_to_the_same_length(self):
        """Same line, same length, different stations -- the fingerprint must move.

        The cache fingerprint originally recorded each line's route LENGTH and
        id but not its membership. Rerouting line 0 from [0,1] to [0,2] leaves
        both unchanged, so the cache answered with the old legality: EXTEND and
        PREPEND toward station 1 reported illegal when they are legal, and
        toward station 2 legal when they are not.

        That was survivable only because `_apply` happens to grow routes rather
        than replace them -- a property of the current caller, not of the game.
        This drives the replacement directly so the fingerprint term is gated on
        its own, rather than by the `_restore` cache-clear that also covers it.
        """
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        for _ in range(200):
            env.step(0)
        mediator = env._mediator
        mediator.create_path_from_station_indices([0, 1])
        env.action_masks()

        mediator.replace_path_by_index(0, [0, 2])
        produced = env.action_masks()
        expected = _reference_mask(env)
        env.close()

        differing = np.flatnonzero(produced != expected)
        self.assertEqual(
            len(differing),
            0,
            f"after rerouting a line to a route of the same length the mask "
            f"disagrees on {len(differing)} actions "
            f"{[(int(i), ActionKind(ACTION_TABLE[i][0]).name, ACTION_TABLE[i][1:]) for i in differing[:4]]}; "
            "the cache is keyed on route length rather than membership",
        )

    def test_it_matches_after_an_unassignment_is_queued_through_the_public_api(self):
        """The third fingerprint term, and the one the rule is actually about.

        `is_unassignment_queued` is in the fingerprint for a reason nothing in
        this environment's action table can produce: no action here queues an
        unassignment, so "unreachable from the current caller" was the exact
        argument that let route membership and `is_game_over` be omitted. The
        mediator's public API has `queue_locomotive_unassignment`, and a
        restored save can arrive already queued, so the domain can change it
        even though today's caller cannot.

        `carriage_management._attach_candidate` filters on the flag while the
        plain metro count does not move when one is queued -- so dropping the
        term leaves ATTACH_CARRIAGE advertised on a line that can no longer take
        one, silently, as a policy that will not learn.

        EXACTLY ONE locomotive is assigned first, and that is a pinned input.
        With the line's full four metros assigned, queuing one leaves three
        still attachable and the mask does not move at all, so the comparison
        passes with the term deleted. The flag only reaches the mask when the
        queued metro is the only candidate. The first assertion measures that
        rather than assuming it.
        """
        env = SemanticMetroEnv()
        env.reset(seed=9000)
        for _ in range(400):
            env.step(0)
        mediator = env._mediator
        mediator.create_path_from_station_indices([0, 1])
        self.assertTrue(mediator.can_assign_locomotive(mediator.paths[0]))
        self.assertTrue(mediator.assign_locomotive(mediator.paths[0]))
        before = _reference_mask(env)
        # Warm the cache on the un-queued state, so a stale answer exists to be
        # served.
        env.action_masks()

        self.assertTrue(
            mediator.can_queue_locomotive_unassignment(mediator.paths[0]),
            "the public API cannot queue an unassignment from this state, so "
            "this test never exercises the fingerprint term it exists for",
        )
        self.assertTrue(mediator.queue_locomotive_unassignment(mediator.paths[0]))

        produced = env.action_masks()
        expected = _reference_mask(env)
        env.close()

        moved = np.flatnonzero(before != expected)
        self.assertGreater(
            len(moved),
            0,
            "queuing an unassignment left the true mask unchanged, so this "
            "state cannot tell a fingerprint that carries the flag from one "
            "that drops it and the assertion below is vacuous",
        )
        differing = np.flatnonzero(produced != expected)
        self.assertEqual(
            len(differing),
            0,
            f"after queuing an unassignment through the mediator's public API "
            f"the mask disagrees on {len(differing)} actions "
            f"{[(int(i), ActionKind(ACTION_TABLE[i][0]).name, ACTION_TABLE[i][1:]) for i in differing[:4]]}; "
            "the cache is keyed on what this environment's action table can do "
            "rather than on what the game can do",
        )

    def test_it_matches_after_a_different_game_is_restored_behind_it(self):
        """The search lane swaps `env._mediator` directly, bypassing reset().

        A cache keyed on the previous game answers for the previous game. This
        was a real defect: `_restore` replaced the mediator and left the cache,
        and the fingerprint recorded route LENGTH but not membership, so a
        restored line of equal length inherited the wrong legality -- one legal
        action withheld and one illegal action offered.
        """
        from search_policy import _restore

        from save_game import serialize_game

        env = SemanticMetroEnv()
        env.reset(seed=9000)
        for _ in range(200):
            env.step(0)
        mediator = env._mediator
        mediator.create_path_from_station_indices([0, 1])
        document = serialize_game(mediator)
        at = env._decision

        # Move to a DIFFERENT line of the same length, and warm the cache on it.
        mediator.replace_path_by_index(0, [0, 2])
        env.action_masks()

        _restore(env, document, at)
        produced = env.action_masks()
        expected = _reference_mask(env)
        env.close()

        differing = np.flatnonzero(produced != expected)
        self.assertEqual(
            len(differing),
            0,
            f"after restoring a different game the mask disagrees on "
            f"{len(differing)} actions {[int(i) for i in differing[:6]]}; the "
            "cache is answering for the game that was discarded",
        )

    def test_it_matches_under_random_play_which_builds_odd_lines(self):
        """Random play reaches line shapes and terminal states the heuristic does not.

        The seeds are not arbitrary. A review sweep of 50 episodes found the
        cache serving a stale mask on the TERMINAL state of seeds 8, 17 and 18
        specifically -- `is_game_over` was missing from the fingerprint, so a
        finished game still advertised ASSIGN_LOCOMOTIVE and ATTACH_CARRIAGE.
        A version of this test on seed 11 passed with the defect present, so
        the reproducing seeds are pinned here deliberately.
        """
        total = 0
        for seed in (8, 17, 18, 11):
            rng = np.random.default_rng(seed)

            def chooser(env, rng=rng):
                return int(rng.choice(np.flatnonzero(env.action_masks())))

            total += self._compare_along_an_episode(seed, chooser, 4000)

        self.assertGreater(total, 100, "the episodes ended before enough states")


if __name__ == "__main__":
    unittest.main()
