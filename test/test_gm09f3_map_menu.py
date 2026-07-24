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
