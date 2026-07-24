"""GM-10b contract: the dedicated-RNG weekly offer generator (D-042).

At each GM-10a week boundary the interactive game generates a deterministic SET of
upgrade offers (data only -- applying a choice is GM-10c, per-kind effects GM-10d-g,
replay/persistence reconciliation GM-10h). The offer RNG is a per-week `random.Random`
derived READ-ONLY from the already-persisted gameplay RNG state + week_index, so:
- offers are CONTINUE-EXACT (reproduce after save/load) with NO new persisted state;
- generation is gameplay-INERT (consumes zero gameplay draws);
- offers are gated to the human shell (calendar OFF => never generated for RL/headless).
"""

from __future__ import annotations

import os
import random
import subprocess
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np
import pygame

from config import (
    OFFERS_PER_WEEK,
    WEEK_LENGTH_STEPS,
    game_over_text_color,
    screen_height,
    screen_width,
)
from env import MiniMetroEnv
from maps import resolve_map
from mediator import Mediator
from offers import Offer, OfferKind, describe, generate_offers
from rl.player_env import PlayerPixelEnv
from save_game import serialize_game
from save_load import deserialize_game
from ui.menu_screens import draw_offer_screen

pygame.init()

_SRC = os.path.dirname(os.path.realpath(__file__)) + "/../src"

# Frozen seed-0 offer sequences, pinned as literals (never a runtime capture) so a
# change to the generator, POOL ORDER, or derivation turns them red. CLASSIC (3-kind
# pool) and RIVER (4-kind pool incl. TUNNEL -- week 3 here) lock BOTH pool orderings
# behaviorally (review MINOR: a bounded-pool reorder must not survive the suite).
# The exact values are implicitly coupled to CPython 3.13's `random.sample`; the repo
# pins py313, so a Python bump would require re-pinning these literals.
_SEED0_SEQUENCE = (
    ("CARRIAGE", "NEW_LINE"),
    ("NEW_LINE", "CARRIAGE"),
    ("LOCOMOTIVE", "CARRIAGE"),
    ("NEW_LINE", "CARRIAGE"),
)
_RIVER_SEED0_SEQUENCE = (
    ("LOCOMOTIVE", "NEW_LINE"),
    ("NEW_LINE", "CARRIAGE"),
    ("NEW_LINE", "TUNNEL"),
    ("LOCOMOTIVE", "CARRIAGE"),
    ("CARRIAGE", "LOCOMOTIVE"),
)


def _played(seed, *, calendar=True, map_definition=None):
    kwargs = {"seed": seed}
    if map_definition is not None:
        kwargs = {"seed": seed, "map_definition": map_definition}
    m = Mediator(**kwargs)
    m.week_calendar = calendar
    path = m.create_path_from_station_indices([0, 1, 2])
    m.assign_locomotive(path)
    return m


def _collect_offer_kinds(m, weeks):
    out = []
    while m.week_index < weeks and not m.is_game_over:
        m.increment_time(17)
        if m.is_week_boundary_pending:
            out.append(tuple(o.kind.name for o in m.current_offers))
            m.resolve_week_boundary()
    return out


def _step_to_first_boundary(m):
    guard = 0
    while not m.is_week_boundary_pending and guard < WEEK_LENGTH_STEPS * 2:
        m.increment_time(17)
        guard += 1
    return m


class TestGM10bGenerator(unittest.TestCase):
    def test_generate_offers_is_distinct_and_deterministic(self):
        a = generate_offers(random.Random(5), count=2, tunnels_bounded=True)
        b = generate_offers(random.Random(5), count=2, tunnels_bounded=True)
        self.assertEqual(a, b, "same RNG state -> same offers")
        self.assertEqual(len(a), 2)
        self.assertEqual(len({o.kind for o in a}), 2, "offers are DISTINCT kinds")
        self.assertTrue(all(isinstance(o, Offer) for o in a))

    def test_tunnel_excluded_on_unbounded_included_on_bounded(self):
        # Over many draws, an unbounded (CLASSIC) pool NEVER offers TUNNEL; a bounded
        # pool CAN. Pin the exact pool membership, not just one draw.
        classic_kinds = set()
        bounded_kinds = set()
        for s in range(200):
            classic_kinds |= {
                o.kind
                for o in generate_offers(
                    random.Random(s), count=3, tunnels_bounded=False
                )
            }
            bounded_kinds |= {
                o.kind
                for o in generate_offers(
                    random.Random(s), count=4, tunnels_bounded=True
                )
            }
        self.assertNotIn(
            OfferKind.TUNNEL, classic_kinds, "no tunnel on an unbounded map"
        )
        self.assertEqual(
            classic_kinds,
            {OfferKind.NEW_LINE, OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE},
        )
        self.assertIn(
            OfferKind.TUNNEL, bounded_kinds, "tunnel offered on a bounded map"
        )
        self.assertEqual(len(bounded_kinds), 4)

    def test_labels_are_the_canonical_text(self):
        self.assertEqual(describe(OfferKind.NEW_LINE).label, "New Line")
        self.assertEqual(describe(OfferKind.LOCOMOTIVE).label, "+1 Locomotive")
        self.assertEqual(describe(OfferKind.CARRIAGE).label, "+1 Carriage")
        self.assertEqual(describe(OfferKind.TUNNEL).label, "+1 Tunnel")

    def test_count_below_one_raises_named_error(self):
        # review MINOR: cover zero AND negative -- `< 1` (not `== 0`) must guard both;
        # a negative that slipped through would hit random.sample's generic error.
        for bad in (0, -1, -5):
            with self.assertRaisesRegex(ValueError, "positive number of offers"):
                generate_offers(random.Random(0), count=bad, tunnels_bounded=True)

    def test_count_above_pool_clamps_silently(self):
        # Documented silent cap: count=9 over the 3-kind CLASSIC pool yields 3.
        drawn = generate_offers(random.Random(0), count=9, tunnels_bounded=False)
        self.assertEqual(len(drawn), 3)
        self.assertEqual(len({o.kind for o in drawn}), 3)


class TestGM10bMediatorOffers(unittest.TestCase):
    def test_offers_generated_at_the_boundary_and_frozen_sequence(self):
        self.assertEqual(_collect_offer_kinds(_played(0), 4), list(_SEED0_SEQUENCE))

    def test_same_seed_same_offers(self):
        self.assertEqual(
            _collect_offer_kinds(_played(3), 3), _collect_offer_kinds(_played(3), 3)
        )

    def test_derivation_depends_on_week_index(self):
        # review NIT: isolate week_index -- with the SAME python_random state, two
        # different week_index values must yield DIFFERENT offer seeds. (A weaker
        # "weeks differ" check passes even if week_index were dropped, since the
        # gameplay state already moves each week.)
        m = _played(0)
        for _ in range(300):
            m.increment_time(17)
        state = m.context.python_random.getstate()
        seeds = set()
        original = m.steps
        for wk_steps in (0, WEEK_LENGTH_STEPS, WEEK_LENGTH_STEPS * 5):
            m.steps = wk_steps  # week_index is steps-derived
            m.context.python_random.setstate(state)  # hold the gameplay state fixed
            seeds.add(m._offer_rng_for_current_week().random())
        m.steps = original
        self.assertEqual(len(seeds), 3, "the seed varies with week_index alone")

    def test_default_count_is_offers_per_week(self):
        offers = _step_to_first_boundary(_played(0)).current_offers
        self.assertEqual(len(offers), OFFERS_PER_WEEK)

    def test_resolve_clears_the_offers(self):
        m = _step_to_first_boundary(_played(0))
        self.assertTrue(m.current_offers, "offers present while pending")
        m.resolve_week_boundary()
        self.assertEqual(m.current_offers, ())

    def test_generation_consumes_zero_gameplay_draws(self):
        # review MAJOR-3 (direct): deriving + generating offers must NOT advance
        # EITHER gameplay stream -- both python_random AND numpy_random are persistence
        # state that later station positions/colors consume, so a stray numpy draw
        # here would silently shift the game (and survive a python-only check).
        m = _played(0)
        for _ in range(500):
            m.increment_time(17)
        before_py = m.context.python_random.getstate()
        before_np = m.context.numpy_random.bit_generator.state
        offers = generate_offers(
            m._offer_rng_for_current_week(),
            count=OFFERS_PER_WEEK,
            tunnels_bounded=False,
        )
        self.assertEqual(
            m.context.python_random.getstate(),
            before_py,
            "no python_random draw stolen",
        )
        self.assertEqual(
            m.context.numpy_random.bit_generator.state,
            before_np,
            "no numpy_random draw stolen",
        )
        self.assertEqual(len(offers), OFFERS_PER_WEEK)

    def test_calendar_on_has_identical_gameplay_state_to_off(self):
        # The calendar+offer path leaves gameplay byte-identical to a calendar-OFF
        # control at the same step (generation is inert; the hold just freezes).
        on = _step_to_first_boundary(_played(0, calendar=True))
        target = on.steps
        off = _played(0, calendar=False)
        while off.steps < target and not off.is_game_over:
            off.increment_time(17)
        self.assertEqual(off.steps, target)
        self.assertEqual(
            on.context.python_random.getstate(), off.context.python_random.getstate()
        )
        self.assertEqual(
            on.context.numpy_random.bit_generator.state,
            off.context.numpy_random.bit_generator.state,
        )
        self.assertEqual(on.deliveries, off.deliveries)

    def test_offers_are_continue_exact_across_save_load(self):
        # review BLOCKER fix: offers reproduce EXACTLY after a mid-game save/load
        # (README "Continue resumes exactly"), because they derive from the restored
        # gameplay RNG state -- no new persisted state. Cover a NON-ZERO seed too
        # (review MAJOR): deserialize builds a temporary Mediator(seed=0) before
        # restoring RNG, so a derivation accidentally salted by the CONSTRUCTOR seed
        # would stay exact for seed 0 yet DIVERGE for seed 3 -- this catches that.
        for seed in (0, 3):
            straight = _collect_offer_kinds(_played(seed), 3)

            mid = _played(seed)
            while mid.steps < 2500 and not mid.is_game_over:
                mid.increment_time(17)
                if mid.is_week_boundary_pending:
                    mid.resolve_week_boundary()
            self.assertFalse(mid.is_week_boundary_pending, "save off a boundary")
            loaded = deserialize_game(serialize_game(mid))
            loaded.week_calendar = True
            continued = []
            while loaded.week_index < 3 and not loaded.is_game_over:
                loaded.increment_time(17)
                if loaded.is_week_boundary_pending:
                    continued.append(tuple(o.kind.name for o in loaded.current_offers))
                    loaded.resolve_week_boundary()
            # The straight run's weeks that fall AFTER the save point must match.
            self.assertEqual(
                straight[-len(continued) :],
                continued,
                f"offers Continue-exact for seed {seed}",
            )
            self.assertTrue(continued, f"seed {seed} reached a post-save boundary")

    def test_river_pool_frozen_sequence_locks_bounded_order(self):
        # review MINOR: the BOUNDED (4-kind) pool order must be locked behaviorally,
        # not just by set membership -- a LOCOMOTIVE<->CARRIAGE swap in _BOUNDED_POOL
        # must turn this red. Week 3 draws TUNNEL, so the tunnel kind is exercised.
        m = _played(0, map_definition=resolve_map("river", 1))
        self.assertEqual(m.num_tunnels, 3)
        self.assertEqual(_collect_offer_kinds(m, 5), list(_RIVER_SEED0_SEQUENCE))

    def test_no_save_bytes_added(self):
        # GM-10b persists nothing: a serialized doc has no offer keys and the rng
        # block is unchanged (python + numpy only).
        m = _played(0)
        for _ in range(300):
            m.increment_time(17)
        doc = serialize_game(m)
        self.assertNotIn("offers", doc)
        self.assertNotIn("currentOffers", doc)
        self.assertEqual(set(doc["rng"].keys()), {"python", "numpy"})


class TestGM10bRLGatedOff(unittest.TestCase):
    def test_headless_env_never_generates_offers(self):
        env = MiniMetroEnv()
        env.reset(seed=0)
        for _ in range(WEEK_LENGTH_STEPS + 60):
            env.mediator.step_time(17)
        self.assertEqual(env.mediator.current_offers, (), "RL never generates offers")
        self.assertFalse(env.mediator.week_calendar)

    def test_pixel_env_never_generates_offers(self):
        env = PlayerPixelEnv()
        env.reset(seed=0)
        m = env._mediator
        for _ in range(WEEK_LENGTH_STEPS + 60):
            m.step_time(17)
        self.assertEqual(m.current_offers, (), "the pixel env never generates offers")


class TestGM10bModalRender(unittest.TestCase):
    def _frame(self, offers, week_index=3):
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill((0, 0, 0))
        draw_offer_screen(surface, week_index, offers)
        return pygame.image.tobytes(surface, "RGB")

    def _text_pixels(self, offers):
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill((0, 0, 0))
        draw_offer_screen(surface, 3, offers)
        arr = pygame.surfarray.array3d(surface)
        return int(np.count_nonzero((arr == game_over_text_color).all(axis=2)))

    def test_offers_change_the_frame_and_each_label_contributes(self):
        two = (describe(OfferKind.NEW_LINE), describe(OfferKind.LOCOMOTIVE))
        one = (describe(OfferKind.NEW_LINE),)
        none = self._frame(())
        self.assertNotEqual(self._frame(one), none, "the first label renders")
        self.assertNotEqual(
            self._frame(two), self._frame(one), "the second label renders"
        )

    def test_label_glyphs_are_actually_painted_not_just_the_panel(self):
        # review MAJOR: offer COUNT alone moves the panel/heading geometry, so a
        # "frame changed" check passes even if NO label glyph is blitted. Count the
        # TEXT-color pixels: offers must add glyph pixels BEYOND the heading+Continue
        # text a no-offer frame already has. Removing the label blit turns this red.
        two = (describe(OfferKind.NEW_LINE), describe(OfferKind.LOCOMOTIVE))
        self.assertGreater(
            self._text_pixels(two),
            self._text_pixels(()),
            "the offer label glyphs paint text pixels the panel alone does not",
        )

    def test_render_is_byte_stable_on_repeat(self):
        offers = (describe(OfferKind.NEW_LINE), describe(OfferKind.CARRIAGE))
        first = self._frame(offers)
        self.assertEqual(self._frame(offers), first, "a fresh redraw is identical")
        # Idempotent over EXISTING chrome too (opaque panel convention): drawing again
        # onto the SAME surface leaves it byte-identical.
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill((0, 0, 0))
        draw_offer_screen(surface, 3, offers)
        draw_offer_screen(surface, 3, offers)
        self.assertEqual(pygame.image.tobytes(surface, "RGB"), first)


class TestGM10bImportSafety(unittest.TestCase):
    def test_offers_module_imports_without_pygame(self):
        # review MINOR: actually VERIFY the import-safety contract -- assert pygame
        # was NOT pulled in (a bare `import offers; print(...)` would pass even if
        # offers imported pygame).
        code = (
            "import sys; sys.path.insert(0, r'%s'); import offers; "
            "assert 'pygame' not in sys.modules, 'offers must stay pygame-free'; "
            "print(offers.OfferKind.NEW_LINE.value)" % _SRC
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "new_line")


if __name__ == "__main__":
    unittest.main()
