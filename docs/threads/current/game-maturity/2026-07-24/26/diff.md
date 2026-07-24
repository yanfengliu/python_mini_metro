# GM-09f3 in-game map menu — implementation diff (post-fold)

Source: app_controller.py (current_map_id + picker + restart-preserves-map), main.py (build_game(map_id) + title render), menu_screens.py (title 'map' control). New test: test_gm09f3_map_menu.py (incl. the end-to-end run_game selection→river→crossing integration). Touched: the controller/run-loop fakes. Docs: D-040, README, GAME_RULES, ARCHITECTURE, PROGRESS.

## Production source
```diff
diff --git a/src/app_controller.py b/src/app_controller.py
index 67dc327..214cfe9 100644
--- a/src/app_controller.py
+++ b/src/app_controller.py
@@ -22,6 +22,7 @@ from event.keyboard import KeyboardEvent
 from event.mouse import MouseEvent
 from event.type import KeyboardEventType, MouseEventType
 from geometry.point import Point
+from maps import KNOWN_MAP_IDS
 from settings import DEFAULT_SETTINGS
 from ui.menu_screens import pause_menu_layout, settings_menu_layout, title_layout

@@ -30,6 +31,9 @@ _MENU_REASON = "menu"
 _LOAD_FAILURE_NOTICE = "Could not load the saved game."
 _VOLUME_STEP = 25
 _VOLUME_MAX = 100
+# GM-09f3 (D-040): the title map picker cycles KNOWN_MAP_IDS; Classic is the
+# default and the first selectable (it leads KNOWN_MAP_IDS' sorted order).
+_DEFAULT_MAP_ID = "classic"


 class AppScreen(Enum):
@@ -78,7 +82,7 @@ class AppController:

     def __init__(
         self,
-        build_game: Callable[[], GameTriple],
+        build_game: Callable[[str], GameTriple],
         start_state: AppScreen = AppScreen.TITLE,
         *,
         build_from: Callable[[object], GameTriple] | None = None,
@@ -112,7 +116,14 @@ class AppController:
         self.current_settings = (
             settings.load() if settings is not None else DEFAULT_SETTINGS
         )
-        self.mediator, self.renderer, self.session = build_game()
+        # GM-09f3 (D-040): the title map picker. `current_map_id` is the map a NEW
+        # game will build; the title cycles it over KNOWN_MAP_IDS, and it seeds the
+        # first build below so the seam is uniformly `build_game(map_id)` (never a
+        # zero-arg vs one-arg split). RESTART, by contrast, rebuilds the CURRENT
+        # game's map (read live off the mediator), not the picker; Continue installs
+        # the saved map and never consults the picker.
+        self.current_map_id = _DEFAULT_MAP_ID
+        self.mediator, self.renderer, self.session = build_game(self.current_map_id)
         # A cold start directly in TUTORIAL (e.g. run_game(start_state=TUTORIAL))
         # must build the seeded, game-over-suppressed tutorial and its progress,
         # not leave the ordinary build_game() triple — which would game-over and
@@ -181,11 +192,27 @@ class AppController:
         elif self.state is AppScreen.TUTORIAL:
             self._handle_tutorial(event)

-    def _start_new_game(self) -> None:
-        self.mediator, self.renderer, self.session = self._build_game()
+    def _start_new_game(self, map_id: str) -> None:
+        # Build a fresh game on `map_id`. The title New Game / Enter pass the picker
+        # (`current_map_id`); RESTART surfaces pass the CURRENT game's map so a
+        # restart replays the same terrain, never the picker's pending choice
+        # (GM-09f3 review MAJOR-1).
+        self.mediator, self.renderer, self.session = self._build_game(map_id)
         self.notice = None
         self.state = AppScreen.PLAYING

+    def _cycle_map(self) -> None:
+        # The title map picker advances to the next map, wrapping KNOWN_MAP_IDS.
+        # Only ever holds a registered id, so `.index` cannot fail (GM-09f3).
+        index = KNOWN_MAP_IDS.index(self.current_map_id)
+        self.current_map_id = KNOWN_MAP_IDS[(index + 1) % len(KNOWN_MAP_IDS)]
+
+    def _restart_current_game(self) -> None:
+        # Restart replays the CURRENT game's map (read live off the mediator), not
+        # the picker -- so restarting a Continued River game gives River even when
+        # the picker sits on Lake (GM-09f3 review MAJOR-1).
+        self._start_new_game(self.mediator.map_definition.map_id)
+
     def _continue_game(self) -> None:
         # Continue is inert without a proven-loadable autosave: peek gates the
         # attempt (F4), a failed load surfaces a notice and stays on TITLE, and
@@ -251,7 +278,7 @@ class AppController:
             self._close_pause_menu(AppScreen.PLAYING)
         elif armed == "restart":
             self._close_pause_menu(AppScreen.PLAYING)
-            self._start_new_game()
+            self._restart_current_game()
         elif armed == "exit_to_title":
             # Rewrite the byte-identical boundary save BEFORE the menu reason is
             # released, so a later Continue reloads the menu-entry document.
@@ -265,14 +292,14 @@ class AppController:

     def _handle_title(self, event: object) -> None:
         if _is_key_up(event, pygame.K_RETURN):
-            self._start_new_game()
+            self._start_new_game(self.current_map_id)
             return
         position = _mouse_up_position(event)
         if position is None:
             return
         layout = title_layout(screen_width, screen_height)
         if _clicked(layout, "new_game", position):
-            self._start_new_game()
+            self._start_new_game(self.current_map_id)
         elif _clicked(layout, "continue", position):
             self._continue_game()
         elif _clicked(layout, "exit", position):
@@ -281,13 +308,17 @@ class AppController:
             self._open_settings(AppScreen.TITLE)
         elif _clicked(layout, "tutorial", position):
             self._start_tutorial()
+        elif _clicked(layout, "map", position):
+            # GM-09f3: cycle the picker in place; the title stays put and the label
+            # updates, and the next New Game builds the chosen map.
+            self._cycle_map()

     def _handle_game_over(self, event: object) -> None:
         # Mirrors the historical loop-inline branch: R restarts, Escape exits,
         # and clicks resolve through the prepared game-over rects.
         if isinstance(event, KeyboardEvent):
             if _is_key_up(event, pygame.K_r):
-                self._start_new_game()
+                self._restart_current_game()
             elif _is_key_up(event, pygame.K_ESCAPE):
                 self._autosave_delete()
                 raise SystemExit
@@ -297,7 +328,7 @@ class AppController:
             return
         action = self.mediator.handle_game_over_click(position)
         if action == "restart":
-            self._start_new_game()
+            self._restart_current_game()
         elif action == "exit":
             self._autosave_delete()
             raise SystemExit
diff --git a/src/main.py b/src/main.py
index 856a38e..39e9978 100644
--- a/src/main.py
+++ b/src/main.py
@@ -26,6 +26,7 @@ from highscores import (
     record_score,
     save_highscores,
 )
+from maps import map_by_id
 from mediator import Mediator
 from rendering.game_renderer import GameRenderer
 from save_game import load_game, save_game
@@ -213,8 +214,11 @@ def run_game(
     game_surface = pygame.Surface((screen_width, screen_height))
     clock = pygame.time.Clock()

-    def build_game():
-        mediator = Mediator()
+    def build_game(map_id="classic"):
+        # GM-09f3 (D-040): build on the chosen map. The controller passes the title
+        # picker's id for a new game, or the current game's id for a restart; a
+        # registered id always resolves (map_by_id raises on an unknown one).
+        mediator = Mediator(map_definition=map_by_id(map_id))
         renderer = GameRenderer()
         session = GameSession(mediator, step_observer=renderer)
         session.prepare_layout(game_surface)
@@ -370,7 +374,7 @@ def run_game(

         game_surface.fill(screen_color)
         if state == AppScreen.TITLE:
-            draw_title_screen(game_surface)
+            draw_title_screen(game_surface, current_map_id=controller.current_map_id)
             if peek_autosave():
                 _draw_title_continue_button(game_surface)
             if controller.notice:
diff --git a/src/ui/menu_screens.py b/src/ui/menu_screens.py
index a21ff5a..9203a93 100644
--- a/src/ui/menu_screens.py
+++ b/src/ui/menu_screens.py
@@ -75,11 +75,12 @@ def title_layout(width: int, height: int) -> dict[str, pygame.Rect]:
     """Deterministic, disjoint hit-test rects for the title-screen controls."""

     # Stacked buttons anchored to the middle slot; each new control is APPENDED
-    # (Settings after GM-07c, Tutorial after GM-08c) so the prior rects stay
-    # byte identical, and the heading stays anchored to the first key.
+    # (Settings after GM-07c, Tutorial after GM-08c, map picker after GM-09f3) so
+    # the prior rects stay byte identical, and the heading stays anchored to the
+    # first key.
     return _stacked_buttons(
         width,
-        ("new_game", "continue", "exit", "settings", "tutorial"),
+        ("new_game", "continue", "exit", "settings", "tutorial", "map"),
         height // 2 - game_over_button_height - game_over_button_spacing,
     )

@@ -147,9 +148,15 @@ def _draw_heading(surface: pygame.Surface, width: int, bottom: int, label: str)


 def draw_title_screen(
-    surface: pygame.Surface, continue_available: bool = False
+    surface: pygame.Surface,
+    continue_available: bool = False,
+    current_map_id: str = "classic",
 ) -> None:
-    """Paint deterministic title chrome; draw Continue only when available."""
+    """Paint deterministic title chrome; draw Continue only when available.
+
+    GM-09f3 (D-040): the appended map-picker button shows the map a New Game will
+    build (``current_map_id``); clicking it cycles the choice.
+    """

     width, height = surface.get_size()
     layout = title_layout(width, height)
@@ -160,6 +167,7 @@ def draw_title_screen(
     _draw_button(surface, layout["exit"], "Exit")
     _draw_button(surface, layout["settings"], "Settings")
     _draw_button(surface, layout["tutorial"], "Tutorial")
+    _draw_button(surface, layout["map"], f"Map: {current_map_id.title()}")


 def draw_notice(surface: pygame.Surface, message: str) -> None:
```

## Test surgery (fakes + stubs)
```diff
diff --git a/test/test_gm07a_app_controller.py b/test/test_gm07a_app_controller.py
index 099ab08..2f61624 100644
--- a/test/test_gm07a_app_controller.py
+++ b/test/test_gm07a_app_controller.py
@@ -116,6 +116,9 @@ class _RecordingMediator:
         self.log = log
         self.name = name
         self.is_game_over = False
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.held = []
         self.game_over_result = None

@@ -167,7 +170,7 @@ class _RecordingSession:
 def _fake_factory(log):
     triples = []

-    def build():
+    def build(map_id="classic"):
         index = len(triples)
         mediator = _RecordingMediator(log, f"mediator-{index}")
         renderer = SimpleNamespace(name=f"renderer-{index}")
@@ -428,7 +431,7 @@ class TestGM07aMidDragMenuEntry(unittest.TestCase):
         renderer = GameRenderer()
         session = GameSession(mediator, step_observer=renderer)

-        def build():
+        def build(map_id="classic"):
             return mediator, renderer, session

         controller = _controller(self, build, playing)
diff --git a/test/test_gm07a_pause_menu_arming.py b/test/test_gm07a_pause_menu_arming.py
index e22017b..a01bd24 100644
--- a/test/test_gm07a_pause_menu_arming.py
+++ b/test/test_gm07a_pause_menu_arming.py
@@ -15,6 +15,8 @@ import unittest

 sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

+from types import SimpleNamespace
+
 import pygame

 from app_controller import AppController, AppScreen
@@ -35,6 +37,9 @@ class _FakeMediator:
     def __init__(self, name: str) -> None:
         self.name = name
         self.is_game_over = False
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.held: list[str] = []

     def hold_pause_reason(self, reason: str) -> None:
@@ -58,7 +63,7 @@ class _FakeSession:
 def _factory(log: list):
     triples: list[tuple[_FakeMediator, object, _FakeSession]] = []

-    def build():
+    def build(map_id="classic"):
         index = len(triples)
         triple = (
             _FakeMediator(f"mediator-{index}"),
diff --git a/test/test_gm07a_run_game_loop.py b/test/test_gm07a_run_game_loop.py
index 18b6041..0cfbd0c 100644
--- a/test/test_gm07a_run_game_loop.py
+++ b/test/test_gm07a_run_game_loop.py
@@ -63,6 +63,9 @@ class _RecordingMediator:
         self.log = log
         self.name = name
         self.is_game_over = False
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.held: list[str] = []

     def hold_pause_reason(self, reason: str) -> None:
@@ -131,7 +134,7 @@ def _run_loop(frames_events, **run_kwargs):
     renderers: list[_RecordingRenderer] = []
     sessions: list[_RecordingSession] = []

-    def build_mediator() -> _RecordingMediator:
+    def build_mediator(map_definition=None) -> _RecordingMediator:
         mediator = _RecordingMediator(log, f"mediator-{len(mediators)}")
         mediators.append(mediator)
         return mediator
@@ -167,7 +170,7 @@ def _run_loop(frames_events, **run_kwargs):
         patch("main.GameRenderer", side_effect=build_renderer),
         patch(
             "main.draw_title_screen",
-            side_effect=lambda surface: log.append(("chrome", "title")),
+            side_effect=lambda surface, **kwargs: log.append(("chrome", "title")),
         ),
         patch(
             "main.draw_pause_menu",
diff --git a/test/test_gm07c_autosave_controller.py b/test/test_gm07c_autosave_controller.py
index 35add15..7ca2c42 100644
--- a/test/test_gm07c_autosave_controller.py
+++ b/test/test_gm07c_autosave_controller.py
@@ -115,6 +115,9 @@ class _RecordingMediator:
     def __init__(self, name):
         self.name = name
         self.is_game_over = False
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.held = []
         self.game_over_result = None

@@ -152,7 +155,7 @@ def _factories():
         triples.append((mediator, renderer, session))
         return mediator, renderer, session

-    def build_game():
+    def build_game(map_id="classic"):
         return _wrap(_RecordingMediator(f"mediator-{len(triples)}"))

     def build_from(loaded):
diff --git a/test/test_gm07c_continue_roundtrip.py b/test/test_gm07c_continue_roundtrip.py
index ef4a380..2c89a39 100644
--- a/test/test_gm07c_continue_roundtrip.py
+++ b/test/test_gm07c_continue_roundtrip.py
@@ -161,7 +161,7 @@ class _FileAutosave:
         return load_game(self.path)


-def _title_build_game(mediator=None):
+def _title_build_game(map_id="classic", mediator=None):
     subject = Mediator(seed=0) if mediator is None else mediator
     return subject, SimpleNamespace(), _RecSession(subject)

@@ -175,7 +175,11 @@ class TestGM07cContinueRoundtrip(unittest.TestCase):
         env = _line_env(seed)
         controller = _continue_controller(
             self,
-            lambda: (env.mediator, SimpleNamespace(), _RecSession(env.mediator)),
+            lambda map_id="classic": (
+                env.mediator,
+                SimpleNamespace(),
+                _RecSession(env.mediator),
+            ),
             start_state=_screen(self, "PLAYING"),
             build_from=_identity_build_from,
             autosave=autosave,
diff --git a/test/test_gm07c_run_game_loop.py b/test/test_gm07c_run_game_loop.py
index e196e0a..d0238f3 100644
--- a/test/test_gm07c_run_game_loop.py
+++ b/test/test_gm07c_run_game_loop.py
@@ -85,7 +85,7 @@ def _drive_window_close(

     mediators: list[_LoopMediator] = []

-    def build_mediator() -> _LoopMediator:
+    def build_mediator(map_definition=None) -> _LoopMediator:
         mediator = _LoopMediator(game_over)
         mediators.append(mediator)
         return mediator
diff --git a/test/test_gm07d_recorder_controller.py b/test/test_gm07d_recorder_controller.py
index 3e84598..820fbc8 100644
--- a/test/test_gm07d_recorder_controller.py
+++ b/test/test_gm07d_recorder_controller.py
@@ -73,6 +73,9 @@ class _RecordingMediator:
     def __init__(self, name):
         self.name = name
         self.is_game_over = False
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.held = []
         self.game_over_result = None

@@ -116,7 +119,7 @@ def _factories(mediator_factory):
         triples.append((mediator, renderer, session))
         return mediator, renderer, session

-    def build_game():
+    def build_game(map_id="classic"):
         return _wrap(mediator_factory(len(triples)))

     def build_from(loaded):
diff --git a/test/test_gm07d_run_game_loop.py b/test/test_gm07d_run_game_loop.py
index e5cc7d2..7547873 100644
--- a/test/test_gm07d_run_game_loop.py
+++ b/test/test_gm07d_run_game_loop.py
@@ -93,7 +93,7 @@ def _drive_window_close(

     mediators: list[_LoopMediator] = []

-    def build_mediator() -> _LoopMediator:
+    def build_mediator(map_definition=None) -> _LoopMediator:
         mediator = _LoopMediator(game_over)
         mediators.append(mediator)
         return mediator
diff --git a/test/test_gm07e_game_over_reconcile.py b/test/test_gm07e_game_over_reconcile.py
index 7d4da76..9987a37 100644
--- a/test/test_gm07e_game_over_reconcile.py
+++ b/test/test_gm07e_game_over_reconcile.py
@@ -49,6 +49,9 @@ class _RecordingMediator:
     def __init__(self, name):
         self.name = name
         self.is_game_over = False
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.held = []
         self.game_over_result = None

@@ -132,7 +135,7 @@ def _factories(mediator_factory):
         triples.append((mediator, renderer, session))
         return mediator, renderer, session

-    def build_game():
+    def build_game(map_id="classic"):
         return _wrap(mediator_factory(len(triples)))

     def build_from(loaded):
@@ -272,6 +275,9 @@ class TestGM07eReconcileGameOverController(unittest.TestCase):
 class _LoopMediator:
     def __init__(self):
         self.is_game_over = False
+        self.map_definition = SimpleNamespace(
+            map_id="classic", map_definition_version=1
+        )
         self.deliveries = 11
         self.held = []

@@ -325,7 +331,7 @@ def _drive(testcase, frame_batches, *, max_frames=None, record_result=None):
     mediators: list[_LoopMediator] = []
     draw_log: list[str] = []

-    def build_mediator() -> _LoopMediator:
+    def build_mediator(map_definition=None) -> _LoopMediator:
         mediator = _LoopMediator()
         mediators.append(mediator)
         return mediator
diff --git a/test/test_gm08a_settings_controller.py b/test/test_gm08a_settings_controller.py
index d61298d..c992cd2 100644
--- a/test/test_gm08a_settings_controller.py
+++ b/test/test_gm08a_settings_controller.py
@@ -49,7 +49,7 @@ class _FakeSession:


 def _factory():
-    def build():
+    def build(map_id="classic"):
         return (_FakeMediator(), object(), _FakeSession())

     return build
diff --git a/test/test_gm08c_tutorial_app.py b/test/test_gm08c_tutorial_app.py
index 864d9ca..7b90d35 100644
--- a/test/test_gm08c_tutorial_app.py
+++ b/test/test_gm08c_tutorial_app.py
@@ -57,7 +57,7 @@ def _controller(with_tutorial=True, autosave=None, highscores=None):
     play = _triple()
     tut = _triple()

-    def build_game():
+    def build_game(map_id="classic"):
         return play

     def build_tutorial():
@@ -95,7 +95,7 @@ class TestGM08cTutorialController(unittest.TestCase):
         # would game-over and freeze with no overlay).
         tut = _triple()
         controller = AppController(
-            lambda: _triple(),
+            lambda map_id="classic": _triple(),
             start_state=AppScreen.TUTORIAL,
             build_tutorial=lambda: tut,
         )
```

## New: test/test_gm09f3_map_menu.py
```python
"""GM-09f3 contract: the in-game map menu (D-040).

The title screen picks a map; New Game builds it; RESTART replays the CURRENT
game's map (not the picker); Continue loads the saved map; the tutorial stays
Classic. The recorder/save layers are already map-aware (GM-09f/f2), so this unit
only adds selection + threading the chosen MapDefinition into the game build.
"""

from __future__ import annotations

import contextlib
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from app_controller import AppController, AppScreen
from config import screen_height, screen_width
from event.keyboard import KeyboardEvent
from event.mouse import MouseEvent
from event.type import KeyboardEventType, MouseEventType
from geometry.point import Point
from maps import CLASSIC, KNOWN_MAP_IDS, RIVER, map_by_id
from mediator import Mediator
from ui.menu_screens import draw_title_screen, pause_menu_layout, title_layout

pygame.init()


class _FakeMediator:
    """A controller-shaped stub carrying a real `map_definition` (for restart)."""

    def __init__(self, map_definition):
        self.map_definition = map_definition
        self.is_game_over = False
        self.held: list[str] = []
        self.game_over_result = None

    def hold_pause_reason(self, reason):
        if reason not in self.held:
            self.held.append(reason)

    def release_pause_reason(self, reason):
        if reason in self.held:
            self.held.remove(reason)

    def handle_game_over_click(self, position):
        return self.game_over_result


def _spy_build_game():
    calls: list[str] = []

    def build_game(map_id="classic"):
        calls.append(map_id)
        mediator = _FakeMediator(map_by_id(map_id))
        return mediator, SimpleNamespace(), SimpleNamespace(dispatch=lambda event: None)

    build_game.calls = calls
    return build_game


def _click(controller, key):
    rect = title_layout(screen_width, screen_height)[key]
    controller.handle_event(
        MouseEvent(MouseEventType.MOUSE_UP, Point(rect.centerx, rect.centery))
    )


def _key_up(controller, key):
    controller.handle_event(KeyboardEvent(KeyboardEventType.KEY_UP, key))


class TestGM09f3Picker(unittest.TestCase):
    def test_default_map_is_classic(self):
        controller = AppController(_spy_build_game(), start_state=AppScreen.TITLE)
        self.assertEqual(controller.current_map_id, "classic")

    def test_clicking_map_cycles_through_known_maps_and_wraps(self):
        controller = AppController(_spy_build_game(), start_state=AppScreen.TITLE)
        seen = [controller.current_map_id]
        for _ in range(len(KNOWN_MAP_IDS)):
            _click(controller, "map")
            seen.append(controller.current_map_id)
        # A full cycle visits every known map once and returns to the start.
        self.assertEqual(seen[:-1], list(KNOWN_MAP_IDS))
        self.assertEqual(seen[-1], KNOWN_MAP_IDS[0], "the cycle wraps to the first map")

    def test_new_game_builds_the_picked_map(self):
        build_game = _spy_build_game()
        controller = AppController(build_game, start_state=AppScreen.TITLE)
        while controller.current_map_id != "river":
            _click(controller, "map")
        _click(controller, "new_game")
        self.assertEqual(controller.state, AppScreen.PLAYING)
        self.assertEqual(
            build_game.calls[-1], "river", "New Game builds the picker map"
        )

    def test_enter_starts_the_picked_map(self):
        build_game = _spy_build_game()
        controller = AppController(build_game, start_state=AppScreen.TITLE)
        while controller.current_map_id != "delta":
            _click(controller, "map")
        _key_up(controller, pygame.K_RETURN)
        self.assertEqual(build_game.calls[-1], "delta")


class TestGM09f3RestartPreservesMap(unittest.TestCase):
    """Codex MAJOR-1: Restart replays the CURRENT game's map, not the picker."""

    def test_pause_restart_uses_the_current_game_map_not_the_picker(self):
        build_game = _spy_build_game()
        # Start directly in a RIVER game, then move the picker to a DIFFERENT map.
        controller = AppController(build_game, start_state=AppScreen.PLAYING)
        controller.mediator = _FakeMediator(RIVER)
        controller.current_map_id = "lake"  # the picker sits elsewhere
        # Open the pause menu, then arm + fire Restart.
        _key_up(controller, pygame.K_ESCAPE)
        self.assertEqual(controller.state, AppScreen.PAUSE_MENU)
        self._arm_and_fire_pause_restart(controller)
        self.assertEqual(
            build_game.calls[-1],
            "river",
            "restart replays the played map, not the picker",
        )

    def _arm_and_fire_pause_restart(self, controller):
        rect = pause_menu_layout(screen_width, screen_height)["restart"]
        centre = Point(rect.centerx, rect.centery)
        controller.handle_event(MouseEvent(MouseEventType.MOUSE_DOWN, centre))
        controller.handle_event(MouseEvent(MouseEventType.MOUSE_UP, centre))

    def test_game_over_restart_after_continue_keeps_the_loaded_map(self):
        build_game = _spy_build_game()
        # Continue loads a RIVER game via build_from; the picker sits on lake.
        loaded = _FakeMediator(RIVER)
        controller = AppController(
            build_game,
            start_state=AppScreen.PLAYING,
            build_from=lambda mediator: (
                mediator,
                SimpleNamespace(),
                SimpleNamespace(dispatch=lambda event: None),
            ),
            autosave=SimpleNamespace(peek=lambda: True, load=lambda: loaded),
        )
        controller.current_map_id = "lake"
        controller.state = AppScreen.TITLE
        _click(controller, "continue")
        self.assertIs(controller.mediator, loaded, "Continue installs the river save")
        # Game over, then R to restart -> must rebuild RIVER, not the lake picker.
        controller.mediator.is_game_over = True
        controller.state = AppScreen.GAME_OVER
        _key_up(controller, pygame.K_r)
        self.assertEqual(build_game.calls[-1], "river")

    def test_game_over_mouse_restart_after_continue_keeps_the_loaded_map(self):
        # Distinct from the K_r path: the game-over CLICK restart branch
        # (handle_game_over_click -> "restart") must ALSO preserve the played map,
        # not the picker (Codex impl-review MINOR-1).
        build_game = _spy_build_game()
        loaded = _FakeMediator(RIVER)
        loaded.game_over_result = "restart"  # a game-over click resolves to restart
        controller = AppController(
            build_game,
            start_state=AppScreen.PLAYING,
            build_from=lambda mediator: (
                mediator,
                SimpleNamespace(),
                SimpleNamespace(dispatch=lambda event: None),
            ),
            autosave=SimpleNamespace(peek=lambda: True, load=lambda: loaded),
        )
        controller.current_map_id = "lake"
        controller.state = AppScreen.TITLE
        _click(controller, "continue")
        controller.mediator.is_game_over = True
        controller.state = AppScreen.GAME_OVER
        controller.handle_event(MouseEvent(MouseEventType.MOUSE_UP, Point(10, 10)))
        self.assertEqual(
            build_game.calls[-1], "river", "the game-over CLICK restart keeps the map"
        )


class TestGM09f3ContinueAndTutorial(unittest.TestCase):
    def test_continue_loads_the_saved_map_and_leaves_the_picker(self):
        build_game = _spy_build_game()
        loaded = _FakeMediator(RIVER)
        controller = AppController(
            build_game,
            start_state=AppScreen.TITLE,
            build_from=lambda mediator: (
                mediator,
                SimpleNamespace(),
                SimpleNamespace(dispatch=lambda event: None),
            ),
            autosave=SimpleNamespace(peek=lambda: True, load=lambda: loaded),
        )
        controller.current_map_id = "lake"
        _click(controller, "continue")
        self.assertIs(controller.mediator, loaded)
        self.assertEqual(
            controller.current_map_id, "lake", "Continue does not disturb the picker"
        )

    def test_tutorial_ignores_the_picker(self):
        build_game = _spy_build_game()
        tutorial_calls: list[int] = []

        def build_tutorial():
            tutorial_calls.append(1)
            return (
                _FakeMediator(CLASSIC),
                SimpleNamespace(),
                SimpleNamespace(dispatch=lambda event: None),
            )

        controller = AppController(
            build_game, start_state=AppScreen.TITLE, build_tutorial=build_tutorial
        )
        while controller.current_map_id != "river":
            _click(controller, "map")
        _click(controller, "tutorial")
        self.assertEqual(len(tutorial_calls), 1, "the tutorial seam built the game")
        self.assertEqual(
            build_game.calls, ["classic"], "the picker never reached the tutorial build"
        )


class TestGM09f3Render(unittest.TestCase):
    def test_title_paints_a_deterministic_map_button(self):
        surface_a = pygame.Surface((screen_width, screen_height))
        surface_b = pygame.Surface((screen_width, screen_height))
        draw_title_screen(surface_a, current_map_id="river")
        draw_title_screen(surface_b, current_map_id="river")
        self.assertEqual(
            pygame.image.tobytes(surface_a, "RGB"),
            pygame.image.tobytes(surface_b, "RGB"),
            "the title render is deterministic",
        )
        # The map button occupies a nonempty region of title_layout["map"].
        rect = title_layout(screen_width, screen_height)["map"]
        self.assertTrue(
            surface_a.get_rect().contains(rect), "the map rect is on-screen"
        )

    def test_map_label_reflects_the_selected_id(self):
        classic_surface = pygame.Surface((screen_width, screen_height))
        river_surface = pygame.Surface((screen_width, screen_height))
        draw_title_screen(classic_surface, current_map_id="classic")
        draw_title_screen(river_surface, current_map_id="river")
        # The only chrome that depends on the map id is the map button, so a
        # different selection paints a different title (the label changed).
        self.assertNotEqual(
            pygame.image.tobytes(classic_surface, "RGB"),
            pygame.image.tobytes(river_surface, "RGB"),
            "the button label changes with the selected map",
        )

    def test_appending_map_keeps_the_earlier_title_rects_byte_identical(self):
        # Pin the EXACT pre-map rects (not just relative order): appending "map" must
        # move NONE of them, so a 1px drift of the whole stack fails here (Codex
        # impl-review MINOR). The map rect is the appended sixth slot.
        layout = title_layout(screen_width, screen_height)
        self.assertEqual(
            {key: tuple(layout[key]) for key in layout},
            {
                "new_game": (810, 458, 300, 64),
                "continue": (810, 540, 300, 64),
                "exit": (810, 622, 300, 64),
                "settings": (810, 704, 300, 64),
                "tutorial": (810, 786, 300, 64),
                "map": (810, 868, 300, 64),
            },
        )


class _IntegrationSession:
    def __init__(self, mediator):
        self.mediator = mediator

    def prepare_layout(self, surface):
        pass

    def dispatch(self, event):
        pass

    def advance(self, elapsed_ms):
        return SimpleNamespace(alpha=0.0)


class TestGM09f3RunGameIntegration(unittest.TestCase):
    def test_run_game_selection_builds_a_real_river_mediator_end_to_end(self):
        # The FINAL link (Codex impl-review MAJOR): cycling the picker to river + New
        # Game must make main.run_game's REAL build_game resolve the id into
        # Mediator(map_definition=RIVER) -- and that selection-built mediator must
        # itself enforce the crossing/tunnel gate. A regression that ignored map_id
        # (always Classic) keeps every OTHER test green (controller tests use fake
        # build_game spies; run-loop tests patch main.Mediator; the focused gate test
        # builds Mediator directly), so drive the real loop and build a REAL Mediator.
        import main

        built: list = []

        def build_mediator(map_definition=None, **kwargs):
            mediator = Mediator(seed=0, map_definition=map_definition)
            built.append(mediator)
            return mediator

        layout = title_layout(screen_width, screen_height)

        def _up(rect):
            return SimpleNamespace(
                type=pygame.MOUSEBUTTONUP,
                pos=(rect.centerx, rect.centery),
                button=1,
            )

        # Frame 1 cycles the picker classic->delta->lake->river (3 clicks); frame 2
        # New Game builds it; frame 3 quits.
        frames = [
            [_up(layout["map"]), _up(layout["map"]), _up(layout["map"])],
            [_up(layout["new_game"])],
            [SimpleNamespace(type=pygame.QUIT)],
        ]
        with contextlib.ExitStack() as stack:
            pygame_mock = stack.enter_context(patch("main.pygame"))
            stack.enter_context(patch("main.Mediator", side_effect=build_mediator))
            stack.enter_context(
                patch(
                    "main.GameSession",
                    side_effect=lambda m, **k: _IntegrationSession(m),
                )
            )
            stack.enter_context(
                patch(
                    "main.GameRenderer",
                    side_effect=lambda: SimpleNamespace(draw=lambda *a, **k: None),
                )
            )
            stack.enter_context(patch("main.write_autosave", lambda mediator: None))
            stack.enter_context(patch("main.delete_autosave", lambda: None))
            stack.enter_context(patch("main.peek_autosave", lambda: False))
            stack.enter_context(patch("main.draw_title_screen", lambda *a, **k: None))
            pygame_mock.QUIT = pygame.QUIT
            pygame_mock.MOUSEBUTTONUP = pygame.MOUSEBUTTONUP
            pygame_mock.MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN
            pygame_mock.MOUSEMOTION = pygame.MOUSEMOTION
            window = MagicMock()
            window.get_size.return_value = (screen_width, screen_height)
            pygame_mock.display.set_mode.return_value = window
            surface = MagicMock()
            surface.get_size.return_value = (screen_width, screen_height)
            pygame_mock.Surface.return_value = surface
            pygame_mock.time.Clock.return_value = SimpleNamespace(tick=lambda fps: 17)
            pygame_mock.event.get.side_effect = frames
            with self.assertRaises(SystemExit):
                main.run_game(start_state=AppScreen.TITLE)
        # built[0] is the initial classic title build; the New Game build is River.
        self.assertEqual(
            built[0].map_definition, CLASSIC, "the initial build is Classic"
        )
        selected = built[-1]
        self.assertEqual(
            selected.map_definition, RIVER, "New Game builds the picked RIVER map"
        )
        # ...and that SELECTION-built mediator enforces the crossing/tunnel gate.
        self.assertEqual(selected.consumed_tunnels, 0)
        selected.create_path_from_station_indices([2, 0])
        self.assertEqual(
            selected.consumed_tunnels, 1, "the selected river map's tunnel gate applies"
        )


class TestGM09f3GateComposition(unittest.TestCase):
    def test_a_selected_river_game_enforces_the_crossing_tunnel_gate(self):
        # Codex MINOR-3: selection must reach the real crossing/tunnel gate, not just
        # paint terrain. Build exactly as `build_game` does (map_by_id) and commit a
        # river-crossing line -> a tunnel is consumed against the budget.
        mediator = Mediator(seed=0, map_definition=map_by_id("river"))
        self.assertEqual(mediator.consumed_tunnels, 0)
        mediator.create_path_from_station_indices([2, 0])  # a left<->right crossing
        self.assertEqual(
            mediator.consumed_tunnels, 1, "the selected river map's tunnel gate applies"
        )
        self.assertEqual(mediator.map_definition, RIVER)


if __name__ == "__main__":
    unittest.main()
```
