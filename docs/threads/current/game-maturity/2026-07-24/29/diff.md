# GM-10c week-boundary offer CHOICE CONTROLS — implementation diff

Source: mediator.py (resolve_week_boundary(offer=None) + _apply_offer no-op match-dispatch), menu_screens.py (offer_menu_layout(width,height,count) → one button per offer; draw_offer_screen paints them), app_controller.py (_handle_offer arms/routes offer buttons), main.py (OFFER-render + QUIT comments). Tests: test_gm10c_choice.py (NEW: selection routing/arming-disarm/apply-order/per-kind-inertness/label-binding render) + test_gm10a_calendar.py (arming test + _FakeMediator/_LoopMediator migrated). Docs: D-043, README, GAME_RULES, ARCHITECTURE, PROGRESS.

## Production source
```diff
diff --git a/src/app_controller.py b/src/app_controller.py
index 07f1ecc..fce1768 100644
--- a/src/app_controller.py
+++ b/src/app_controller.py
@@ -324,11 +324,12 @@ class AppController:
             self._open_settings(AppScreen.PAUSE_MENU)

     def _handle_offer(self, event: object) -> None:
-        # GM-10a (D-041): the week-boundary modal's single Continue control is
-        # ARMED (a down+up on the SAME control) so a stale gameplay mouse-up that
-        # crossed the boundary cannot dismiss it (review MAJOR). Continue resolves
-        # the week and resumes PLAYING. GM-10c replaces Continue with the offer.
-        layout = offer_menu_layout(screen_width, screen_height)
+        # GM-10c (D-043): the week-boundary modal shows one button per offer; each is
+        # ARMED (a down+up on the SAME button) so a stale gameplay mouse-up that
+        # crossed the boundary cannot choose (the GM-10a arming discipline). An armed
+        # click on `offer_i` chooses current_offers[i]: resolve applies it and resumes.
+        offers = self.mediator.current_offers
+        layout = offer_menu_layout(screen_width, screen_height, len(offers))
         pressed = _mouse_down_position(event)
         if pressed is not None:
             self._armed_menu_control = next(
@@ -340,8 +341,15 @@ class AppController:
             return
         armed = self._armed_menu_control
         self._armed_menu_control = None
-        if armed == "continue" and _clicked(layout, "continue", position):
-            self.mediator.resolve_week_boundary()
+        if armed is None or not _clicked(layout, armed, position):
+            return
+        # The layout keys are exactly offer_0..offer_{len-1} and the sim is frozen
+        # (offers unchanged between press and release), so `armed` is always a live
+        # key and the parsed index is in range; the bound check is a belt-and-braces
+        # guard on the `offers[index]` access, never expected to fire.
+        index = int(armed.removeprefix("offer_"))
+        if index < len(offers):
+            self.mediator.resolve_week_boundary(offers[index])
             self.state = AppScreen.PLAYING

     def _handle_title(self, event: object) -> None:
diff --git a/src/main.py b/src/main.py
index ff65087..a6595ed 100644
--- a/src/main.py
+++ b/src/main.py
@@ -329,9 +329,10 @@ def run_game(
                 # boundary, drop a finished run's save, and touch nothing on the
                 # title screen (nor for a non-game controller).
                 if controller.state is AppScreen.OFFER:
-                    # Closing mid-offer (GM-10a): resolve the week (there is no
-                    # choice yet) and autosave the resumed game, so Continue reloads
-                    # past the boundary. Mid-offer persistence proper is GM-10h.
+                    # Closing mid-offer (GM-10a): resolve the week with NO choice (the
+                    # no-arg forced resolve -- the player did not pick an offer) and
+                    # autosave the resumed game, so Continue reloads past the boundary.
+                    # Mid-offer / applied-offer persistence proper is GM-10h.
                     controller.mediator.resolve_week_boundary()
                     write_autosave(controller.mediator)
                 elif controller.state in (AppScreen.PLAYING, AppScreen.PAUSE_MENU):
@@ -429,8 +430,8 @@ def run_game(
                 if overlay is not None:
                     draw_tutorial_overlay(game_surface, *overlay)
             elif state == AppScreen.OFFER:
-                # The week-boundary modal over the frozen game frame (GM-10a); the
-                # week's upgrade offers are previewed read-only (GM-10b).
+                # The week-boundary modal over the frozen game frame (GM-10a): the
+                # week's offers (GM-10b) as one selectable button each (GM-10c).
                 draw_offer_screen(
                     game_surface,
                     controller.mediator.week_index,
diff --git a/src/mediator.py b/src/mediator.py
index 042b648..5d06bf4 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -50,7 +50,7 @@ from graph.graph_algo import bfs, build_station_nodes_dict
 from graph.node import Node
 from input_coordinator import InputCoordinator
 from maps import CLASSIC, MapDefinition
-from offers import Offer, generate_offers
+from offers import Offer, OfferKind, generate_offers
 from passenger_flow import PassengerFlow
 from path_handles import PathEditSelection
 from path_lifecycle import PathLifecycle
@@ -707,13 +707,33 @@ class Mediator:
         # True while the calendar is paused at a week boundary awaiting a resolve.
         return _WEEK_REASON in self._pause_reason_store(_WEEK_REASON)

-    def resolve_week_boundary(self) -> None:
-        # Continue past a week boundary: clear the week's offers and release the
-        # pause. GM-10b generates offers (below); GM-10c will APPLY the chosen one
-        # here, BEFORE clearing, and GM-10h reconciles applied-offer persistence.
+    def resolve_week_boundary(self, offer: Offer | None = None) -> None:
+        # Continue past a week boundary: APPLY the chosen offer (GM-10c), then clear
+        # the week's offers and release the pause. A None offer is a forced resolve
+        # with no choice (the window-close path in main.run_game), which applies
+        # nothing. GM-10h reconciles applied-offer persistence across Continue.
+        if offer is not None:
+            self._apply_offer(offer)
         self.current_offers = ()
         self.release_pause_reason(_WEEK_REASON)

+    def _apply_offer(self, offer: Offer) -> None:
+        # GM-10c dispatches the chosen offer to its per-kind effect. The effects
+        # themselves land in GM-10d-g (line/locomotive/carriage/tunnel) -- each arm
+        # is a no-op here, so GM-10c changes NO game state and is Continue-safe with
+        # no new persisted bytes. A future kind without a handler must fail loud.
+        match offer.kind:
+            case OfferKind.NEW_LINE:
+                pass  # GM-10d: grant a free line (via purchased_num_paths, persisted)
+            case OfferKind.LOCOMOTIVE:
+                pass  # GM-10e: +1 num_metros (needs the _require_running_config pin relaxed / GM-10h)
+            case OfferKind.CARRIAGE:
+                pass  # GM-10f: +1 num_carriages (same pin as locomotives)
+            case OfferKind.TUNNEL:
+                pass  # GM-10g: +1 tunnel budget (needs a persisted bonus / GM-10h)
+            case _:
+                raise ValueError(f"no effect handler for offer kind {offer.kind!r}")
+
     def _offer_rng_for_current_week(self) -> random.Random:
         # GM-10b (D-042): a dedicated per-week offer RNG, derived READ-ONLY from the
         # already-persisted gameplay RNG state + week_index. `getstate()` consumes no
diff --git a/src/ui/menu_screens.py b/src/ui/menu_screens.py
index 1b95872..d3cb86a 100644
--- a/src/ui/menu_screens.py
+++ b/src/ui/menu_screens.py
@@ -31,8 +31,6 @@ _BEST_INDICATOR_TEXT = "NEW BEST"
 _HEADING_FONT_SIZE = 96
 _TUTORIAL_SUBLINE_FONT_SIZE = 26
 _HEADING_GAP = 60
-# Gap between the GM-10b offer preview panel and the Continue button below it.
-_OFFER_GAP = 24
 # Settings rows carry value labels ("Reduced Motion: On"), so they use a wider
 # button than the menu stacks; centering is on the screen midline regardless.
 _SETTINGS_BUTTON_WIDTH = 620
@@ -195,55 +193,39 @@ def draw_notice(surface: pygame.Surface, message: str) -> None:
     surface.blit(text, text.get_rect(center=banner.center))


-def offer_menu_layout(width: int, height: int) -> dict[str, pygame.Rect]:
-    """Hit-test rects for the GM-10a week-boundary modal (a single Continue)."""
+def offer_menu_layout(width: int, height: int, count: int) -> dict[str, pygame.Rect]:
+    """Hit-test rects for the GM-10c week-boundary modal: one button per offer.

-    # One centred button in the lower half, mirroring the pause/settings stacks
-    # so the shared arming + _clicked helpers apply unchanged.
-    return _stacked_buttons(width, ("continue",), height // 2)
+    ``count`` is the number of offers (``len(mediator.current_offers)``). The keys
+    are ``offer_0``..``offer_{count-1}``, a centred stack in the lower half that
+    reuses the shared arming + `_clicked` helpers unchanged. ``count == 0`` yields
+    an empty layout (defensive; the modal is only shown with offers present).
+    """
+
+    return _stacked_buttons(
+        width, tuple(f"offer_{i}" for i in range(count)), height // 2
+    )


 def draw_offer_screen(
     surface: pygame.Surface, week_index: int, offers: Sequence[Offer]
 ) -> None:
-    """Paint the deterministic week-boundary modal (GM-10a + GM-10b).
+    """Paint the deterministic week-boundary modal (GM-10a/b/c).

-    A banner, the week's upgrade offers previewed read-only (GM-10b -- choosing is
-    GM-10c), and Continue. The offer labels sit on an opaque panel painted in the
-    same call, so repeated frame draws over existing chrome stay byte-identical
-    (the module-wide convention shared with _draw_button/_draw_heading).
+    A banner and one SELECTABLE button per upgrade offer (GM-10c -- clicking one
+    chooses and applies it). Each button is opaque chrome painted in the same call,
+    so repeated frame draws over existing chrome stay byte-identical (the module
+    convention shared with _draw_button/_draw_heading).
     """

     width, height = surface.get_size()
-    layout = offer_menu_layout(width, height)
-    continue_rect = layout["continue"]
-    font = _font(font_name, game_over_hint_font_size)
-    rendered = [
-        font.render(offer.label, True, game_over_text_color) for offer in offers
-    ]
-    line_height = max((text.get_height() for text in rendered), default=0) + 12
-    block_height = line_height * len(rendered)
-    offers_bottom = continue_rect.top - _OFFER_GAP
-    offers_top = offers_bottom - block_height
-    _draw_heading(
-        surface, width, offers_top - _HEADING_GAP, f"Week {week_index} complete"
+    layout = offer_menu_layout(width, height, len(offers))
+    heading_bottom = (
+        layout["offer_0"].top - _HEADING_GAP if offers else height // 2 - _HEADING_GAP
     )
-    if rendered:
-        panel_width = max(text.get_width() for text in rendered) + 60
-        panel = pygame.Rect(0, 0, panel_width, block_height + 12)
-        panel.center = (width // 2, offers_top + block_height // 2)
-        pygame.draw.rect(surface, game_over_button_color, panel, border_radius=10)
-        pygame.draw.rect(
-            surface,
-            game_over_button_border_color,
-            panel,
-            game_over_button_border_width,
-            border_radius=10,
-        )
-        for index, text in enumerate(rendered):
-            centre_y = offers_top + line_height * index + line_height // 2
-            surface.blit(text, text.get_rect(center=(width // 2, centre_y)))
-    _draw_button(surface, continue_rect, "Continue")
+    _draw_heading(surface, width, heading_bottom, f"Week {week_index} complete")
+    for index, offer in enumerate(offers):
+        _draw_button(surface, layout[f"offer_{index}"], offer.label)


 def draw_tutorial_overlay(
```

## Tests
```diff
diff --git a/test/test_gm10a_calendar.py b/test/test_gm10a_calendar.py
index 7d1bb3b..6c211c1 100644
--- a/test/test_gm10a_calendar.py
+++ b/test/test_gm10a_calendar.py
@@ -182,14 +182,19 @@ class _FakeMediator:
         self.resolved = 0
         self.week_index = 1
         self.held = []
+        # GM-10c: two opaque offer tokens so the modal renders two selectable
+        # buttons; the controller passes the chosen one back to resolve.
+        self.current_offers = ("offer-a", "offer-b")
+        self.applied = []

     @property
     def is_week_boundary_pending(self):
         return self._week_pending

-    def resolve_week_boundary(self):
+    def resolve_week_boundary(self, offer=None):
         self._week_pending = False
         self.resolved += 1
+        self.applied.append(offer)

     def hold_pause_reason(self, reason):
         self.held.append(reason)
@@ -281,21 +286,25 @@ class TestGM10aOfferArming(unittest.TestCase):
             MouseEvent(MouseEventType.MOUSE_DOWN, Point(rect.centerx, rect.centery))
         )

-    def test_continue_requires_an_offer_local_down_up_pair(self):
-        # review MAJOR: a bare gameplay mouse-up that crossed the boundary must NOT
-        # dismiss the offer -- only an in-offer down->up on Continue resolves it.
+    def test_offer_choice_requires_a_local_down_up_pair(self):
+        # review MAJOR (GM-10a arming, GM-10c offer buttons): a bare gameplay mouse-up
+        # that crossed the boundary must NOT choose -- only an in-offer down->up on an
+        # offer button chooses it, resolves the week, and resumes PLAYING.
         controller, mediator, session = _offer_controller()
         controller.reconcile_week_boundary()
         self.assertEqual(controller.state, AppScreen.OFFER)
-        rect = offer_menu_layout(screen_width, screen_height)["continue"]
+        rect = offer_menu_layout(
+            screen_width, screen_height, len(mediator.current_offers)
+        )["offer_0"]
         # A bare release (no matching in-offer press) is a no-op.
         self._up(controller, rect)
         self.assertEqual(controller.state, AppScreen.OFFER, "a bare release is ignored")
         self.assertEqual(mediator.resolved, 0)
-        # An armed press+release resolves the week and resumes PLAYING.
+        # An armed press+release chooses offer 0, resolves, and resumes PLAYING.
         self._down(controller, rect)
         self._up(controller, rect)
         self.assertEqual(controller.state, AppScreen.PLAYING)
+        self.assertEqual(mediator.applied, ["offer-a"], "chose current_offers[0]")
         self.assertEqual(mediator.resolved, 1)


@@ -396,7 +405,7 @@ class _LoopMediator:
     def is_week_boundary_pending(self):
         return self._pending

-    def resolve_week_boundary(self):
+    def resolve_week_boundary(self, offer=None):
         self._pending = False
         self.resolved += 1

diff --git a/test/test_gm10c_choice.py b/test/test_gm10c_choice.py
new file mode 100644
index 0000000..048f6de
--- a/test/test_gm10c_choice.py
+++ b/test/test_gm10c_choice.py
@@ -0,0 +1,301 @@
+"""GM-10c contract: week-boundary offer CHOICE CONTROLS (D-043).
+
+The GM-10b read-only offer preview becomes interactive: the modal shows one button
+per offer; an armed down->up on a button chooses that offer, and
+`Mediator.resolve_week_boundary(offer)` applies it (via a per-kind dispatch) then
+clears + releases the week pause. The per-kind EFFECTS are GM-10d-g -- in GM-10c the
+dispatch arms are no-op stubs, so choosing changes NO game state and is Continue-safe
+with no new persisted bytes.
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import unittest
+from types import SimpleNamespace
+
+sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
+
+import numpy as np
+import pygame
+
+from app_controller import AppController, AppScreen
+from config import game_over_text_color, screen_height, screen_width
+from event.mouse import MouseEvent
+from event.type import MouseEventType
+from geometry.point import Point
+from mediator import Mediator
+from offers import OfferKind, describe
+from save_game import serialize_game
+from ui.menu_screens import draw_offer_screen, offer_menu_layout
+
+pygame.init()
+
+_INERT_ATTRS = (
+    "deliveries",
+    "line_credits",
+    "num_metros",
+    "num_carriages",
+    "available_locomotives",
+    "available_carriages",
+    "purchased_num_paths",
+    "unlocked_num_paths",
+    "unlocked_num_stations",
+    "num_tunnels",
+    "consumed_tunnels",
+    # non-serialized RUNTIME state (review MAJOR: not in serialize_game, so a save-doc
+    # check alone would miss a mutation touching these):
+    "current_offers",
+    "week_calendar",
+    "is_paused",
+    "is_game_over",
+    "steps",
+    "time_ms",
+    "game_speed_multiplier",
+)
+
+
+class _ChoiceSession:
+    def __init__(self):
+        self.dispatched = []
+
+    def dispatch(self, event):
+        self.dispatched.append(event)
+
+
+class _ChoiceMediator:
+    def __init__(self, offers):
+        self.is_game_over = False
+        self._pending = True
+        self.week_index = 1
+        self.current_offers = offers
+        self.applied = []
+
+    @property
+    def is_week_boundary_pending(self):
+        return self._pending
+
+    def resolve_week_boundary(self, offer=None):
+        self._pending = False
+        self.applied.append(offer)
+
+    def hold_pause_reason(self, reason):
+        pass
+
+    def release_pause_reason(self, reason):
+        pass
+
+
+def _offer_controller(offers=("A", "B")):
+    session = _ChoiceSession()
+    mediator = _ChoiceMediator(offers)
+
+    def build_game(map_id="classic"):
+        return mediator, SimpleNamespace(), session
+
+    controller = AppController(build_game, start_state=AppScreen.PLAYING)
+    controller.mediator = mediator
+    controller.session = session
+    controller.reconcile_week_boundary()  # promote PLAYING -> OFFER
+    return controller, mediator
+
+
+def _rect(mediator, key):
+    return offer_menu_layout(screen_width, screen_height, len(mediator.current_offers))[
+        key
+    ]
+
+
+def _down(controller, rect):
+    controller.handle_event(
+        MouseEvent(MouseEventType.MOUSE_DOWN, Point(rect.centerx, rect.centery))
+    )
+
+
+def _up(controller, rect):
+    controller.handle_event(
+        MouseEvent(MouseEventType.MOUSE_UP, Point(rect.centerx, rect.centery))
+    )
+
+
+class TestGM10cSelectionControls(unittest.TestCase):
+    def test_arming_an_offer_button_chooses_that_offer(self):
+        for index, token in ((0, "A"), (1, "B")):
+            controller, mediator = _offer_controller(("A", "B"))
+            self.assertEqual(controller.state, AppScreen.OFFER)
+            rect = _rect(mediator, f"offer_{index}")
+            _down(controller, rect)
+            _up(controller, rect)
+            self.assertEqual(controller.state, AppScreen.PLAYING)
+            self.assertEqual(
+                mediator.applied,
+                [token],
+                f"offer_{index} chose current_offers[{index}]",
+            )
+
+    def test_a_bare_release_does_not_choose(self):
+        controller, mediator = _offer_controller(("A", "B"))
+        rect = _rect(mediator, "offer_0")
+        _up(controller, rect)  # no matching in-offer press
+        self.assertEqual(controller.state, AppScreen.OFFER)
+        self.assertEqual(mediator.applied, [])
+
+    def test_a_mismatched_release_does_not_choose_and_disarms(self):
+        # review MAJOR: down offer_0 -> up offer_1 must not choose AND must DISARM (the
+        # up clears the arm before the match check). A "clear after the match guard"
+        # mutant leaves offer_0 armed, so a LATER bare up on offer_0 wrongly chooses it.
+        controller, mediator = _offer_controller(("A", "B"))
+        _down(controller, _rect(mediator, "offer_0"))
+        _up(controller, _rect(mediator, "offer_1"))  # mismatch: no choice
+        self.assertEqual(controller.state, AppScreen.OFFER)
+        self.assertEqual(mediator.applied, [])
+        # A subsequent BARE up on the originally-armed button must NOT choose.
+        _up(controller, _rect(mediator, "offer_0"))
+        self.assertEqual(controller.state, AppScreen.OFFER, "the mismatch disarmed")
+        self.assertEqual(mediator.applied, [])
+
+    def test_a_single_offer_renders_one_button_that_chooses_it(self):
+        controller, mediator = _offer_controller(("solo",))
+        rect = _rect(mediator, "offer_0")
+        _down(controller, rect)
+        _up(controller, rect)
+        self.assertEqual(controller.state, AppScreen.PLAYING)
+        self.assertEqual(mediator.applied, ["solo"])
+
+
+class TestGM10cApplyOffer(unittest.TestCase):
+    def test_resolve_with_an_offer_applies_it_then_clears(self):
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        while not m.is_week_boundary_pending:
+            m.increment_time(17)
+        offer = m.current_offers[0]
+        applied = []
+        m._apply_offer = lambda o: applied.append(o)  # spy
+        m.resolve_week_boundary(offer)
+        self.assertEqual(applied, [offer], "the chosen offer was applied")
+        self.assertEqual(m.current_offers, (), "offers cleared after resolve")
+        self.assertFalse(m.is_week_boundary_pending, "pause released")
+
+    def test_apply_runs_before_clear_and_before_release(self):
+        # review MAJOR/NIT: pin the full apply -> clear -> release order. Capture, AT
+        # apply time, both current_offers (a clear-before-apply mutant empties it) and
+        # is_week_boundary_pending (a release-before-apply mutant flips it False, which
+        # would expose a future throwing effect to an already-released boundary).
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        while not m.is_week_boundary_pending:
+            m.increment_time(17)
+        captured = []
+        m._apply_offer = lambda o: captured.append(
+            (tuple(m.current_offers), m.is_week_boundary_pending)
+        )
+        week_offers = tuple(m.current_offers)
+        self.assertNotEqual(week_offers, (), "sanity: the week had offers")
+        m.resolve_week_boundary(week_offers[0])
+        self.assertEqual(
+            captured,
+            [(week_offers, True)],
+            "apply saw the offers present AND the boundary still held (before clear+release)",
+        )
+        self.assertEqual(m.current_offers, (), "cleared after apply")
+        self.assertFalse(m.is_week_boundary_pending, "released after apply")
+
+    def test_resolve_with_no_offer_clears_without_applying(self):
+        # The window-close path calls resolve_week_boundary() with no choice.
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        while not m.is_week_boundary_pending:
+            m.increment_time(17)
+        applied = []
+        m._apply_offer = lambda o: applied.append(o)
+        m.resolve_week_boundary()
+        self.assertEqual(applied, [], "no offer -> nothing applied")
+        self.assertEqual(m.current_offers, ())
+        self.assertFalse(m.is_week_boundary_pending)
+
+    def test_applying_each_offer_is_state_inert(self):
+        # GM-10c is a no-op dispatch: applying a kind must change NO game state and no
+        # serialized byte (effects are GM-10d-g). review MAJOR: check PER-KIND on a
+        # FRESH mediator (so compensating cross-kind mutations cannot cancel) and over
+        # runtime state beyond the save doc. A real effect on any kind turns red.
+        for kind in OfferKind:
+            m = Mediator(seed=0)
+            for _ in range(300):
+                m.increment_time(17)
+            before = {attr: getattr(m, attr) for attr in _INERT_ATTRS}
+            before_doc = serialize_game(m)
+            m._apply_offer(describe(kind))
+            after = {attr: getattr(m, attr) for attr in _INERT_ATTRS}
+            self.assertEqual(after, before, f"{kind.name} apply moved runtime state")
+            self.assertEqual(
+                serialize_game(m), before_doc, f"{kind.name} apply moved a save byte"
+            )
+
+    def test_apply_offer_handles_every_kind(self):
+        m = Mediator(seed=0)
+        for kind in OfferKind:
+            m._apply_offer(describe(kind))  # must not raise
+
+    def test_apply_offer_rejects_an_unknown_kind(self):
+        m = Mediator(seed=0)
+        forged = SimpleNamespace(kind="not-a-kind", label="?")
+        with self.assertRaisesRegex(ValueError, "no effect handler for offer kind"):
+            m._apply_offer(forged)
+
+
+class TestGM10cRender(unittest.TestCase):
+    def _text_pixels(self, offers):
+        surface = pygame.Surface((screen_width, screen_height))
+        surface.fill((0, 0, 0))
+        draw_offer_screen(surface, 3, offers)
+        arr = pygame.surfarray.array3d(surface)
+        return int(np.count_nonzero((arr == game_over_text_color).all(axis=2)))
+
+    def test_each_button_shows_its_own_label_over_counts_one_to_four(self):
+        # review MAJOR: cover 1..4 offers (not just 2); assert every button rect is
+        # painted, every button shows its OWN (distinct) label -- painting offer 0's
+        # label on every button collapses the regions to a set of size 1 -- and all
+        # rects are pairwise disjoint. Dropping offer_2/offer_3 leaves a rect blank.
+        pool = tuple(describe(k) for k in OfferKind)  # four distinct labels
+        for count in (1, 2, 3, 4):
+            offers = pool[:count]
+            layout = offer_menu_layout(screen_width, screen_height, count)
+            rects = [layout[f"offer_{i}"] for i in range(count)]
+            surface = pygame.Surface((screen_width, screen_height))
+            surface.fill((0, 0, 0))
+            draw_offer_screen(surface, 3, offers)
+            arr = pygame.surfarray.array3d(surface)
+            regions = []
+            for index, rect in enumerate(rects):
+                region = arr[rect.left : rect.right, rect.top : rect.bottom]
+                self.assertTrue(
+                    (region != 0).any(), f"count={count} offer_{index} not painted"
+                )
+                regions.append(region.tobytes())
+            self.assertEqual(
+                len(set(regions)), count, f"count={count}: each button its own label"
+            )
+            for i in range(count):
+                for j in range(i + 1, count):
+                    self.assertFalse(
+                        rects[i].colliderect(rects[j]),
+                        f"count={count}: offer_{i}/offer_{j} overlap",
+                    )
+
+    def test_offer_labels_add_glyph_pixels_and_render_is_byte_stable(self):
+        two = (describe(OfferKind.NEW_LINE), describe(OfferKind.LOCOMOTIVE))
+        self.assertGreater(
+            self._text_pixels(two), self._text_pixels(()), "offer labels paint glyphs"
+        )
+        surface = pygame.Surface((screen_width, screen_height))
+        surface.fill((0, 0, 0))
+        draw_offer_screen(surface, 3, two)
+        first = pygame.image.tobytes(surface, "RGB")
+        draw_offer_screen(surface, 3, two)  # idempotent over existing chrome
+        self.assertEqual(pygame.image.tobytes(surface, "RGB"), first)
+
+
+if __name__ == "__main__":
+    unittest.main()
```

## Docs
```diff
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index a62cb80..37b27e5 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -380,6 +380,7 @@ python_mini_metro/
 - GM-09f3 (D-040) COMPLETES GM-09f with the in-game MAP MENU. `AppController` gains `current_map_id` (default `classic`), cycled by an appended title control `map` (`title_layout` appends the `"map"` key so the prior title rects stay byte-identical; `draw_title_screen` gains a `current_map_id` param and paints a `Map: {Name}` button; `main.run_game` threads `controller.current_map_id` into it). The `build_game` seam becomes uniformly `Callable[[str], GameTriple]`: `main.run_game`'s `build_game(map_id)` resolves `maps.map_by_id(map_id)` into `Mediator(map_definition=…)` (every downstream layer was already map-aware, GM-09a–f2). NEW GAME / ENTER build `current_map_id`; RESTART (pause + game-over) rebuilds the CURRENT game's map read live off `self.mediator.map_definition.map_id` via `_restart_current_game` (so restarting a Continued River game gives River even when the picker sits on Lake); Continue installs the SAVED map and never consults the picker; the tutorial stays Classic. Only `main`+`app_controller`+`menu_screens` change; the headless/agent/recursive/RL entries construct `Mediator(map_definition=…)` directly and never meet the title picker.
 - GM-10a (D-041) opens GM-10 with the simulation CALENDAR. `config.WEEK_LENGTH_STEPS` defines a "week" in sim steps; `Mediator.increment_time`, after the COMPLETE tick (post queued-return settlement), holds a new `"week"` pause reason when `mediator.week_calendar` is on, the tick crossed a new boundary, and the run is not game over. `"week"` joins `_PAUSE_REASONS` (frozen by the existing gate; never cleared by Space/speed); `week_index` is a `steps`-derived property and `resolve_week_boundary()` releases the pause. The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it, so RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, and frame-limited/headless runs never pause — the calendar branch is never taken off the human path, so no `env.py`/checkpoint/save change and no determinism risk. The human shell adds `AppScreen.OFFER`: `AppController.reconcile_week_boundary()` (per-frame AFTER `reconcile_game_over`, so a terminal tick wins; cancelling any armed gesture via the pinned letterbox-cancel before switching) promotes a pending boundary to a modal whose armed Continue (`menu_screens.offer_menu_layout`/`draw_offer_screen`) resolves the week; `main` renders it over the frozen frame, resolves-then-autosaves on a mid-offer window close, and consumes the offer frame's audio silently; `save_game._require_quiescent` blocks saving while a boundary is pending. Persistence + the RL observation/offer are deferred to GM-10h/GM-10b.
 - GM-10b (D-042) adds the weekly OFFER GENERATOR. A new dependency-light `src/offers.py` (stdlib-only — `enum`/`dataclasses`/`random`, no pygame/mediator, so it is import-safe on every headless/RL path) owns the data model (`OfferKind`, frozen `Offer`, `describe`) and a PURE `generate_offers(rng, *, count, tunnels_bounded)` that draws `count` DISTINCT kinds via `rng.sample` from an explicitly-ordered pool — the four kinds on a finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC) map. `config.OFFERS_PER_WEEK` (2) sets the count. When `Mediator._maybe_hold_week_boundary` fires (same calendar/crossing/not-game-over gate as the hold), it stores `self.current_offers` from `generate_offers`; `resolve_week_boundary` clears them (GM-10c will APPLY the chosen one here first); `main` passes `current_offers` into `draw_offer_screen`, which previews the labels read-only on an opaque panel (byte-stable on repeat). The offer RNG is a DEDICATED per-week `random.Random` derived READ-ONLY from `context.python_random.getstate()` + `week_index` (sha256 over the repr, cross-process stable) — a deliberate design choice (dual-plan-reviewed): reading the state consumes no gameplay draws (station spawns stay byte-identical) AND, because that gameplay RNG state is already restored exactly on Continue, the same week's offers reproduce byte-exact after save/load with NO new persisted state. So GM-10b adds ZERO save/checkpoint/observation bytes (the `rng` block, exact-key save validation, checkpoint schema, and every frozen fixture are untouched) and never runs off the human path. Applying a choice is GM-10c, per-kind effects GM-10d–g, and applied-offer/replay persistence GM-10h (which must not trail GM-10c). (Adding `offers.py` and editing the runtime `src` files rotates the LIVE RL content fingerprint — `compute_content_fingerprint` hashes all of `src/**` — so a pre-GM-10b manifest fails strict resume/eval by default; EXPECTED and correct for fresh runs, no frozen fixture is repinned since `EXPECTED_LF_TRAINING` pins only `TRAINING_SOURCE_PATHS`, which excludes these files.)
+- GM-10c (D-043) makes the offers SELECTABLE. `menu_screens.offer_menu_layout(width, height, count)` now returns one button rect per offer (keys `offer_0..offer_{count-1}`); `draw_offer_screen` paints each offer as a button. `AppController._handle_offer` arms a button on mouse-down and, on a matching mouse-up (the GM-10a arming discipline, so a stale gameplay release cannot choose), calls `Mediator.resolve_week_boundary(current_offers[i])`. `resolve_week_boundary(offer=None)` gains the optional chosen offer: it dispatches to `Mediator._apply_offer(offer)` (a `match offer.kind` over `OfferKind`, raising a named `ValueError` on an unknown kind) then clears `current_offers` and releases the pause; `None` is a forced resolve with no choice (the `main.run_game` window-close path, unchanged). The per-kind arms are NO-OP stubs in GM-10c — choosing changes NO game state, so it is Continue-safe with ZERO new persisted bytes (the state-inertness is test-locked against the full `serialize_game` doc). The real effects are GM-10d–g: a NEW_LINE grant can flow through the already-persisted `purchased_num_paths` (Continue-safe standalone), while the LOCOMOTIVE/CARRIAGE grants hit `save_load._require_running_config` (which pins `numMetros`/`numCarriages` to config) and the TUNNEL grant needs a persisted bonus, so those must land with GM-10h.
 - `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
 - `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
 - `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
diff --git a/GAME_RULES.md b/GAME_RULES.md
index d60511a..1eeaeb1 100644
--- a/GAME_RULES.md
+++ b/GAME_RULES.md
@@ -157,8 +157,8 @@ This document summarizes the game rules currently implemented in code.
   - R: restart (game-over screen).
   - ESC: exit (game-over screen).
 - The pause menu holds its own pause reason: opening it while SPACE-paused keeps both, and resuming from the menu releases only the menu hold, so the game stays paused until SPACE (or a speed button) clears the user pause. Speed-button selections still clear only the user pause and never the menu hold; the keyboard speed keys only set the speed and never unpause.
-- Weekly calendar (interactive play only): every fixed span of simulation time (a "week") the game pauses at a week boundary and shows a modal; click Continue to resume, and the sim carries on from exactly where it froze with no time backlog. This pause is its own reason — SPACE and the speed buttons cannot dismiss it, and saving is blocked until you Continue (closing the window mid-week resumes the game past the boundary via Continue). The calendar is a human-play feature: headless, RL, tutorial, and frame-limited runs never pause for a week. (GM-10a lays the calendar; the end-of-week upgrade choice arrives in later units.)
-- Weekly offers (interactive play only): the week-boundary modal previews a seeded SET of `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers, drawn from a pool of New Line, +1 Locomotive, +1 Carriage, and +1 Tunnel — the tunnel offer appears only on maps with a finite tunnel budget (never on open CLASSIC, which is unbounded). The offers are fully deterministic: they are generated from a dedicated per-week random stream derived from the game's own RNG state and the week number, so they consume no gameplay randomness (station spawns are byte-identical whether or not offers are generated) and reproduce EXACTLY when you Continue a saved game. GM-10b previews the offers read-only; choosing one to apply arrives in later units (its effect and its cross-Continue persistence with it).
+- Weekly calendar (interactive play only): every fixed span of simulation time (a "week") the game pauses at a week boundary and shows a modal; choosing one of that week's offers (below) resolves the week, and the sim carries on from exactly where it froze with no time backlog. This pause is its own reason — SPACE and the speed buttons cannot dismiss it, and saving is blocked until you resolve the week (closing the window mid-week resolves it with no choice and resumes the game past the boundary). The calendar is a human-play feature: headless, RL, tutorial, and frame-limited runs never pause for a week. (GM-10a lays the calendar; GM-10b generates the offers; GM-10c makes them selectable.)
+- Weekly offers (interactive play only): the week-boundary modal previews a seeded SET of `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers, drawn from a pool of New Line, +1 Locomotive, +1 Carriage, and +1 Tunnel — the tunnel offer appears only on maps with a finite tunnel budget (never on open CLASSIC, which is unbounded). The offers are fully deterministic: they are generated from a dedicated per-week random stream derived from the game's own RNG state and the week number, so they consume no gameplay randomness (station spawns are byte-identical whether or not offers are generated) and reproduce EXACTLY when you Continue a saved game. GM-10b generated the offers; GM-10c makes them SELECTABLE — the modal shows one button per offer, and an armed click (a press and release on the same button, so a stale gameplay release cannot choose) picks that offer, resolves the week, and resumes. The choice is dispatched to a per-kind effect; the effects each kind grants (line/locomotive/carriage/tunnel) are being added incrementally in later units, and closing the window mid-offer resolves with no choice.
 - Autosave: opening the pause menu and Exit to Title each write a single autosave to `saves/autosave.json`, and closing the window mid-run keeps it, so the title screen's Continue reloads the game exactly where you left off (releasing the menu pause, honoring a held SPACE pause). Reaching game over deletes the autosave, so a finished run cannot be Continued; every autosave is best-effort and never blocks play or exit.
 - Tutorial: a coached playthrough reached from the title screen. It runs a real seeded game with on-screen prompts that walk through drawing a line, rerouting it, adding a train, delivering a passenger, overload pressure, pausing, and changing speed; each lesson advances when you actually perform it (overload advances after a few seconds of watching). Press Esc to skip or leave at any point. The tutorial game never ends (so a first-timer cannot lose mid-lesson) and never autosaves or records a high score. It is presentation only and changes no game rules or balance.
 - Settings: a Settings screen, reached from the title or pause menu (Back returns to whichever opened it, and opening it from the pause menu keeps the game paused), toggles fullscreen, steps the master/music/SFX volumes in 25% increments, and toggles reduced motion. Settings persist to `saves/settings.json` and survive restart; fullscreen applies to the live window and reduced motion holds the passenger-warning, station-unlock, and path-button blinks steady while suppressing the snap-blip rings (the master and SFX volumes scale the procedural audio cues). Settings are presentation-only and change no game balance; a missing or corrupt settings file falls back to the defaults and never blocks play.
diff --git a/PROGRESS.md b/PROGRESS.md
index cce089d..dfa0755 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -182,3 +182,4 @@
 - Closed the GM-09c abort-inertness follow-up (`task_384488d0`), fixing the two PRE-EXISTING non-inert traces a cancelled path draft left in `PathLifecycle.abort_path_creation` -- both surfaced by the GM-09c review but deferred there because the obvious fixes broke CLASSIC byte-identity. (1) The transient snap-blips a draft paints as it grows (`add_station_to_path`/`end_path_on_station`) leaked into the canonical checkpoint (serialized raw, pruned only by `increment_time` on expiry), so a headless `MiniMetroEnv` rollout checkpointed a cancelled draft indefinitely; `_paint_creation_snap_blip` now records each painted blip (the tuple `start_snap_blip` actually appends -- `Station.start_snap_blip` now RETURNS it, coupling the receipt to the real append so a non-appending station leaves no phantom) and abort drops exactly those by LAST value-match, which -- since `start_snap_blip` has one caller and only one draft is live -- is provably the draft's own blip even when a removed line's reclaimed-color blip lingers beside it (identity is unusable because `prune_visual_effects` rebuilds the tuples each tick; a color match would erase the survivor). (2) A mid-draft `remove_path` runs `assign_paths_to_buttons`, binding the still-drafting path to a button; abort now detaches that one mapping (`path_to_button.pop` + `PathButton.remove_path` if it still points at the draft) surgically -- NOT a full reassign -- so no colored button points at a removed line. `finish` forgets a committed draft's receipts (no unbounded bookkeeping). Byte-identity is exact and PROVEN by a whole-src HEAD-shadow differential: a drag-then-FINISH (committed line) and the ghost scenario are byte-identical to pre-change HEAD, and only a drag-then-ABORT differs, by exactly the removed draft blips (the button detach is checkpoint-invisible -- `button.path` derefs to `None` either way); `save-v1.json`/`save-v2-classic.json` (which serialize `snapBlips`, empty in the fixtures) and the GM-09a construct/trajectory fingerprints are unmoved. TDD: six red-first tests (fully-inert CLASSIC checkpoint, reclaimed-color collision, an adversarial same-time ordering case that a remove-FIRST would fail, duplicate re-snap, ghost button, no-op-when-unbound guard) plus a component-level abort-detach test; the GM-09c `test_rejected_multistation_creation` was strengthened from RNG-inert to FULLY checkpoint-inert. Triple adversarial review (two harness lanes -- byte-identity + correctness/contract, both HOLD -- and external Codex ultra) because the last three review rounds each caught a byte-identity regression in this exact area; Codex caught a stale-doc regression BOTH harness lanes missed (this ARCHITECTURE.md GM-09c note and the `finish`/`end_path` comments still said abort was "unchanged / left to a follow-up") and drove the receipt-to-append coupling and the commit-time receipt clear. Full `py313` suite green (1484 tests, 12 skips); `path_lifecycle.py` gains three small helpers, no new module.
 - Opened GM-10 with GM-10a, the simulation CALENDAR (D-041) -- the foundation for weekly progression. A "week" is `config.WEEK_LENGTH_STEPS` (1200 ≈ 20s at 1x); `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement), holds a new `"week"` pause reason when the calendar is enabled, a new boundary crossed (`old//W < steps//W`), and not game over. `"week"` joins `_PAUSE_REASONS` (never cleared by Space/speed); `week_index` is `steps`-derived (no new persisted scalar); `resolve_week_boundary()` releases it. The calendar is OPT-IN, default OFF -- only INTERACTIVE `main.run_game` (build_game/build_from, gated on `max_frames is None`) enables it, so RL/tutorial/headless never pause. The human shell adds `AppScreen.OFFER`: `reconcile_week_boundary()` (per-frame AFTER game-over reconcile, cancelling any gesture) promotes to a modal whose armed Continue resolves the week; window-close mid-offer resolves+autosaves; offer-frame audio consumed silently; saving blocked while pending. HIGH-RISK -> DUAL plan review, both REVISE (harness 1 BLOCKER; Codex 2 BLOCKER + 4 MAJOR with reproduced counterexamples). GATING to the human shell resolved the BLOCKERs structurally: my first plan resolved a headless freeze only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` drives via `advance_exact` and the tutorial is a third direct-Mediator shell -- all would soft-lock at step 1200; gating (week_calendar default OFF) means the branch is never taken off the human path (no env.py/checkpoint/save change, no determinism risk). Codex also refuted my "pause is trajectory-invariant" probe (it bypassed the FixedStepClock cadence) -- gating moots it. The hold-after-full-tick (settlement), terminal precedence, gesture-cancel+arming, and window-close edges were all folded with pinned regressions. The DUAL impl review then confirmed the production code CORRECT on both lanes, with all findings TEST-STRENGTH: Codex mutation-proved six survivors the harness rated shippable (an exact-landing-only hold, a hold-before-settlement, a dropped not-game-over guard, a truthy-not-`is True` OFFER guard, a wrong letterbox-cancel event, and a missing run-loop OFFER promotion/QUIT path), each now pinned (a genuine-crossing speed-4 test, a queued-settlement-parity test, a live-Mock `is True` test, an exact-cancel-event assertion, and real-`run_game` gating + OFFER-loop integration tests). Full `py313` suite green (1507 tests). GM-10b (dedicated-RNG offers) opens next.
 - Continued GM-10 with GM-10b, the dedicated-RNG weekly OFFER GENERATOR (D-042). A new stdlib-only `src/offers.py` (`OfferKind`/`Offer`/pure `generate_offers`) draws `OFFERS_PER_WEEK` (2) DISTINCT upgrade offers from a map-appropriate pool (New Line / +1 Locomotive / +1 Carriage, plus +1 Tunnel only on a finite-tunnel map); `Mediator._maybe_hold_week_boundary` stores `current_offers` at the hold and `resolve_week_boundary` clears them; `draw_offer_screen` previews the labels read-only. The offer RNG is a dedicated per-week `random.Random` derived READ-ONLY from `python_random.getstate()` + `week_index` — a DUAL-PLAN-REVIEW pivot: Codex BLOCKED the first plan (a persisted `spawn(3)` stream deferred to GM-10h would RESET on Continue and diverge, violating README's "Continue resumes exactly"), so offers are instead derived from the already-persisted gameplay RNG state, making them Continue-EXACT with ZERO new save/checkpoint/observation bytes and gameplay-INERT (getstate consumes no draws — station spawns stay byte-identical, every frozen fixture untouched). Gated to the human shell like the calendar, so RL/headless/tutorial never generate (`current_offers` stays `()`). Empirically pre-validated (cadence ~4-6 weeks/game; separate-stream inertness; spawn byte-compat; Continue-exactness of the boundary python-state — all proven before planning). Dual plan review (harness REVISE + Codex BLOCK → the stateless pivot) + dual impl review folded. Applying a choice is GM-10c, per-kind effects GM-10d-g, applied-offer persistence GM-10h (which must not trail GM-10c). Full `py313` suite green (1527 tests).
+- Continued GM-10 with GM-10c, the week-boundary CHOICE CONTROLS (D-043). The GM-10b read-only preview becomes interactive: `menu_screens.offer_menu_layout(width, height, count)` returns one button per offer (`offer_0..offer_{count-1}`), `draw_offer_screen` paints them, and `AppController._handle_offer` arms a button on press and, on a matching release (the GM-10a arming discipline, so a stale gameplay release cannot choose), calls `Mediator.resolve_week_boundary(current_offers[i])`. `resolve_week_boundary(offer=None)` gains the optional chosen offer: it dispatches to a new `_apply_offer` (`match offer.kind`, named `ValueError` on an unknown kind) then clears + releases; `None` is the window-close forced resolve (unchanged). The per-kind arms are NO-OP stubs — choosing changes NO game state, so GM-10c is Continue-safe with ZERO new persisted bytes (locked by a test asserting every kind leaves the full `serialize_game` doc byte-identical). The real effects are GM-10d-g: NEW_LINE can ride the already-persisted `purchased_num_paths` (Continue-safe standalone), while LOCOMOTIVE/CARRIAGE hit `_require_running_config` and TUNNEL needs a persisted bonus, so those land with GM-10h. Full `py313` suite green (1540 tests).
diff --git a/README.md b/README.md
index fb70143..a38a8cd 100644
--- a/README.md
+++ b/README.md
@@ -66,7 +66,7 @@ Set `PYTHON` to a specific interpreter path when `python` is not the intended ex
 * Opening the pause menu autosaves your game to `saves/autosave.json`; Exit to Title rewrites the same save before leaving, and closing the window mid-run keeps it, so Continue on the title screen resumes exactly where you left off. Reaching game over deletes the autosave, so a finished run cannot be Continued.
 * Finishing a run records its lifetime deliveries to a high-score leaderboard at `saves/highscores.json` (ranked and capped per map and rules version); a new best shows a compact indicator on the game-over screen.
 * Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
-* Every week of play the game pauses at a week boundary and shows a modal previewing that week's upgrade offers (a seeded pick of New Line / +1 Locomotive / +1 Carriage / +1 Tunnel — tunnel offers appear only on maps with a tunnel budget); click Continue to resume (the sim carries on with no time backlog). The offers are deterministic and reproduce exactly on Continue; choosing one to apply is a later step. This is an interactive-play feature — headless, RL, and frame-limited runs never pause for a week or generate offers.
+* Every week of play the game pauses at a week boundary and shows a modal with that week's upgrade offers (a seeded pick of New Line / +1 Locomotive / +1 Carriage / +1 Tunnel — tunnel offers appear only on maps with a tunnel budget), one clickable button each; click one to choose it and resume (the sim carries on with no time backlog). The offers are deterministic and reproduce exactly on Continue. Choosing an offer resolves the week (the modal only closes when you pick one); the upgrade each kind grants is being added incrementally. This is an interactive-play feature — headless, RL, and frame-limited runs never pause for a week or generate offers.
 * The top-left HUD shows lifetime passengers delivered, currently spendable line credits, unassigned locomotives, and unassigned carriages as separate values.
 * Each filled grey circle at the bottom is an unused unlocked metro line slot.
 * Hold an assigned colored circle, drag through the replacement station order, and release on the final station to redraw that line; the selected circle is outlined and an invalid repeated-station draft turns red.
diff --git a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
index fa7a8ab..72718b1 100644
--- a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
+++ b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
@@ -263,3 +263,9 @@ Reason: the DUAL plan review (both REVISE) was decisive — the harness caught a
 Decision: GM-10b adds the weekly OFFER GENERATOR — a new stdlib-only `src/offers.py` (`OfferKind`, frozen `Offer`, `describe`, pure `generate_offers(rng, *, count, tunnels_bounded)`) plus mediator/UI wiring. At each held week boundary, `Mediator._maybe_hold_week_boundary` (same calendar/crossing/not-game-over gate as the hold) stores `self.current_offers` = `generate_offers` of `config.OFFERS_PER_WEEK` (2) DISTINCT kinds drawn via `rng.sample` from an explicitly-ordered pool — four kinds on a finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC, `num_tunnels is None`) map; `resolve_week_boundary` clears them (GM-10c will APPLY the chosen one here first); `main` passes `current_offers` into `draw_offer_screen`, which previews the labels read-only on an opaque panel. The offer RNG is a DEDICATED per-week `random.Random` derived READ-ONLY from `context.python_random.getstate()` + `week_index` (sha256 over the repr — cross-process stable, never the salted builtin `hash()`). GM-10b adds NO `SimulationContext`/save-schema/checkpoint/observation change: offers are transient (never serialized) and derived from already-persisted state, so they are Continue-EXACT with ZERO new persisted bytes and every frozen fixture is untouched. Gated to the human shell like the calendar (RL/headless/tutorial never generate). Applying a choice is GM-10c, per-kind effects GM-10d–g, applied-offer/replay persistence GM-10h.

 Reason: a design PIVOT forced by the dual plan review (harness REVISE, Codex BLOCK). Plan v1 used a persisted dedicated `SeedSequence.spawn(3)` `offer_random` stream with persistence DEFERRED to GM-10h — but Codex proved (verified against `README.md:66` "Continue … resumes exactly") that an unpersisted stream RESETS on load, so the next week's offers would DIVERGE from uninterrupted play. The harness lane had rated the same deferral "clean" — the two-lane disagreement is the review-coverage lesson. Codex's own suggested alternative — "generate statelessly from already-persisted inputs" — is the resolution, and it is STRICTLY simpler: no `SimulationContext` change, no schema migration, and it dissolves the gesture-rollback-snapshot concern (no offer-stream state to roll back). Four premises were empirically proven BEFORE the plan (per the observer-predicate lesson): games last ~4–6 weeks (offers are meaningful), a separate offer stream is gameplay-inert, `spawn` is byte-back-compatible (moot after the pivot), and — the load-bearing one — `python_random.getstate()` at a week boundary is byte-identical after a mid-game save→load (so the derived offers reproduce exactly). ORDERING CONSTRAINT (review MINOR): GM-10c (apply a choice) must NOT ship ahead of GM-10h (applied-offer/replay persistence), or a Continue could inconsistently resurrect/replace an applied choice. `OFFERS_PER_WEEK=2` is a provisional balance default (GM-11 may tune it); a value above the CLASSIC pool size would silently clamp there (documented at the `min` clamp). GM-10c (choice controls) opens next.
+
+## D-043
+
+Decision: GM-10c makes the week-boundary offers SELECTABLE. `menu_screens.offer_menu_layout` gains a `count` param and returns one button rect per offer (`offer_0..offer_{count-1}`); `draw_offer_screen` paints each offer as a button. `AppController._handle_offer` arms a button on mouse-down and, on a matching mouse-up (the GM-10a arming discipline — a stale gameplay release cannot choose), resolves with the chosen offer. `Mediator.resolve_week_boundary(offer=None)` gains the optional chosen offer: it calls `_apply_offer(offer)` (a `match offer.kind` over `OfferKind`, raising a named `ValueError` on an unknown kind), then clears `current_offers` and releases the pause; `offer=None` is a forced resolve with no choice (the `main.run_game` window-close path, unchanged and backward-compatible). In GM-10c every per-kind arm is a NO-OP stub, so choosing changes NO game state and adds ZERO new persisted bytes (Continue-safe; state-inertness is test-locked against the full `serialize_game` doc). The per-kind EFFECTS are GM-10d-g; applied-offer/replay persistence is GM-10h.
+
+Reason: keep the roadmap's clean split (controls in GM-10c, effects in GM-10d-g, persistence in GM-10h) rather than fold an effect in early — a no-op dispatch is fully testable via the control flow (arming, routing offer_i→current_offers[i], resume, window-close-no-apply) and the state-inertness lock, and it keeps the D-042 ordering constraint vacuously satisfied (GM-10c persists nothing). REFINEMENT of that constraint discovered here (from the `_require_running_config` pin, Explore): the constraint bites per-EFFECT, not on GM-10c itself — GM-10d's NEW_LINE grant can flow through the already-persisted `purchased_num_paths` and is Continue-safe standalone, but GM-10e/f (LOCOMOTIVE/CARRIAGE via `num_metros`/`num_carriages`, pinned by `save_load._require_running_config` to config values) and GM-10g (TUNNEL, needs a persisted bonus over the immutable `map_definition.tunnel_budget`) MUST land with GM-10h. The chosen offer is passed as an argument (not stored) so there is no throwaway mediator state; the additive `offer=None` default keeps every existing `resolve_week_boundary()` caller (window-close, tests) valid. GM-10d (line upgrade — the first, Continue-safe effect) opens next.
```
