"""GM-10d contract: the NEW_LINE offer effect -- a free line (D-044).

Picking the NEW_LINE week-boundary offer unlocks the next metro line for free (no
credit spend), capped at num_paths. It is the FIRST real per-kind offer effect;
locomotive/carriage/tunnel stay stub no-ops (GM-10e/f/g). The grant flows through
the already-persisted purchased_num_paths, so it is Continue-exact with no schema
change (D-043/D-044); RL/headless never reach it (offers gated to the human shell).
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import num_paths, path_unlock_milestones
from mediator import Mediator
from offers import OfferKind, describe
from progression import NetworkProgression
from save_game import serialize_game
from save_load import deserialize_game

pygame.init()


def _fresh_progression():
    return NetworkProgression(
        num_paths=num_paths,
        path_unlock_milestones=path_unlock_milestones,
        num_stations=20,
        initial_num_stations=3,
        station_unlock_milestones=[10, 30, 50],
    )


class TestGM10dGrantFreePath(unittest.TestCase):
    def test_grant_unlocks_the_next_line_without_spending_credits(self):
        p = _fresh_progression()
        p.line_credits = 5
        self.assertEqual(p.purchased_num_paths, 1)
        self.assertTrue(p.grant_free_path(), "a line was granted")
        self.assertEqual(p.purchased_num_paths, 2)
        self.assertEqual(p.get_unlocked_num_paths(), 2)
        self.assertEqual(p.line_credits, 5, "a grant spends NO credits")

    def test_grant_caps_at_num_paths(self):
        p = _fresh_progression()
        granted = 0
        while p.grant_free_path():
            granted += 1
        self.assertEqual(p.purchased_num_paths, num_paths, "capped at num_paths")
        self.assertEqual(granted, num_paths - 1, "started at 1, granted up to the cap")
        self.assertFalse(p.grant_free_path(), "a grant at the cap is a no-op")
        self.assertEqual(p.purchased_num_paths, num_paths)

    def test_grant_at_or_above_cap_is_a_noop(self):
        # review MAJOR: pin the `>=` cap, not `==`. A loaded save can legitimately hold
        # purchased_num_paths ABOVE num_paths (the schema clamps unlocked, not
        # purchased -- get_unlocked_num_paths mins it down), and an `==` guard would
        # grant AGAIN from such a state. Both `== num_paths` and `> num_paths` no-op.
        p = _fresh_progression()
        for excess in (0, 1, 3):
            p.purchased_num_paths = num_paths + excess
            self.assertFalse(
                p.grant_free_path(), f"no-op at purchased={num_paths + excess}"
            )
            self.assertEqual(p.purchased_num_paths, num_paths + excess, "unchanged")


class TestGM10dApplyNewLine(unittest.TestCase):
    def _pending_game(self):
        m = Mediator(seed=0)
        m.week_calendar = True
        while not m.is_week_boundary_pending:
            m.increment_time(17)
        return m

    def test_choosing_new_line_unlocks_a_line_and_refreshes_caches(self):
        m = self._pending_game()
        offer = describe(OfferKind.NEW_LINE)
        # Present NEW_LINE explicitly (RNG-independent + satisfies the confinement
        # guard: only a currently-offered choice can be applied).
        m.current_offers = (offer, describe(OfferKind.LOCOMOTIVE))
        before_unlocked = m.unlocked_num_paths
        before_credits = m.line_credits
        m.resolve_week_boundary(offer)
        self.assertEqual(m.unlocked_num_paths, before_unlocked + 1, "a line unlocked")
        self.assertEqual(m.purchased_num_paths, before_unlocked + 1)
        self.assertEqual(m.line_credits, before_credits, "no credit spend")
        self.assertEqual(m.current_offers, (), "offers cleared")
        self.assertFalse(m.is_week_boundary_pending, "pause released")
        # The newly-unlocked path button is no longer locked (cache refreshed).
        self.assertFalse(
            m.path_buttons[before_unlocked].is_locked, "new line's button unlocked"
        )

    def test_grant_starts_the_unlock_blink(self):
        # review MINOR: the grant must refresh via update_unlocked_num_paths so the
        # newly-unlocked button BLINKS (as a purchase does). A mutant that eagerly
        # bumps unlocked_num_paths inside grant_free_path would suppress the blink.
        m = Mediator(seed=0)
        button = m.path_buttons[1]
        self.assertFalse(button.is_unlock_blink_active(m.time_ms))
        m._grant_free_line()
        self.assertTrue(
            button.is_unlock_blink_active(m.time_ms), "the free line's button blinks"
        )

    def test_new_line_grant_is_continue_exact(self):
        m = Mediator(seed=0)
        m._grant_free_line()  # purchased 1 -> 2
        self.assertEqual(m.purchased_num_paths, 2)
        self.assertEqual(m.unlocked_num_paths, 2)
        doc = serialize_game(m)
        self.assertEqual(doc["purchasedNumPaths"], 2)
        self.assertEqual(
            doc["numPaths"], num_paths, "the total is unchanged (pin holds)"
        )
        loaded = deserialize_game(doc)  # must not raise (_require_running_config OK)
        self.assertEqual(loaded.purchased_num_paths, 2, "purchased reproduced")
        self.assertEqual(loaded.unlocked_num_paths, 2, "unlocked reproduced")

    def test_grant_free_line_at_the_cap_is_a_noop(self):
        m = Mediator(seed=0)
        for _ in range(num_paths):  # drive purchased_num_paths to the cap
            m._grant_free_line()
        self.assertEqual(m.purchased_num_paths, num_paths)
        before = serialize_game(m)
        m._grant_free_line()  # nothing left to grant
        self.assertEqual(m.purchased_num_paths, num_paths, "still capped")
        self.assertEqual(serialize_game(m), before, "a maxed grant moves no save byte")

    def test_resolve_rejects_an_offer_that_was_not_presented(self):
        # review MAJOR: an offer is applicable only when it is a currently-presented
        # choice at a held boundary -- otherwise a headless/out-of-band call could
        # grant an upgrade and bypass the weekly economy.
        offered = describe(OfferKind.NEW_LINE)
        # (a) no pending boundary at all (a fresh headless-style game).
        m = Mediator(seed=0)
        self.assertFalse(m.is_week_boundary_pending)
        with self.assertRaisesRegex(ValueError, "currently-presented"):
            m.resolve_week_boundary(offered)
        self.assertEqual(m.purchased_num_paths, 1, "no line granted out of boundary")
        # (b) a pending boundary that offered DIFFERENT kinds.
        p = self._pending_game()
        p.current_offers = (describe(OfferKind.CARRIAGE),)  # NEW_LINE not offered
        with self.assertRaisesRegex(ValueError, "currently-presented"):
            p.resolve_week_boundary(offered)
        self.assertTrue(p.is_week_boundary_pending, "rejected -- boundary still held")

    def test_the_other_offer_kinds_still_grant_nothing(self):
        # LOCOMOTIVE/CARRIAGE/TUNNEL are GM-10e/f/g -- still no-op, so they do not
        # unlock a line (only NEW_LINE does).
        for kind in (OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE, OfferKind.TUNNEL):
            m = Mediator(seed=0)
            before = m.unlocked_num_paths
            m._apply_offer(describe(kind))
            self.assertEqual(
                m.unlocked_num_paths, before, f"{kind.name} unlocked no line"
            )


if __name__ == "__main__":
    unittest.main()
