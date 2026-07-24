"""GM-10c contract: week-boundary offer CHOICE CONTROLS (D-043).

The GM-10b read-only offer preview becomes interactive: the modal shows one button
per offer; an armed down->up on a button chooses that offer, and
`Mediator.resolve_week_boundary(offer)` applies it (via a per-kind dispatch) then
clears + releases the week pause. The per-kind EFFECTS are GM-10d-g -- in GM-10c the
dispatch arms are no-op stubs, so choosing changes NO game state and is Continue-safe
with no new persisted bytes.
"""

from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np
import pygame

from app_controller import AppController, AppScreen
from config import game_over_text_color, screen_height, screen_width
from event.mouse import MouseEvent
from event.type import MouseEventType
from geometry.point import Point
from mediator import Mediator
from offers import OfferKind, describe
from save_game import serialize_game
from ui.menu_screens import draw_offer_screen, offer_menu_layout

pygame.init()

_INERT_ATTRS = (
    "deliveries",
    "line_credits",
    "num_metros",
    "num_carriages",
    "available_locomotives",
    "available_carriages",
    "purchased_num_paths",
    "unlocked_num_paths",
    "unlocked_num_stations",
    "num_tunnels",
    "consumed_tunnels",
    # non-serialized RUNTIME state (review MAJOR: not in serialize_game, so a save-doc
    # check alone would miss a mutation touching these):
    "current_offers",
    "week_calendar",
    "is_paused",
    "is_game_over",
    "steps",
    "time_ms",
    "game_speed_multiplier",
)


class _ChoiceSession:
    def __init__(self):
        self.dispatched = []

    def dispatch(self, event):
        self.dispatched.append(event)


class _ChoiceMediator:
    def __init__(self, offers):
        self.is_game_over = False
        self._pending = True
        self.week_index = 1
        self.current_offers = offers
        self.applied = []

    @property
    def is_week_boundary_pending(self):
        return self._pending

    def resolve_week_boundary(self, offer=None):
        self._pending = False
        self.applied.append(offer)

    def hold_pause_reason(self, reason):
        pass

    def release_pause_reason(self, reason):
        pass


def _offer_controller(offers=("A", "B")):
    session = _ChoiceSession()
    mediator = _ChoiceMediator(offers)

    def build_game(map_id="classic"):
        return mediator, SimpleNamespace(), session

    controller = AppController(build_game, start_state=AppScreen.PLAYING)
    controller.mediator = mediator
    controller.session = session
    controller.reconcile_week_boundary()  # promote PLAYING -> OFFER
    return controller, mediator


def _rect(mediator, key):
    return offer_menu_layout(screen_width, screen_height, len(mediator.current_offers))[
        key
    ]


def _down(controller, rect):
    controller.handle_event(
        MouseEvent(MouseEventType.MOUSE_DOWN, Point(rect.centerx, rect.centery))
    )


def _up(controller, rect):
    controller.handle_event(
        MouseEvent(MouseEventType.MOUSE_UP, Point(rect.centerx, rect.centery))
    )


class TestGM10cSelectionControls(unittest.TestCase):
    def test_arming_an_offer_button_chooses_that_offer(self):
        for index, token in ((0, "A"), (1, "B")):
            controller, mediator = _offer_controller(("A", "B"))
            self.assertEqual(controller.state, AppScreen.OFFER)
            rect = _rect(mediator, f"offer_{index}")
            _down(controller, rect)
            _up(controller, rect)
            self.assertEqual(controller.state, AppScreen.PLAYING)
            self.assertEqual(
                mediator.applied,
                [token],
                f"offer_{index} chose current_offers[{index}]",
            )

    def test_a_bare_release_does_not_choose(self):
        controller, mediator = _offer_controller(("A", "B"))
        rect = _rect(mediator, "offer_0")
        _up(controller, rect)  # no matching in-offer press
        self.assertEqual(controller.state, AppScreen.OFFER)
        self.assertEqual(mediator.applied, [])

    def test_a_mismatched_release_does_not_choose_and_disarms(self):
        # review MAJOR: down offer_0 -> up offer_1 must not choose AND must DISARM (the
        # up clears the arm before the match check). A "clear after the match guard"
        # mutant leaves offer_0 armed, so a LATER bare up on offer_0 wrongly chooses it.
        controller, mediator = _offer_controller(("A", "B"))
        _down(controller, _rect(mediator, "offer_0"))
        _up(controller, _rect(mediator, "offer_1"))  # mismatch: no choice
        self.assertEqual(controller.state, AppScreen.OFFER)
        self.assertEqual(mediator.applied, [])
        # A subsequent BARE up on the originally-armed button must NOT choose.
        _up(controller, _rect(mediator, "offer_0"))
        self.assertEqual(controller.state, AppScreen.OFFER, "the mismatch disarmed")
        self.assertEqual(mediator.applied, [])

    def test_a_single_offer_renders_one_button_that_chooses_it(self):
        controller, mediator = _offer_controller(("solo",))
        rect = _rect(mediator, "offer_0")
        _down(controller, rect)
        _up(controller, rect)
        self.assertEqual(controller.state, AppScreen.PLAYING)
        self.assertEqual(mediator.applied, ["solo"])


class TestGM10cApplyOffer(unittest.TestCase):
    def test_resolve_with_an_offer_applies_it_then_clears(self):
        m = Mediator(seed=0)
        m.week_calendar = True
        while not m.is_week_boundary_pending:
            m.increment_time(17)
        offer = m.current_offers[0]
        applied = []
        m._apply_offer = lambda o: applied.append(o)  # spy
        m.resolve_week_boundary(offer)
        self.assertEqual(applied, [offer], "the chosen offer was applied")
        self.assertEqual(m.current_offers, (), "offers cleared after resolve")
        self.assertFalse(m.is_week_boundary_pending, "pause released")

    def test_apply_runs_before_clear_and_before_release(self):
        # review MAJOR/NIT: pin the full apply -> clear -> release order. Capture, AT
        # apply time, both current_offers (a clear-before-apply mutant empties it) and
        # is_week_boundary_pending (a release-before-apply mutant flips it False, which
        # would expose a future throwing effect to an already-released boundary).
        m = Mediator(seed=0)
        m.week_calendar = True
        while not m.is_week_boundary_pending:
            m.increment_time(17)
        captured = []
        m._apply_offer = lambda o: captured.append(
            (tuple(m.current_offers), m.is_week_boundary_pending)
        )
        week_offers = tuple(m.current_offers)
        self.assertNotEqual(week_offers, (), "sanity: the week had offers")
        m.resolve_week_boundary(week_offers[0])
        self.assertEqual(
            captured,
            [(week_offers, True)],
            "apply saw the offers present AND the boundary still held (before clear+release)",
        )
        self.assertEqual(m.current_offers, (), "cleared after apply")
        self.assertFalse(m.is_week_boundary_pending, "released after apply")

    def test_resolve_with_no_offer_clears_without_applying(self):
        # The window-close path calls resolve_week_boundary() with no choice.
        m = Mediator(seed=0)
        m.week_calendar = True
        while not m.is_week_boundary_pending:
            m.increment_time(17)
        applied = []
        m._apply_offer = lambda o: applied.append(o)
        m.resolve_week_boundary()
        self.assertEqual(applied, [], "no offer -> nothing applied")
        self.assertEqual(m.current_offers, ())
        self.assertFalse(m.is_week_boundary_pending)

    def test_applying_a_stub_offer_kind_is_state_inert(self):
        # The still-STUB kinds (GM-10e/f/g: locomotive/carriage/tunnel) must change NO
        # game state and no serialized byte. review MAJOR: check PER-KIND on a FRESH
        # mediator (so compensating cross-kind mutations cannot cancel) and over runtime
        # state beyond the save doc. (NEW_LINE now grants a line -- GM-10d, tested in
        # test_gm10d_line.py.) A real effect on a stub kind turns red.
        stub_kinds = (OfferKind.LOCOMOTIVE, OfferKind.CARRIAGE, OfferKind.TUNNEL)
        for kind in stub_kinds:
            m = Mediator(seed=0)
            for _ in range(300):
                m.increment_time(17)
            before = {attr: getattr(m, attr) for attr in _INERT_ATTRS}
            before_doc = serialize_game(m)
            m._apply_offer(describe(kind))
            after = {attr: getattr(m, attr) for attr in _INERT_ATTRS}
            self.assertEqual(after, before, f"{kind.name} apply moved runtime state")
            self.assertEqual(
                serialize_game(m), before_doc, f"{kind.name} apply moved a save byte"
            )

    def test_apply_offer_handles_every_kind(self):
        m = Mediator(seed=0)
        for kind in OfferKind:
            m._apply_offer(describe(kind))  # must not raise

    def test_apply_offer_rejects_an_unknown_kind(self):
        m = Mediator(seed=0)
        forged = SimpleNamespace(kind="not-a-kind", label="?")
        with self.assertRaisesRegex(ValueError, "no effect handler for offer kind"):
            m._apply_offer(forged)


class TestGM10cRender(unittest.TestCase):
    def _text_pixels(self, offers):
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill((0, 0, 0))
        draw_offer_screen(surface, 3, offers)
        arr = pygame.surfarray.array3d(surface)
        return int(np.count_nonzero((arr == game_over_text_color).all(axis=2)))

    def test_each_button_shows_its_own_label_over_counts_one_to_four(self):
        # review MAJOR: cover 1..4 offers (not just 2); assert every button rect is
        # painted, every button shows its OWN (distinct) label -- painting offer 0's
        # label on every button collapses the regions to a set of size 1 -- and all
        # rects are pairwise disjoint. Dropping offer_2/offer_3 leaves a rect blank.
        pool = tuple(describe(k) for k in OfferKind)  # four distinct labels
        for count in (1, 2, 3, 4):
            offers = pool[:count]
            layout = offer_menu_layout(screen_width, screen_height, count)
            rects = [layout[f"offer_{i}"] for i in range(count)]
            surface = pygame.Surface((screen_width, screen_height))
            surface.fill((0, 0, 0))
            draw_offer_screen(surface, 3, offers)
            arr = pygame.surfarray.array3d(surface)
            regions = []
            for index, rect in enumerate(rects):
                region = arr[rect.left : rect.right, rect.top : rect.bottom]
                self.assertTrue(
                    (region != 0).any(), f"count={count} offer_{index} not painted"
                )
                regions.append(region.tobytes())
            self.assertEqual(
                len(set(regions)), count, f"count={count}: each button its own label"
            )
            for i in range(count):
                for j in range(i + 1, count):
                    self.assertFalse(
                        rects[i].colliderect(rects[j]),
                        f"count={count}: offer_{i}/offer_{j} overlap",
                    )

    def test_offer_labels_add_glyph_pixels_and_render_is_byte_stable(self):
        two = (describe(OfferKind.NEW_LINE), describe(OfferKind.LOCOMOTIVE))
        self.assertGreater(
            self._text_pixels(two), self._text_pixels(()), "offer labels paint glyphs"
        )
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill((0, 0, 0))
        draw_offer_screen(surface, 3, two)
        first = pygame.image.tobytes(surface, "RGB")
        draw_offer_screen(surface, 3, two)  # idempotent over existing chrome
        self.assertEqual(pygame.image.tobytes(surface, "RGB"), first)


if __name__ == "__main__":
    unittest.main()
