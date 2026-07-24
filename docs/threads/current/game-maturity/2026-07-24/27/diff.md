# GM-10a simulation calendar — implementation diff

Source: config.py (WEEK_LENGTH_STEPS), mediator.py (week_calendar + the boundary hold after the full tick + week API + the 'week' reason), app_controller.py (AppScreen.OFFER + reconcile_week_boundary + _handle_offer), main.py (build_game/build_from gate on max_frames, the reconcile hook, QUIT-during-OFFER, audio, render), menu_screens.py (offer layout/screen), save_game.py (quiescence). New test: test_gm10a_calendar.py (core + gating + run-loop OFFER integration, hardened for the 6 impl-review mutation folds). Docs: D-041, README, GAME_RULES, ARCHITECTURE, PROGRESS.

## Production source
```diff
diff --git a/src/app_controller.py b/src/app_controller.py
index 214cfe9..07f1ecc 100644
--- a/src/app_controller.py
+++ b/src/app_controller.py
@@ -24,7 +24,12 @@ from event.type import KeyboardEventType, MouseEventType
 from geometry.point import Point
 from maps import KNOWN_MAP_IDS
 from settings import DEFAULT_SETTINGS
-from ui.menu_screens import pause_menu_layout, settings_menu_layout, title_layout
+from ui.menu_screens import (
+    offer_menu_layout,
+    pause_menu_layout,
+    settings_menu_layout,
+    title_layout,
+)

 GameTriple = tuple[object, object, object]
 _MENU_REASON = "menu"
@@ -45,6 +50,7 @@ class AppScreen(Enum):
     GAME_OVER = auto()
     SETTINGS = auto()
     TUTORIAL = auto()
+    OFFER = auto()  # GM-10a (D-041): the week-boundary modal over the frozen game


 def _cycle_volume(value: int) -> int:
@@ -175,10 +181,35 @@ class AppController:
             self._autosave_delete()
             self._record_highscore()

+    def reconcile_week_boundary(self) -> None:
+        """Promote a pending week boundary to the ``OFFER`` modal (GM-10a/D-041).
+
+        Idempotent and a no-op unless still ``PLAYING`` and NOT game over with a
+        pending boundary. It runs AFTER ``reconcile_game_over`` (both in
+        ``handle_event`` and per-frame in ``main.run_game``), so a tick that ends
+        the game promotes to ``GAME_OVER``, never to an offer (review MAJOR). Any
+        armed gameplay gesture is cancelled through the pinned letterbox-cancel
+        before switching, exactly as pause-menu entry does, so a mid-draft mouse-up
+        cannot leak into or resume stale through the modal (review MAJOR).
+        """
+        # `is True` (not just truthiness) so a stub/MagicMock mediator that
+        # auto-vivifies the attribute as a truthy Mock does NOT falsely enter the
+        # offer -- exactly as reconcile_game_over guards is_game_over. A real
+        # Mediator returns a real bool, so a genuine pending week is never masked.
+        if (
+            self.state is AppScreen.PLAYING
+            and self.mediator.is_game_over is not True
+            and getattr(self.mediator, "is_week_boundary_pending", False) is True
+        ):
+            self.session.dispatch(MouseEvent(MouseEventType.MOUSE_UP, Point(-1, -1)))
+            self._armed_menu_control = None
+            self.state = AppScreen.OFFER
+
     def handle_event(self, event: object) -> None:
         """Route one converted event according to the current screen."""

         self.reconcile_game_over()
+        self.reconcile_week_boundary()
         if self.state is AppScreen.PLAYING:
             self._handle_playing(event)
         elif self.state is AppScreen.PAUSE_MENU:
@@ -191,6 +222,8 @@ class AppController:
             self._handle_settings(event)
         elif self.state is AppScreen.TUTORIAL:
             self._handle_tutorial(event)
+        elif self.state is AppScreen.OFFER:
+            self._handle_offer(event)

     def _start_new_game(self, map_id: str) -> None:
         # Build a fresh game on `map_id`. The title New Game / Enter pass the picker
@@ -290,6 +323,27 @@ class AppController:
             # cleared above.
             self._open_settings(AppScreen.PAUSE_MENU)

+    def _handle_offer(self, event: object) -> None:
+        # GM-10a (D-041): the week-boundary modal's single Continue control is
+        # ARMED (a down+up on the SAME control) so a stale gameplay mouse-up that
+        # crossed the boundary cannot dismiss it (review MAJOR). Continue resolves
+        # the week and resumes PLAYING. GM-10c replaces Continue with the offer.
+        layout = offer_menu_layout(screen_width, screen_height)
+        pressed = _mouse_down_position(event)
+        if pressed is not None:
+            self._armed_menu_control = next(
+                (key for key in layout if _clicked(layout, key, pressed)), None
+            )
+            return
+        position = _mouse_up_position(event)
+        if position is None:
+            return
+        armed = self._armed_menu_control
+        self._armed_menu_control = None
+        if armed == "continue" and _clicked(layout, "continue", position):
+            self.mediator.resolve_week_boundary()
+            self.state = AppScreen.PLAYING
+
     def _handle_title(self, event: object) -> None:
         if _is_key_up(event, pygame.K_RETURN):
             self._start_new_game(self.current_map_id)
diff --git a/src/config.py b/src/config.py
index 6e12fb8..49d47ed 100644
--- a/src/config.py
+++ b/src/config.py
@@ -85,6 +85,13 @@ carriage_queue_outline_color = metro_queue_outline_color
 carriage_queue_outline_width = metro_queue_outline_width
 carriage_passengers_per_row = 3

+# weekly calendar (GM-10a / D-041): a "week" is a fixed number of sim steps. At
+# 60 steps/s (the 17,17,16 tick cadence) 1200 steps is ~20 s at 1x speed. A
+# provisional balance default -- GM-11 may tune it or make it escalate. Only the
+# human PLAYING shell enables the calendar (Mediator.week_calendar); RL/headless
+# and the tutorial leave it off, so weeks never pause a headless sim.
+WEEK_LENGTH_STEPS = 1200
+
 # path
 path_unlock_milestones = [0, 90, 300, 650]
 num_paths = len(path_unlock_milestones)
diff --git a/src/main.py b/src/main.py
index 39e9978..7bdcc4d 100644
--- a/src/main.py
+++ b/src/main.py
@@ -35,6 +35,7 @@ from settings import load_settings, save_settings
 from ui.menu_screens import (
     draw_best_indicator,
     draw_notice,
+    draw_offer_screen,
     draw_pause_menu,
     draw_settings_menu,
     draw_title_screen,
@@ -113,6 +114,11 @@ def _audio_step(controller, state, previous_audio_session, snapshot, backend):
             controller.current_settings.master_volume,
             controller.current_settings.sfx_volume,
         )
+    elif state is AppScreen.OFFER:
+        # A boundary-tick delivery/unlock is CONSUMED silently while the offer
+        # modal is up (re-baseline, no tone), so nothing bursts after Continue
+        # (GM-10a review MINOR); the modal is not a gameplay-tone screen.
+        snapshot = snapshot_of(controller.mediator)
     return previous_audio_session, snapshot


@@ -219,6 +225,12 @@ def run_game(
         # picker's id for a new game, or the current game's id for a restart; a
         # registered id always resolves (map_by_id raises on an unknown one).
         mediator = Mediator(map_definition=map_by_id(map_id))
+        # GM-10a (D-041): only INTERACTIVE human play opts into the weekly calendar,
+        # so a week boundary pauses for the offer. A frame-limited/headless run
+        # (max_frames set -- the same signal that picks NullAudio and a PLAYING
+        # start) leaves it off, since no one is there to resolve the offer; RL and
+        # the tutorial leave it off too.
+        mediator.week_calendar = max_frames is None
         renderer = GameRenderer()
         session = GameSession(mediator, step_observer=renderer)
         session.prepare_layout(game_surface)
@@ -226,7 +238,9 @@ def run_game(

     def build_from(mediator):
         # Wrap a loaded Mediator into the live triple exactly as build_game does
-        # (prepare_layout included), returning the SAME loaded mediator.
+        # (prepare_layout included), returning the SAME loaded mediator. A Continued
+        # interactive game keeps its calendar (GM-10a).
+        mediator.week_calendar = max_frames is None
         renderer = GameRenderer()
         session = GameSession(mediator, step_observer=renderer)
         session.prepare_layout(game_surface)
@@ -314,7 +328,13 @@ def run_game(
                 # State-gated window-close autosave (D-027/F1): persist a mid-run
                 # boundary, drop a finished run's save, and touch nothing on the
                 # title screen (nor for a non-game controller).
-                if controller.state in (AppScreen.PLAYING, AppScreen.PAUSE_MENU):
+                if controller.state is AppScreen.OFFER:
+                    # Closing mid-offer (GM-10a): resolve the week (there is no
+                    # choice yet) and autosave the resumed game, so Continue reloads
+                    # past the boundary. Mid-offer persistence proper is GM-10h.
+                    controller.mediator.resolve_week_boundary()
+                    write_autosave(controller.mediator)
+                elif controller.state in (AppScreen.PLAYING, AppScreen.PAUSE_MENU):
                     if controller.mediator.is_game_over:
                         delete_autosave()
                         # Record the finished run at the window-close race,
@@ -360,6 +380,10 @@ def run_game(
         # Idempotent and mutually exclusive with the window-close QUIT gate above,
         # which fires only while the state is still PLAYING/PAUSE_MENU.
         controller.reconcile_game_over()
+        # Week-boundary reconcile (GM-10a/D-041): AFTER game-over so a terminal tick
+        # promotes to GAME_OVER, never to an offer; promotes a pending boundary to
+        # the OFFER modal, cancelling any armed gesture first.
+        controller.reconcile_week_boundary()
         state = controller.state

         # Gameplay SFX (GM-08b): after reconcile so the promotion-frame game-over
@@ -404,6 +428,9 @@ def run_game(
                 overlay = controller.tutorial_overlay()
                 if overlay is not None:
                     draw_tutorial_overlay(game_surface, *overlay)
+            elif state == AppScreen.OFFER:
+                # The week-boundary modal over the frozen game frame (GM-10a).
+                draw_offer_screen(game_surface, controller.mediator.week_index)
         window_surface.fill(screen_color)
         target_size = (viewport.width, viewport.height)
         if viewport.width > 0 and viewport.height > 0:
diff --git a/src/mediator.py b/src/mediator.py
index e27034d..4d9ace8 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -6,6 +6,7 @@ import pygame

 from carriage_management import CarriageManagement
 from config import (
+    WEEK_LENGTH_STEPS,
     game_over_button_height,
     game_over_button_spacing,
     game_over_button_width,
@@ -73,7 +74,11 @@ from utils import get_shape_from_type, hue_to_rgb, pick_distinct_hue

 TravelPlans = Dict[Passenger, TravelPlan]

-_PAUSE_REASONS = frozenset({"user", "menu"})
+# "week" (GM-10a / D-041) is the calendar's boundary pause -- held only by the
+# human PLAYING shell (see Mediator.week_calendar) and, unlike "user"/"menu",
+# never cleared by the Space toggle or speed buttons.
+_PAUSE_REASONS = frozenset({"user", "menu", "week"})
+_WEEK_REASON = "week"


 def _get_game_renderer_factory():
@@ -156,6 +161,11 @@ class Mediator:
         self.path_edit_selection: PathEditSelection | None = None
         self.travel_plans: TravelPlans = {}
         self.is_paused = False
+        # GM-10a (D-041): the weekly calendar is OPT-IN and OFF by default, so
+        # RL/headless envs, the tutorial, and tests never pause for a week boundary
+        # (they would soft-lock a driver that cannot resolve the offer). Only the
+        # human PLAYING shell (main.run_game's build_game/build_from) sets this True.
+        self.week_calendar = False
         self.game_speed_multiplier = 1
         self.unlocked_num_paths = self.get_unlocked_num_paths()
         self.unlocked_num_stations = self.get_unlocked_num_stations()
@@ -677,6 +687,22 @@ class Mediator:
             self._pause_reasons = store
         return store

+    @property
+    def week_index(self) -> int:
+        # GM-10a: which week the run is in, DERIVED from the already-persisted
+        # steps, so week identity survives save/load with no new stored scalar.
+        return self.steps // WEEK_LENGTH_STEPS
+
+    @property
+    def is_week_boundary_pending(self) -> bool:
+        # True while the calendar is paused at a week boundary awaiting a resolve.
+        return _WEEK_REASON in self._pause_reason_store(_WEEK_REASON)
+
+    def resolve_week_boundary(self) -> None:
+        # Continue past a week boundary. In GM-10a this just releases the pause;
+        # GM-10b applies the chosen offer here before releasing.
+        self.release_pause_reason(_WEEK_REASON)
+
     def set_paused(self, paused: bool) -> None:
         self._input.set_paused(self, paused)

@@ -720,6 +746,7 @@ class Mediator:
         )

     def increment_time(self, dt_ms: int) -> None:
+        old_steps = self.steps
         transition_active = not self.is_paused and not self.is_game_over
         # The narrow reconcile runs unconditionally — including paused and
         # terminal states — so a repairable shape never survives a tick.
@@ -733,6 +760,21 @@ class Mediator:
         )
         if transition_active:
             self._drain_and_settle_queued_returns()
+        self._maybe_hold_week_boundary(old_steps)
+
+    def _maybe_hold_week_boundary(self, old_steps: int) -> None:
+        # GM-10a (D-041): after the COMPLETE tick (post queued-return settlement),
+        # hold the "week" pause if the calendar is enabled and this tick crossed a
+        # NEW week boundary. Placed LAST so the settlement is never interrupted
+        # mid-tick (review MAJOR), and skipped on game over so a terminal tick
+        # promotes to GAME_OVER rather than an offer (review MAJOR). WEEK_LENGTH_STEPS
+        # >> the max speed (4), so at most one boundary crosses per tick; a frozen
+        # tick advances no steps, so a held week never re-triggers. (At speed 4 the
+        # hold lands at e.g. steps=1202, not 1200 -- week_index is identical.)
+        if not self.week_calendar or self.is_game_over:
+            return
+        if old_steps // WEEK_LENGTH_STEPS < self.steps // WEEK_LENGTH_STEPS:
+            self.hold_pause_reason(_WEEK_REASON)

     def _drain_and_settle_queued_returns(self) -> None:
         """Force-alight stranded riders, then settle emptied queued returns.
diff --git a/src/save_game.py b/src/save_game.py
index 4977034..7560570 100644
--- a/src/save_game.py
+++ b/src/save_game.py
@@ -73,6 +73,15 @@ def _require_quiescent(mediator: Any) -> None:
         raise ValueError("cannot save during a path redraw gesture")
     if mediator.path_edit_selection is not None:
         raise ValueError("cannot save during a path edit selection")
+    # GM-10a (D-041): a pending week-boundary offer is a transient, unresolved
+    # choice that GM-10a does not persist (deferred to GM-10h). validate_save
+    # already rejects a "week" pause reason before any file I/O; this gives the
+    # clearer, actionable error at the save boundary. Defensive getattr keeps
+    # non-Mediator save shapes (which never hold "week") working.
+    if getattr(mediator, "is_week_boundary_pending", False):
+        raise ValueError(
+            "cannot save while a week-boundary offer is pending; resolve it first"
+        )


 def _require_canonical_fleet(mediator: Any) -> None:
diff --git a/src/ui/menu_screens.py b/src/ui/menu_screens.py
index 9203a93..64a2b4e 100644
--- a/src/ui/menu_screens.py
+++ b/src/ui/menu_screens.py
@@ -190,6 +190,28 @@ def draw_notice(surface: pygame.Surface, message: str) -> None:
     surface.blit(text, text.get_rect(center=banner.center))


+def offer_menu_layout(width: int, height: int) -> dict[str, pygame.Rect]:
+    """Hit-test rects for the GM-10a week-boundary modal (a single Continue)."""
+
+    # One centred button in the lower half, mirroring the pause/settings stacks
+    # so the shared arming + _clicked helpers apply unchanged.
+    return _stacked_buttons(width, ("continue",), height // 2)
+
+
+def draw_offer_screen(surface: pygame.Surface, week_index: int) -> None:
+    """Paint the deterministic week-boundary modal: a banner + Continue (GM-10a)."""
+
+    width, height = surface.get_size()
+    layout = offer_menu_layout(width, height)
+    _draw_heading(
+        surface,
+        width,
+        layout["continue"].top - _HEADING_GAP,
+        f"Week {week_index} complete",
+    )
+    _draw_button(surface, layout["continue"], "Continue")
+
+
 def draw_tutorial_overlay(
     surface: pygame.Surface, prompt: str, ordinal: int, total: int, done: bool
 ) -> None:
```

## Tests (new file)
```diff
diff --git a/test/test_gm10a_calendar.py b/test/test_gm10a_calendar.py
new file mode 100644
index 0000000..388b507
--- a/test/test_gm10a_calendar.py
+++ b/test/test_gm10a_calendar.py
@@ -0,0 +1,555 @@
+"""GM-10a contract: the simulation calendar + week pause reason (D-041).
+
+A "week" is WEEK_LENGTH_STEPS sim steps. Only the interactive human shell enables
+the calendar (Mediator.week_calendar), so RL/headless/tutorial never pause. At a
+boundary the mediator holds the "week" pause AFTER the complete tick (so
+settlement is never interrupted) and only when not game over; the human shell
+promotes it to an OFFER modal (after game-over reconcile, cancelling any gesture)
+whose armed Continue resolves it. Nothing about the calendar is persisted in
+GM-10a; week_index is derived from steps.
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import unittest
+from types import SimpleNamespace
+from unittest.mock import MagicMock, patch
+
+sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")
+
+import pygame
+
+import main
+from app_controller import AppController, AppScreen
+from config import WEEK_LENGTH_STEPS, screen_height, screen_width
+from env import MiniMetroEnv
+from event.mouse import MouseEvent
+from event.type import MouseEventType
+from geometry.point import Point
+from mediator import Mediator
+from rl.player_env import PlayerPixelEnv
+from save_game import serialize_game
+from ui.menu_screens import offer_menu_layout
+
+pygame.init()
+
+
+def _step_to_boundary(mediator, extra=0):
+    ticks = 0
+    while mediator.steps < WEEK_LENGTH_STEPS + extra and ticks < WEEK_LENGTH_STEPS * 2:
+        mediator.increment_time(17)
+        ticks += 1
+    return mediator
+
+
+class TestGM10aCalendarCore(unittest.TestCase):
+    def test_calendar_off_by_default_never_pauses(self):
+        m = Mediator(seed=0)
+        self.assertFalse(m.week_calendar, "the calendar is OFF by default")
+        _step_to_boundary(m, extra=100)
+        self.assertGreater(m.steps, WEEK_LENGTH_STEPS, "no freeze without the calendar")
+        self.assertFalse(m.is_week_boundary_pending)
+        self.assertFalse(m.is_paused)
+
+    def test_calendar_on_holds_week_at_the_first_boundary(self):
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        _step_to_boundary(m)
+        self.assertTrue(m.is_week_boundary_pending, "the boundary holds the week pause")
+        self.assertTrue(m.is_paused)
+        self.assertEqual(m.week_index, 1)
+        self.assertGreaterEqual(m.steps, WEEK_LENGTH_STEPS)
+
+    def test_freeze_then_resolve_resumes_without_immediate_retrigger(self):
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        _step_to_boundary(m)
+        frozen = m.steps
+        for _ in range(30):
+            m.increment_time(17)
+        self.assertEqual(m.steps, frozen, "a pending week freezes the sim")
+        m.resolve_week_boundary()
+        self.assertFalse(m.is_week_boundary_pending)
+        m.increment_time(17)
+        self.assertEqual(m.steps, frozen + 1, "resolve resumes advancing")
+        # The next boundary is one full week later, not immediately.
+        for _ in range(50):
+            m.increment_time(17)
+        self.assertFalse(m.is_week_boundary_pending, "no immediate re-trigger")
+
+    def test_week_index_is_derived_from_steps(self):
+        m = Mediator(seed=0)
+        for boundary in (
+            0,
+            WEEK_LENGTH_STEPS - 1,
+            WEEK_LENGTH_STEPS,
+            WEEK_LENGTH_STEPS * 3,
+        ):
+            m.steps = boundary
+            self.assertEqual(m.week_index, boundary // WEEK_LENGTH_STEPS)
+
+    def test_speed_4_crossing_holds_without_landing_exactly(self):
+        # review MAJOR: at speed 4 steps jump +4, so a boundary is CROSSED, not
+        # landed on. Pin that the hold fires on the crossing (old//W < steps//W),
+        # NOT on steps == W -- an exact-landing-only mutant would skip this.
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        while m.steps < WEEK_LENGTH_STEPS - 2:  # speed 1 up to steps == W-2
+            m.increment_time(17)
+        self.assertEqual(m.steps, WEEK_LENGTH_STEPS - 2)
+        m.game_speed_multiplier = 4
+        m.increment_time(17)  # W-2 -> W+2, jumping ACROSS the boundary
+        self.assertEqual(m.steps, WEEK_LENGTH_STEPS + 2, "jumped past, never on, W")
+        self.assertTrue(m.is_week_boundary_pending, "the +4 crossing still holds")
+        self.assertEqual(m.week_index, 1)
+
+    def test_space_and_speed_cannot_dismiss_the_week_pause(self):
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        _step_to_boundary(m)
+        m.is_paused = False  # the SPACE / user-pause toggle path
+        self.assertTrue(m.is_week_boundary_pending, "Space cannot clear the week pause")
+        m.set_game_speed(4)  # a speed button
+        self.assertTrue(m.is_week_boundary_pending, "speed cannot clear the week pause")
+
+    def test_no_hold_when_the_boundary_tick_also_game_overs(self):
+        # review MAJOR: a tick that CROSSES a boundary AND flips is_game_over must
+        # NOT hold "week" -- game over wins. Drive the hold with a genuine crossing
+        # (old_steps W-1 -> steps W) and a post-tick game-over state; deleting the
+        # `or is_game_over` guard would hold here (the mutation the pre-set,
+        # never-crossing version missed).
+        crossed = Mediator(seed=0)
+        crossed.week_calendar = True
+        crossed.steps = WEEK_LENGTH_STEPS  # the tick advanced ACROSS the boundary...
+        crossed.is_game_over = True  # ...and flipped game over on the same tick
+        crossed._maybe_hold_week_boundary(WEEK_LENGTH_STEPS - 1)
+        self.assertFalse(
+            crossed.is_week_boundary_pending,
+            "game over on the crossing tick blocks the hold",
+        )
+        # NOT vacuous: the identical crossing DOES hold when the run is alive.
+        alive = Mediator(seed=0)
+        alive.week_calendar = True
+        alive.steps = WEEK_LENGTH_STEPS
+        alive._maybe_hold_week_boundary(WEEK_LENGTH_STEPS - 1)
+        self.assertTrue(
+            alive.is_week_boundary_pending, "the same crossing holds if alive"
+        )
+
+    def test_the_boundary_hold_does_not_interrupt_queued_settlement(self):
+        # review MAJOR/MINOR: the hold must come AFTER _drain_and_settle_queued_returns,
+        # so a locomotive unassignment queued to settle ON the boundary-crossing tick
+        # completes identically to a calendar-OFF control. `settle()` early-returns
+        # while paused, so a hold placed BEFORE the settle would STRAND the metro
+        # (len(metros)/available_locomotives would diverge) -- this pins that.
+        def board(calendar):
+            m = Mediator(seed=0)
+            m.week_calendar = calendar
+            path = m.create_path_from_station_indices([0, 1, 2])
+            m.assign_locomotive(path)
+            for _ in range(WEEK_LENGTH_STEPS - 1):
+                m.increment_time(17)
+            # Queue the unassignment so it settles on the boundary-crossing tick.
+            m.queue_locomotive_unassignment(m.paths[0])
+            m.increment_time(17)
+            return m
+
+        on = board(True)
+        off = board(False)
+        self.assertTrue(on.is_week_boundary_pending, "the boundary held the week")
+        self.assertFalse(off.is_week_boundary_pending)
+        self.assertEqual(on.steps, off.steps)
+        # The queued metro settled in BOTH -- the hold did not strand it.
+        self.assertEqual(len(on.metros), len(off.metros), "settle ran before the hold")
+        self.assertEqual(on.available_locomotives, off.available_locomotives)
+        self.assertEqual(on.deliveries, off.deliveries)
+
+
+class _FakeSession:
+    def __init__(self):
+        self.dispatched = []
+
+    def dispatch(self, event):
+        self.dispatched.append(event)
+
+
+class _FakeMediator:
+    def __init__(self, *, week_pending=False, game_over=False):
+        self._week_pending = week_pending
+        self.is_game_over = game_over
+        self.resolved = 0
+        self.week_index = 1
+        self.held = []
+
+    @property
+    def is_week_boundary_pending(self):
+        return self._week_pending
+
+    def resolve_week_boundary(self):
+        self._week_pending = False
+        self.resolved += 1
+
+    def hold_pause_reason(self, reason):
+        self.held.append(reason)
+
+    def release_pause_reason(self, reason):
+        pass
+
+
+def _offer_controller(*, week_pending=True, game_over=False):
+    session = _FakeSession()
+    mediator = _FakeMediator(week_pending=week_pending, game_over=game_over)
+
+    def build_game(map_id="classic"):
+        return mediator, SimpleNamespace(), session
+
+    controller = AppController(build_game, start_state=AppScreen.PLAYING)
+    # AppController built its own initial mediator/session; install the fakes so we
+    # drive the reconcile against a shape with the week API.
+    controller.mediator = mediator
+    controller.session = session
+    return controller, mediator, session
+
+
+class TestGM10aOfferPromotion(unittest.TestCase):
+    def test_reconcile_promotes_a_pending_boundary_to_offer(self):
+        controller, mediator, session = _offer_controller()
+        controller.reconcile_week_boundary()
+        self.assertEqual(controller.state, AppScreen.OFFER)
+        # It cancelled the in-progress gameplay gesture via the letterbox cancel.
+        # review MAJOR: pin the EXACT event, not just the count -- a mutant that
+        # dispatches None or a MOUSE_DOWN (or drops the off-viewport position)
+        # would still leave len == 1.
+        self.assertEqual(len(session.dispatched), 1, "one off-viewport cancel")
+        (cancel,) = session.dispatched
+        self.assertIsInstance(cancel, MouseEvent)
+        self.assertEqual(cancel.event_type, MouseEventType.MOUSE_UP)
+        self.assertEqual((cancel.position.left, cancel.position.top), (-1, -1))
+
+    def test_a_truthy_but_not_true_pending_flag_stays_out_of_offer(self):
+        # review MAJOR: the guard is `is True`, not truthy, so a MagicMock whose
+        # is_week_boundary_pending auto-vivifies to a truthy Mock must NOT promote.
+        # SimpleNamespace (getattr -> False) can't distinguish `is True` from
+        # truthy; a live Mock can. This pins the exact `is True` semantics.
+        controller, _mediator, session = _offer_controller()
+        stub = MagicMock()
+        stub.is_game_over = False
+        # is_week_boundary_pending is a truthy auto-Mock, never the literal True.
+        controller.mediator = stub
+        controller.reconcile_week_boundary()
+        self.assertEqual(controller.state, AppScreen.PLAYING)
+        self.assertEqual(session.dispatched, [], "no cancel dispatched")
+
+    def test_game_over_wins_over_a_pending_week(self):
+        # review MAJOR: with both pending, reconcile_game_over (run first) promotes
+        # to GAME_OVER and reconcile_week_boundary no-ops on a terminal mediator.
+        controller, mediator, session = _offer_controller(
+            week_pending=True, game_over=True
+        )
+        controller.reconcile_game_over()
+        controller.reconcile_week_boundary()
+        self.assertEqual(controller.state, AppScreen.GAME_OVER)
+
+    def test_reconcile_is_a_noop_without_a_pending_boundary(self):
+        controller, mediator, session = _offer_controller(week_pending=False)
+        controller.reconcile_week_boundary()
+        self.assertEqual(controller.state, AppScreen.PLAYING)
+
+    def test_a_stub_mediator_never_enters_the_offer(self):
+        # A seam-less controller's minimal mediator has no week API; the `is True`
+        # guard keeps it out of the offer even against a truthy attribute.
+        build_game = lambda map_id="classic": (  # noqa: E731
+            SimpleNamespace(is_game_over=False),
+            SimpleNamespace(),
+            _FakeSession(),
+        )
+        controller = AppController(build_game, start_state=AppScreen.PLAYING)
+        controller.reconcile_week_boundary()  # must not raise, must not enter OFFER
+        self.assertEqual(controller.state, AppScreen.PLAYING)
+
+
+class TestGM10aOfferArming(unittest.TestCase):
+    def _up(self, controller, rect):
+        controller.handle_event(
+            MouseEvent(MouseEventType.MOUSE_UP, Point(rect.centerx, rect.centery))
+        )
+
+    def _down(self, controller, rect):
+        controller.handle_event(
+            MouseEvent(MouseEventType.MOUSE_DOWN, Point(rect.centerx, rect.centery))
+        )
+
+    def test_continue_requires_an_offer_local_down_up_pair(self):
+        # review MAJOR: a bare gameplay mouse-up that crossed the boundary must NOT
+        # dismiss the offer -- only an in-offer down->up on Continue resolves it.
+        controller, mediator, session = _offer_controller()
+        controller.reconcile_week_boundary()
+        self.assertEqual(controller.state, AppScreen.OFFER)
+        rect = offer_menu_layout(screen_width, screen_height)["continue"]
+        # A bare release (no matching in-offer press) is a no-op.
+        self._up(controller, rect)
+        self.assertEqual(controller.state, AppScreen.OFFER, "a bare release is ignored")
+        self.assertEqual(mediator.resolved, 0)
+        # An armed press+release resolves the week and resumes PLAYING.
+        self._down(controller, rect)
+        self._up(controller, rect)
+        self.assertEqual(controller.state, AppScreen.PLAYING)
+        self.assertEqual(mediator.resolved, 1)
+
+
+class TestGM10aSaveBlock(unittest.TestCase):
+    def test_saving_is_blocked_while_a_week_boundary_is_pending(self):
+        m = Mediator(seed=0)
+        m.week_calendar = True
+        _step_to_boundary(m)
+        self.assertTrue(m.is_week_boundary_pending)
+        with self.assertRaisesRegex(ValueError, "week-boundary offer is pending"):
+            serialize_game(m)
+        # Resolving lets the save proceed.
+        m.resolve_week_boundary()
+        self.assertIsInstance(serialize_game(m), dict)
+
+
+class TestGM10aRLUnaffected(unittest.TestCase):
+    def test_a_headless_env_never_pauses_for_a_week(self):
+        # The env's Mediator leaves the calendar OFF, so stepping past a boundary
+        # never freezes and never holds "week" -- the RL/checkpoint path is
+        # structurally free of the calendar.
+        env = MiniMetroEnv()
+        env.reset(seed=0)
+        self.assertFalse(env.mediator.week_calendar)
+        for _ in range(WEEK_LENGTH_STEPS + 60):
+            env.mediator.step_time(17)
+        self.assertGreater(env.mediator.steps, WEEK_LENGTH_STEPS, "no headless freeze")
+        self.assertFalse(env.mediator.is_week_boundary_pending)
+        self.assertFalse(env.mediator.is_paused)
+
+    def test_the_pixel_rl_env_is_calendar_free_past_a_boundary(self):
+        # The player-pixel env (the first-class RL boundary, GM-09a2) builds a bare
+        # Mediator too, so the calendar is OFF and stepping past a week never freezes
+        # the pixel task. step_time -> increment_time -> the hold, so this is NOT
+        # vacuous: a mutant defaulting week_calendar True would freeze here.
+        env = PlayerPixelEnv()
+        env.reset(seed=0)
+        mediator = env._mediator
+        self.assertFalse(
+            mediator.week_calendar, "the pixel env leaves the calendar off"
+        )
+        for _ in range(WEEK_LENGTH_STEPS + 60):
+            mediator.step_time(17)
+        self.assertGreater(mediator.steps, WEEK_LENGTH_STEPS, "no pixel-env freeze")
+        self.assertFalse(mediator.is_week_boundary_pending)
+        self.assertFalse(mediator.is_paused)
+
+
+# --- run_game integration harness (GM-10a review MAJOR: #gating + #offer-loop) ---
+# Drives the REAL main.run_game and the REAL AppController behind recording fakes
+# for the Mediator/GameSession/GameRenderer factory seam (test_gm07a idiom), so the
+# gating (week_calendar = max_frames is None) and the offer promotion/render/QUIT
+# path are pinned against the live loop, not a hand-rolled controller.
+_ELAPSED_MS = 17
+
+
+def _quit_event():
+    return SimpleNamespace(type=pygame.QUIT)
+
+
+class _LoopRenderer:
+    def __init__(self):
+        self.draws = []
+
+    def draw(self, surface, mediator, alpha, reduced_motion=False):
+        self.draws.append(getattr(mediator, "week_index", None))
+
+
+class _LoopSession:
+    def __init__(self, mediator, **kwargs):
+        self.mediator = mediator
+        self.dispatched = []
+        self.step_observer = kwargs.get("step_observer")
+
+    def prepare_layout(self, surface):
+        pass
+
+    def dispatch(self, event):
+        self.dispatched.append(event)
+
+    def advance(self, elapsed_ms):
+        return SimpleNamespace(alpha=1.0)
+
+
+class _LoopMediator:
+    def __init__(self, *, pending=False, week_index=1):
+        self.is_game_over = False
+        self._pending = pending
+        self.week_index = week_index
+        self.week_calendar = None  # build_game/build_from set this on construction
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
+        self.resolved = 0
+
+    @property
+    def is_week_boundary_pending(self):
+        return self._pending
+
+    def resolve_week_boundary(self):
+        self._pending = False
+        self.resolved += 1
+
+    def hold_pause_reason(self, reason):
+        pass
+
+    def release_pause_reason(self, reason):
+        pass
+
+
+def _drive_run_game(frames_events, *, max_frames, start_state=None, pending=False):
+    """Run ``main.run_game`` over the pumped frames; return the captured harness."""
+
+    captured = {}
+    offer_draws = []
+    autosaves = []
+    real_app_controller = main.AppController
+
+    def build_mediator(map_definition=None):
+        mediator = _LoopMediator(pending=pending)
+        captured["mediator"] = mediator
+        return mediator
+
+    def make_controller(*a, **k):
+        controller = real_app_controller(*a, **k)
+        captured["controller"] = controller
+        return controller
+
+    batches = iter(frames_events)
+    exited = {"raised": False}
+
+    with (
+        patch("main.pygame") as pygame_mock,
+        patch("main.Mediator", side_effect=build_mediator),
+        patch(
+            "main.GameSession",
+            side_effect=lambda mediator, **k: _LoopSession(mediator, **k),
+        ),
+        patch("main.GameRenderer", side_effect=_LoopRenderer),
+        patch("main.AppController", side_effect=make_controller),
+        patch(
+            "main.draw_offer_screen",
+            side_effect=lambda surface, week_index: offer_draws.append(week_index),
+        ),
+        patch("main.draw_title_screen", side_effect=lambda *a, **k: None),
+        patch("main.write_autosave", side_effect=lambda m: autosaves.append(m)),
+    ):
+        pygame_mock.QUIT = pygame.QUIT
+        pygame_mock.MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN
+        pygame_mock.MOUSEBUTTONUP = pygame.MOUSEBUTTONUP
+        pygame_mock.MOUSEMOTION = pygame.MOUSEMOTION
+        window = MagicMock()
+        window.get_size.return_value = (screen_width, screen_height)
+        pygame_mock.display.set_mode.return_value = window
+        game_surface = MagicMock()
+        game_surface.get_size.return_value = (screen_width, screen_height)
+        pygame_mock.Surface.return_value = game_surface
+        clock = MagicMock()
+        clock.tick.return_value = _ELAPSED_MS
+        pygame_mock.time.Clock.return_value = clock
+        pygame_mock.event.get.side_effect = lambda: next(batches)
+        try:
+            main.run_game(max_frames=max_frames, start_state=start_state)
+        except SystemExit:
+            exited["raised"] = True
+    return SimpleNamespace(
+        mediator=captured.get("mediator"),
+        controller=captured.get("controller"),
+        offer_draws=offer_draws,
+        autosaves=autosaves,
+        exited=exited["raised"],
+    )
+
+
+class TestGM10aGating(unittest.TestCase):
+    def test_a_frame_limited_run_leaves_the_calendar_off(self):
+        # review MAJOR: the gate is `week_calendar = max_frames is None`. A bounded
+        # (frame-limited/headless) run must build the game with the calendar OFF, so
+        # a screenshot/CI run never soft-locks at a boundary with no one to resolve.
+        harness = _drive_run_game(
+            [[]], max_frames=1, start_state=AppScreen.PLAYING, pending=False
+        )
+        self.assertIs(
+            harness.mediator.week_calendar, False, "bounded run: calendar gated OFF"
+        )
+
+    def test_an_unbounded_interactive_run_enables_the_calendar(self):
+        # The same gate: an unbounded (interactive human) run builds with the
+        # calendar ON. Driven to exit immediately via a title-screen QUIT so the
+        # construction-time build_game is all we assert.
+        harness = _drive_run_game(
+            [[_quit_event()]], max_frames=None, start_state=None, pending=False
+        )
+        self.assertTrue(harness.exited, "QUIT terminated the unbounded run")
+        self.assertIs(
+            harness.mediator.week_calendar, True, "unbounded run: calendar gated ON"
+        )
+
+    def test_the_tutorial_mediator_leaves_the_calendar_off(self):
+        # build_tutorial never sets week_calendar, so the coached tutorial inherits
+        # the Mediator default (OFF) -- a tutorial week boundary never freezes.
+        self.assertFalse(
+            main._tutorial_mediator().week_calendar, "tutorial: calendar off"
+        )
+
+
+class TestGM10aRunLoopOffer(unittest.TestCase):
+    def test_a_pending_boundary_promotes_and_renders_the_offer(self):
+        # review MAJOR: the live loop must promote a pending boundary to OFFER and
+        # render the modal (draw_offer_screen with the week index) OVER the frozen
+        # game frame (the renderer still draws), cancelling the in-progress gesture.
+        harness = _drive_run_game(
+            [[]], max_frames=1, start_state=AppScreen.PLAYING, pending=True
+        )
+        self.assertEqual(harness.controller.state, AppScreen.OFFER)
+        self.assertEqual(harness.offer_draws, [1], "the modal drew the week index")
+        self.assertTrue(
+            harness.controller.renderer.draws, "the frozen frame drew under the modal"
+        )
+        cancels = [
+            e
+            for e in harness.controller.session.dispatched
+            if isinstance(e, MouseEvent)
+        ]
+        self.assertEqual(len(cancels), 1, "one letterbox cancel dispatched")
+        self.assertEqual(cancels[0].event_type, MouseEventType.MOUSE_UP)
+        self.assertEqual((cancels[0].position.left, cancels[0].position.top), (-1, -1))
+
+    def test_closing_mid_offer_resolves_the_week_and_autosaves(self):
+        # review MAJOR: a window-close WHILE the offer is up (frame 0 promotes, frame
+        # 1 delivers QUIT with state already OFFER) resolves the week and autosaves
+        # the resumed game, so Continue reloads PAST the boundary (GM-10a).
+        harness = _drive_run_game(
+            [[], [_quit_event()]],
+            max_frames=None,
+            start_state=AppScreen.PLAYING,
+            pending=True,
+        )
+        self.assertTrue(harness.exited, "QUIT raised SystemExit")
+        self.assertEqual(harness.mediator.resolved, 1, "closing resolved the week")
+        self.assertEqual(
+            harness.autosaves, [harness.mediator], "the resumed game was autosaved"
+        )
+
+    def test_no_offer_no_autosave_on_a_plain_title_quit(self):
+        # Control: without a pending boundary a TITLE QUIT neither resolves a week
+        # nor autosaves -- isolates the OFFER-QUIT branch from the title close.
+        harness = _drive_run_game(
+            [[_quit_event()]], max_frames=None, start_state=None, pending=False
+        )
+        self.assertTrue(harness.exited)
+        self.assertEqual(harness.mediator.resolved, 0)
+        self.assertEqual(harness.autosaves, [], "a title-screen close writes no save")
+
+
+if __name__ == "__main__":
+    unittest.main()
```

## Docs
```diff
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index ab38769..8278f01 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -378,6 +378,7 @@ python_mini_metro/
 - GM-09f (D-038) begins the map/save integration (SPLIT into save-schema / high-score / menu) with the SAVE-SCHEMA v2 map field. `save_schema` gains `SAVE_SCHEMA_VERSION_V2 = 2` (`SUPPORTED = {1, 2}`, current = 2) with two additive top-level keys `mapId`/`mapDefinitionVersion`; `validate_save` is TWO-PHASE (read + support-check `schemaVersion` with a named error BEFORE choosing the version-aware exact-key set `_TOP_LEVEL_KEYS_V1`/`_V2`, so a v1-doc-with-map-keys and a v2-doc-without both fail closed), and the v2 identity is scalar-validated (`_validate_map_identity`). `save_game.serialize_game` replaces `_require_classic_map` with a fail-closed pair: STRUCTURAL `map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`, since a v2 save records only the identity and rebuilds terrain from the registry on load) and `save_load._require_legal_map_state` (every station on the map's `spawn_regions`; `consumed_tunnels <= num_tunnels`) — the latter shared by serialize and post-load so a forged illegal state (a Classic state relabeled `river@1`) is refused both ways. `save_load.deserialize_game` reads the map identity for v2 / synthesizes `classic@1` for v1, resolves via `resolve_map` (fail-closed on unknown id / unsupported version), and threads `map_definition` into the `Mediator`; tunnel counts stay derived. The byte-frozen `scripts/fixtures/save-v1.json` is unchanged and still loads as Classic; the deterministic v1→v2 header-only upgrade is pinned by a new frozen `scripts/fixtures/save-v2-classic.json` (15485 bytes) that the idempotence + cross-process determinism tests target. `stateContract`/`rulesVersion` unchanged; the RL manifest and recursive checkpoint are separate schemas. The high-score `mapDefinitionVersion` and the in-game map menu follow as the next two sub-units (menu last, so it cannot feed an alternate map to the still-classic-hardcoded score recorder).
 - GM-09f2 (D-039) is the second GM-09f sub-unit: the high-score leaderboard records the MAP identity. Both game-over surfaces now hand the recorder the LIVE mediator (the controller seam passes `self.mediator`, and `main.run_game`'s promotion closure drops its old `SimpleNamespace(deliveries=...)` wrapper), so `main.record_highscore` reads `mediator.map_definition.{map_id, map_definition_version}` (direct, fail-SAFE: a missing map records nothing rather than mislabelling — no `or classic`) instead of hardcoding `classic`. `highscores` bumps to schema **v2** keyed by the full `(map, mapDefinitionVersion, rulesVersion)` identity via one shared `_identity` helper (sort + cap + rank), with the `map` grammar tightened to the save's mapId. A legacy v1 board is NOT migrated — it starts empty — because its classic labels are not provably accurate. This lands BEFORE the in-game menu (GM-09f3) so the recorder is already map-aware when non-Classic maps become selectable; `highscores` stays gameplay-free (no `maps` import) and in the persistence isolation set.
 - GM-09f3 (D-040) COMPLETES GM-09f with the in-game MAP MENU. `AppController` gains `current_map_id` (default `classic`), cycled by an appended title control `map` (`title_layout` appends the `"map"` key so the prior title rects stay byte-identical; `draw_title_screen` gains a `current_map_id` param and paints a `Map: {Name}` button; `main.run_game` threads `controller.current_map_id` into it). The `build_game` seam becomes uniformly `Callable[[str], GameTriple]`: `main.run_game`'s `build_game(map_id)` resolves `maps.map_by_id(map_id)` into `Mediator(map_definition=…)` (every downstream layer was already map-aware, GM-09a–f2). NEW GAME / ENTER build `current_map_id`; RESTART (pause + game-over) rebuilds the CURRENT game's map read live off `self.mediator.map_definition.map_id` via `_restart_current_game` (so restarting a Continued River game gives River even when the picker sits on Lake); Continue installs the SAVED map and never consults the picker; the tutorial stays Classic. Only `main`+`app_controller`+`menu_screens` change; the headless/agent/recursive/RL entries construct `Mediator(map_definition=…)` directly and never meet the title picker.
+- GM-10a (D-041) opens GM-10 with the simulation CALENDAR. `config.WEEK_LENGTH_STEPS` defines a "week" in sim steps; `Mediator.increment_time`, after the COMPLETE tick (post queued-return settlement), holds a new `"week"` pause reason when `mediator.week_calendar` is on, the tick crossed a new boundary, and the run is not game over. `"week"` joins `_PAUSE_REASONS` (frozen by the existing gate; never cleared by Space/speed); `week_index` is a `steps`-derived property and `resolve_week_boundary()` releases the pause. The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it, so RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, and frame-limited/headless runs never pause — the calendar branch is never taken off the human path, so no `env.py`/checkpoint/save change and no determinism risk. The human shell adds `AppScreen.OFFER`: `AppController.reconcile_week_boundary()` (per-frame AFTER `reconcile_game_over`, so a terminal tick wins; cancelling any armed gesture via the pinned letterbox-cancel before switching) promotes a pending boundary to a modal whose armed Continue (`menu_screens.offer_menu_layout`/`draw_offer_screen`) resolves the week; `main` renders it over the frozen frame, resolves-then-autosaves on a mid-offer window close, and consumes the offer frame's audio silently; `save_game._require_quiescent` blocks saving while a boundary is pending. Persistence + the RL observation/offer are deferred to GM-10h/GM-10b.
 - `src/progression.py` owns current line/station/economy rules, canonical delivery and credit counters, purchased-line state, and explicitly refreshed unlock caches without importing entities, UI, clocks, or RNG. `Mediator` remains the compatibility facade through explicit writable properties and real public methods; it owns station/path-button identity, active-station slicing, locks/blinks, and delivery/purchase side-effect ordering.
 - `src/route_planner.py` owns stateless route queries, path compression and selection, and lazy boarding/bulk planning proposals without importing pygame or gameplay entities at runtime. `Mediator` remains the public compatibility and side-effect facade: it supplies fresh RNG-ordered destinations, graphs, and resolver callbacks, owns every travel-plan map write and passenger mutation, and applies each yielded proposal before the planner resumes over the live collection. Bulk planning emits explicit arrival, route, and fallback phases; its in-frame selection loop preserves raw-arrival provenance, destination-iterator finalization, callback lifetime, and live local-reference timing through facade effects.
 - `src/path_lifecycle.py` owns path creation, topology completion without automatic locomotive allocation, replacement, invalidation, selection, removal, color release, and button reassignment as a dependency-light stateless component; removal is a rider-conserving snapshot/rollback transaction that alights each onboard rider (crediting destination-shape deliveries) before any collection mutation, with `src/path_removal_snapshot.py` capturing the complete topology, holder, service, progression, blink/lock, and RNG footprint for exact-identity restoration. `src/fleet_management.py` separately owns stateless explicit assignment, empty-preferred then fewest-rider occupied-locomotive eligibility, queued return, cancellation of the earliest queued return, a narrow idempotent reconcile for provably-safe residual fleet shapes, transactional detachment, whole-consist retirement, and post-tick settlement behind public `Mediator` facades. `src/carriage_management.py` owns deterministic fewest/earliest attachment and most/latest capacity-safe detachment; `src/carriage_transaction_snapshot.py` and `src/fleet_validation.py` provide exact graph/RNG/service/intrinsic rollback plus shared ownership, composition, capacity, queue, and service-cache canonicality. `src/entity/metro.py` remains the sole passenger holder and owns one ordered attached-only `Carriage` list; total capacity derives from `_base_capacity` plus each `src/entity/carriage.py` capacity. `src/path_replacement.py` performs replacement preflight, semantic metro binding, and commit effects; `src/path_replacement_geometry.py` builds isolated geometry; and `src/path_replacement_snapshot.py` preserves total inventory, exact composition/intrinsics, passengers, service cache, topology, and RNG before reconciling every stopped Metro after successful replanning. `Mediator` remains the canonical owner of directly writable topology and fleet collections, maps, flags, factories, and entities.
diff --git a/GAME_RULES.md b/GAME_RULES.md
index 0c1e625..0f6a9e1 100644
--- a/GAME_RULES.md
+++ b/GAME_RULES.md
@@ -157,6 +157,7 @@ This document summarizes the game rules currently implemented in code.
   - R: restart (game-over screen).
   - ESC: exit (game-over screen).
 - The pause menu holds its own pause reason: opening it while SPACE-paused keeps both, and resuming from the menu releases only the menu hold, so the game stays paused until SPACE (or a speed button) clears the user pause. Speed-button selections still clear only the user pause and never the menu hold; the keyboard speed keys only set the speed and never unpause.
+- Weekly calendar (interactive play only): every fixed span of simulation time (a "week") the game pauses at a week boundary and shows a modal; click Continue to resume, and the sim carries on from exactly where it froze with no time backlog. This pause is its own reason — SPACE and the speed buttons cannot dismiss it, and saving is blocked until you Continue (closing the window mid-week resumes the game past the boundary via Continue). The calendar is a human-play feature: headless, RL, tutorial, and frame-limited runs never pause for a week. (GM-10a lays the calendar; the end-of-week upgrade choice arrives in later units.)
 - Autosave: opening the pause menu and Exit to Title each write a single autosave to `saves/autosave.json`, and closing the window mid-run keeps it, so the title screen's Continue reloads the game exactly where you left off (releasing the menu pause, honoring a held SPACE pause). Reaching game over deletes the autosave, so a finished run cannot be Continued; every autosave is best-effort and never blocks play or exit.
 - Tutorial: a coached playthrough reached from the title screen. It runs a real seeded game with on-screen prompts that walk through drawing a line, rerouting it, adding a train, delivering a passenger, overload pressure, pausing, and changing speed; each lesson advances when you actually perform it (overload advances after a few seconds of watching). Press Esc to skip or leave at any point. The tutorial game never ends (so a first-timer cannot lose mid-lesson) and never autosaves or records a high score. It is presentation only and changes no game rules or balance.
 - Settings: a Settings screen, reached from the title or pause menu (Back returns to whichever opened it, and opening it from the pause menu keeps the game paused), toggles fullscreen, steps the master/music/SFX volumes in 25% increments, and toggles reduced motion. Settings persist to `saves/settings.json` and survive restart; fullscreen applies to the live window and reduced motion holds the passenger-warning, station-unlock, and path-button blinks steady while suppressing the snap-blip rings (the master and SFX volumes scale the procedural audio cues). Settings are presentation-only and change no game balance; a missing or corrupt settings file falls back to the defaults and never blocks play.
diff --git a/PROGRESS.md b/PROGRESS.md
index 330afa9..562bf13 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -179,3 +179,4 @@
 - Began the map/save integration with GM-09f, the SAVE-SCHEMA v2 map field (D-038) -- the first of a plan-review-driven split (save-schema, then high-score identity, then the in-game menu). The save schema gains `SAVE_SCHEMA_VERSION_V2 = 2` (a superset of v1) with two additive top-level keys `mapId`/`mapDefinitionVersion`, so a non-Classic game (river/delta/lake) saves and loads with its map intact; `validate_save` is two-phase (read + support-check `schemaVersion` with a named error BEFORE choosing the version-aware exact-key set, so a v1-doc-with-map-keys and a v2-doc-without both fail closed). `serialize_game` replaces the old `_require_classic_map` guard with a fail-closed pair: STRUCTURAL `map_definition == resolve_map(id, version)` (generalizing GM-09b's `== CLASSIC`, since a v2 save records only the identity and rebuilds terrain from the registry on load) and a shared `_require_legal_map_state` (stations on the map's land, `consumed_tunnels <= num_tunnels`) applied on serialize AND post-load, so a forged illegal state is refused both ways. `deserialize_game` synthesizes `classic@1` for a v1 doc (keys absent) and resolves the map fail-closed for v2 (unknown id / unsupported version raise), threading `map_definition` into the Mediator; tunnel counts stay derived. The byte-frozen `save-v1.json` is unchanged and still loads as Classic; the deterministic v1->v2 header-only upgrade is pinned by a new frozen `save-v2-classic.json` (15485 bytes, SHA `60f2bc16...` -- exactly Codex's prediction) that the idempotence + cross-process determinism tests target. HIGH-RISK, so escalated to a DUAL plan review (both lanes REVISE, direction + split confirmed) that drove the two load-bearing choices: the guard must be STRUCTURAL (mere resolvability fails open into the GM-09b forged-Classic bug -- verified: 2 of 20 seed-0 CLASSIC stations sit in RIVER's band) and identity alone needs STATE-legality (a valid identity + illegal state is still corrupt). The DUAL impl review (harness SHIP + Codex FIX-FIRST) folded a latent serialize fail-open (`getattr(...) or CLASSIC` would coerce a FALSEY `MapDefinition` into `classic@1` and lose its terrain -- now defaults only on `is None`) and made `_validate_map_identity` a true non-empty-ASCII/no-whitespace mirror of `rl.manifest_schema` (both matched the code-vs-D-038-contract gap), with regressions plus a forged-over-budget LOAD test. Full `py313` suite green (1450 tests, 12 skips); the three GM-09b/d/e "not serializable" tests flipped to round-trips (the forged-classic rejection stays green). GM-09f2 (high-score `mapDefinitionVersion`) is next, then GM-09f3 (in-game menu, last so it can't feed an alternate map to the still-classic-hardcoded score recorder).
 - Continued the map/save integration with GM-09f2, the HIGH-SCORE map identity (D-039) -- the second of the GM-09f split, landing map-awareness in the recorder BEFORE the menu makes non-Classic maps selectable, so GM-09f3 needs zero recorder change. Both game-over surfaces UNIFY on the live mediator: `app_controller._record_highscore` hands the seam `self.mediator` (not `.deliveries`) and `main.run_game`'s promotion closure drops its `SimpleNamespace(deliveries=...)` wrapper, so the frame-accurate reconcile and the window-close QUIT both call the IDENTICAL `record_highscore(mediator)`, which reads `mediator.map_definition.{map_id, map_definition_version}` DIRECTLY (no `or classic` default -- a missing map records nothing rather than mislabelling). `highscores` becomes schema v2 keyed by the full `(map, mapDefinitionVersion, rulesVersion)` identity via one shared `_identity` helper (sort + cap + rank, so no predicate keys on a subset), with `record_score` gaining a required `map_definition_version` and the entry `map` tightened to the save's mapId grammar; `stateContract` stays stable. A legacy v1 board is NOT migrated -- START-EMPTY -- because a v1 `map="classic"` label is not provably accurate (the recorder was classic-hardcoded while GM-09f made non-Classic saves loadable via Continue), so synthesizing `classic@1` would preserve contamination. HIGH-RISK -> DUAL plan review (both REVISE, design UPHELD) drove the whole-mediator seam (REQUIRED to keep MAJOR-3: a minimal context would force the controller to read the map), the START-EMPTY pivot (Codex MAJOR-2, which also killed a migrate-before-validate hazard), the ONE-`_identity`-helper rank fix (else classic@2 miscounts against classic@1), and the two omitted test files (`test_gm07d_run_game_loop` real-recorder stubs + `test_gm07e`'s local spy). Full `py313` suite green (1459 tests, 12 skips); `highscores.py` 272 lines. GM-09f3 (in-game map menu) is the final GM-09f sub-unit.
 - COMPLETED GM-09f with GM-09f3, the in-game MAP MENU (D-040) -- the payoff that lets a human pick `classic`/`river`/`delta`/`lake` from the title. `AppController` gains `current_map_id` (default classic), cycled by an appended title `map` control (`title_layout` appends the key so prior title rects stay byte-identical; `draw_title_screen` gains `current_map_id` and paints a `Map: {Name}` button; `main` threads `controller.current_map_id`). The `build_game` seam becomes uniformly `Callable[[str], GameTriple]` -- `main.run_game`'s `build_game(map_id)` resolves `map_by_id(map_id)` into `Mediator(map_definition=...)` (every downstream layer was already map-aware, GM-09a-f2). NEW GAME / ENTER build the picker; RESTART (pause + game-over) rebuilds the CURRENT game's map read live off `self.mediator.map_definition.map_id` (`_restart_current_game`), so restarting a Continued River game gives River even with the picker on Lake; Continue installs the SAVED map; the tutorial stays Classic. Dual plan review (both REVISE, architecture UPHELD): Codex caught the Restart-switches-map MAJOR the harness rated acceptable, drove the uniform seam arity, the 11-callable fake update (incl. the dangerous `_title_build_game(mediator=None)` positional collision), and the crossing-gate composition test; alphabetical cycle order kept. Editing app_controller/main/menu_screens rotates the live RL content fingerprint (expected; no fixture repin -- `EXPECTED_LF_TRAINING` pins only training sources). Full `py313` suite green (1472 tests, 12 skips); app_controller 424, main 440, menu_screens 297 lines. GM-09 (maps + save/high-score/menu integration) is COMPLETE; GM-10 (weekly progression) opens next.
+- Opened GM-10 with GM-10a, the simulation CALENDAR (D-041) -- the foundation for weekly progression. A "week" is `config.WEEK_LENGTH_STEPS` (1200 ≈ 20s at 1x); `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement), holds a new `"week"` pause reason when the calendar is enabled, a new boundary crossed (`old//W < steps//W`), and not game over. `"week"` joins `_PAUSE_REASONS` (never cleared by Space/speed); `week_index` is `steps`-derived (no new persisted scalar); `resolve_week_boundary()` releases it. The calendar is OPT-IN, default OFF -- only INTERACTIVE `main.run_game` (build_game/build_from, gated on `max_frames is None`) enables it, so RL/tutorial/headless never pause. The human shell adds `AppScreen.OFFER`: `reconcile_week_boundary()` (per-frame AFTER game-over reconcile, cancelling any gesture) promotes to a modal whose armed Continue resolves the week; window-close mid-offer resolves+autosaves; offer-frame audio consumed silently; saving blocked while pending. HIGH-RISK -> DUAL plan review, both REVISE (harness 1 BLOCKER; Codex 2 BLOCKER + 4 MAJOR with reproduced counterexamples). GATING to the human shell resolved the BLOCKERs structurally: my first plan resolved a headless freeze only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` drives via `advance_exact` and the tutorial is a third direct-Mediator shell -- all would soft-lock at step 1200; gating (week_calendar default OFF) means the branch is never taken off the human path (no env.py/checkpoint/save change, no determinism risk). Codex also refuted my "pause is trajectory-invariant" probe (it bypassed the FixedStepClock cadence) -- gating moots it. The hold-after-full-tick (settlement), terminal precedence, gesture-cancel+arming, and window-close edges were all folded with pinned regressions. Full `py313` suite green (1488 tests, 12 skips). GM-10b (dedicated-RNG offers) opens next.
diff --git a/README.md b/README.md
index 3b9f888..44ef9f8 100644
--- a/README.md
+++ b/README.md
@@ -66,6 +66,7 @@ Set `PYTHON` to a specific interpreter path when `python` is not the intended ex
 * Opening the pause menu autosaves your game to `saves/autosave.json`; Exit to Title rewrites the same save before leaving, and closing the window mid-run keeps it, so Continue on the title screen resumes exactly where you left off. Reaching game over deletes the autosave, so a finished run cannot be Continued.
 * Finishing a run records its lifetime deliveries to a high-score leaderboard at `saves/highscores.json` (ranked and capped per map and rules version); a new best shows a compact indicator on the game-over screen.
 * Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
+* Every week of play the game pauses at a week boundary and shows a modal; click Continue to resume (the sim carries on with no time backlog). This is an interactive-play feature — headless, RL, and frame-limited runs never pause for a week.
 * The top-left HUD shows lifetime passengers delivered, currently spendable line credits, unassigned locomotives, and unassigned carriages as separate values.
 * Each filled grey circle at the bottom is an unused unlocked metro line slot.
 * Hold an assigned colored circle, drag through the replacement station order, and release on the final station to redraw that line; the selected circle is outlined and an invalid repeated-station draft turns red.
diff --git a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
index 1518838..3d77db1 100644
--- a/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
+++ b/docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md
@@ -251,3 +251,9 @@ Reason: the leaderboard schema already keyed by `map` (GM-07d) but the recorder
 Decision: GM-09f3 (the FINAL GM-09f sub-unit) adds the in-game MAP MENU — a title-screen picker so a human can actually select `classic`/`river`/`delta`/`lake`, completing the map/save integration. `AppController` gains `current_map_id` (default `classic`), cycled in place by a new appended title control `map` (the picker button shows `Map: {Name}` and clicking it advances over `KNOWN_MAP_IDS`, wrapping). The `build_game` seam becomes uniformly `Callable[[str], GameTriple]`: `__init__` seeds `current_map_id` first and calls `build_game(current_map_id)`, and `main.run_game`'s `build_game(map_id)` resolves `map_by_id(map_id)` into `Mediator(map_definition=…)` (the whole terrain/crossing/save/high-score/RL stack was already map-aware, GM-09a–f2). NEW GAME (the title `new_game` click and the `Enter` shortcut) builds `current_map_id`; RESTART (pause-menu Restart, game-over `R`, game-over Restart) rebuilds the CURRENT game's map read live off `self.mediator.map_definition.map_id`, via a dedicated `_restart_current_game`; and Continue (`_continue_game`/`build_from`) installs the SAVED map and never consults the picker. The tutorial stays Classic (`build_tutorial` unchanged — a fixed coached lesson). The appended `map` key keeps `new_game`/`continue`/`exit`/`settings`/`tutorial` rects byte-identical (`_stacked_buttons` positions by ordinal); `draw_title_screen` gains a `current_map_id` param and `main` threads `controller.current_map_id` into it.

 Reason: the save (GM-09f) and high-score (GM-09f2) recorders were deliberately made map-aware FIRST, so the menu — landing LAST — needs zero recorder change: selection simply flows the chosen `MapDefinition` into the one place that builds the game. The DUAL plan review (both REVISE, architecture UPHELD) drove three load-bearing choices. (1) The EXPLICIT `build_game(map_id)` seam over a zero-arg closure that reads `controller.current_map_id`: `build_game` is passed INTO `AppController` before the controller exists, so a back-reference would need a late-binding forward/nonlocal ref; the cost is a uniform (grep-driven) update of every controller `build_game` test fake. (2) RESTART preserves the CURRENT game's map, NOT the picker (Codex MAJOR-1, verified reachable): with the picker on `lake`, Continuing a River save then Restarting must replay River — so restart reads `self.mediator.map_definition.map_id`, while only New Game/Enter use the picker. (3) The crossing/tunnel GATE must compose with selection end-to-end (Codex MINOR-3): a selected River game's committed crossing consumes a tunnel against the budget, not just paints terrain. Alphabetical cycle order (`classic→delta→lake→river`) is kept (deterministic, violates no curated-order contract); Classic leads and is the default. Editing `app_controller`/`main`/`menu_screens` rotates the live environment-content fingerprint, so a pre-GM-09f3 RL manifest fails resume/eval by default — expected and correct; no frozen fixture is repinned (`EXPECTED_LF_TRAINING` pins only the RL training sources, untouched here). This COMPLETES GM-09f (maps + save/high-score/menu integration); GM-10 (weekly progression) opens next.
+
+## D-041
+
+Decision: GM-10a opens GM-10 (weekly progression) with the simulation CALENDAR — a deterministic week boundary that pauses the sim for an explicit player continue, the foundation the later sub-units (GM-10b offers, GM-10c choice UI, GM-10d-g upgrades, GM-10h persistence) build on. A "week" is `config.WEEK_LENGTH_STEPS` sim steps (provisional 1200 ≈ 20 s at 1×, a GM-11 balance target). `Mediator.increment_time`, AFTER the complete tick (post queued-return settlement — placement matters, review MAJOR), holds a new `"week"` pause reason when the calendar is enabled, this tick crossed a new boundary (`old_steps // W < steps // W`, integer division so 1×/2×/4× never skip), and the run is NOT game over (so a terminal tick promotes to GAME_OVER, review MAJOR). `"week"` joins `_PAUSE_REASONS` and freezes the sim through the existing gate; unlike `"user"`/`"menu"` it is never cleared by the Space toggle or speed buttons. `week_index` is DERIVED from the already-persisted `steps` (no new stored scalar). The human shell promotes a pending boundary to a new `AppScreen.OFFER` modal via `AppController.reconcile_week_boundary()` — run per-frame AFTER `reconcile_game_over`, no-op unless PLAYING/not-terminal, cancelling any armed gameplay gesture through the pinned letterbox-cancel before switching (review MAJOR) — whose armed Continue (down→up on the control) calls `mediator.resolve_week_boundary()` and resumes PLAYING (review MAJOR). Closing the window mid-offer resolves then autosaves (window-close→Continue promise, review MINOR); the offer frame's audio deltas are consumed silently (review MINOR); saving is blocked while a boundary is pending (a clearer error over `validate_save`'s existing vocabulary rejection). The calendar is OPT-IN, default OFF: only INTERACTIVE `main.run_game` (`build_game`/`build_from`, gated on `max_frames is None`) enables it; RL (`MiniMetroEnv`/`PlayerPixelEnv`), the tutorial, frame-limited/headless smoke runs, and all tests leave it off. NO save-schema and NO checkpoint-schema change; the RL observation of the week and mid-offer persistence are deferred to GM-10b/GM-10h.
+
+Reason: the DUAL plan review (both REVISE) was decisive — the harness caught a BLOCKER and Codex went far deeper (2 BLOCKER + 4 MAJOR with reproduced live counterexamples). (1) My first plan resolved a headless freeze only in `MiniMetroEnv._complete_step`, but `PlayerPixelEnv` (the first-class RL boundary) drives via `GameSession.advance_exact` and the tutorial is a third direct-Mediator shell — all would soft-lock permanently at step 1200. GATING the calendar to interactive human play (a `week_calendar` flag, default OFF) resolves every headless shell structurally (the hold never occurs) and removes the `env.py` change entirely. (2) My "a pause is trajectory-invariant" premise was FALSE — my probe used direct `increment_time` (fixed 17 ms) and bypassed the `(17,17,16)` `FixedStepClock` cadence, which a pause resets, so `time_ms` diverges at identical `steps`; but gating keeps the calendar out of every deterministic/RL/exact-tick path, so their trajectory is byte-identical (the branch is never taken), and the cadence reset is PRE-EXISTING behavior shared by the `user`/`menu` pauses on the already-non-deterministic human wall-clock path — so no version bump and no clock fix here. (3) The hold placement, terminal precedence, gesture-cancel/arming, window-close, and audio edges were all reproduced by Codex and folded with pinned regressions. Persistence is deferred because GM-10h owns it and `week_index` rides on `steps`; the RL offer integration is GM-10b/GM-12. `WEEK_LENGTH_STEPS=1200` is a provisional foundation default (fixed, not escalating — escalation is GM-11). GM-10b (deterministic dedicated-RNG offers) opens next.
```
