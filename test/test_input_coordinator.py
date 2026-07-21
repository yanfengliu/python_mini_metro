import ast
import gc
import unittest
import weakref
from pathlib import Path
from types import SimpleNamespace

from test import mediator_test_support as support
from test.input_coordinator_direct_support import (
    Host,
    Point,
    RecordingButton,
    RecordingProgression,
    RecordingRect,
    RecordingRenderer,
    event,
)

# isort: split

import input_coordinator as input_coordinator_module
from input_coordinator import InputCoordinator


class TestInputCoordinator(support.MediatorTestCase):
    def setUp(self):
        self.events = []
        self.host = Host(self.events)
        self.coordinator = InputCoordinator()

    def test_component_is_stateless_dependency_light_and_non_retaining(self):
        self.assertFalse(hasattr(self.coordinator, "__dict__"))
        with self.assertRaises(AttributeError):
            self.coordinator.host = self.host

        source = Path(input_coordinator_module.__file__).read_text(encoding="utf-8")
        imports = {
            node.module or ""
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.ImportFrom)
        }
        imports.update(
            alias.name
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Import)
            for alias in node.names
        )
        self.assertLessEqual(
            imports,
            {
                "__future__",
                "collections.abc",
                "fleet_input",
                "input_coordinator_host",
                "path_handle_input",
                "path_handles",
                "typing",
            },
        )

        renderer = RecordingRenderer(self.events)

        class Resolver:
            def __call__(self):
                raise AssertionError("explicit renderer must bypass resolver")

        resolver = Resolver()
        resolver_ref = weakref.ref(resolver)
        screen = SimpleNamespace(get_width=lambda: 4, get_height=lambda: 5)
        self.host._layout_size = (4, 5)
        self.coordinator.render(
            self.host,
            screen,
            renderer,
            get_renderer_factory=resolver,
        )
        del resolver
        gc.collect()
        self.assertIsNone(resolver_ref())

    def test_prepare_layout_preserves_dependency_and_effect_order(self):
        self.host.path_buttons = ["path-button"]
        self.host.speed_buttons = ["speed-button"]

        def getter(name, value):
            def resolve():
                self.events.append(("get", name))
                return value

            return resolve

        def path_positions(buttons, width, height):
            self.events.append(("path", buttons, width, height))

        def speed_positions(buttons, width, height):
            self.events.append(("speed", buttons, width, height))

        def rect_factory(_x, _y, width, height):
            self.events.append(("rect", width, height))
            return RecordingRect(width, height, self.events)

        self.coordinator.prepare_layout(
            self.host,
            200,
            100,
            get_update_path_button_positions=getter("path-updater", path_positions),
            get_update_speed_button_positions=getter("speed-updater", speed_positions),
            get_game_over_font_size=getter("font", 18),
            get_rect_factory=getter("rect-factory", rect_factory),
            get_game_over_button_width=getter("button-width", 44),
            get_game_over_button_height=getter("button-height", 12),
            get_game_over_button_spacing=getter("spacing", 13),
        )

        self.assertEqual(
            self.events[:7],
            [
                ("get", "path-updater"),
                ("path", ["path-button"], 200, 100),
                ("get", "speed-updater"),
                ("speed", ["speed-button"], 200, 100),
                ("get", "font"),
                ("get", "rect-factory"),
                ("get", "button-width"),
            ],
        )
        self.assertLess(
            self.events.index(("get", "button-height")),
            self.events.index(("rect", 44, 12)),
        )
        self.assertLess(
            self.events.index("copy"), self.events.index(("get", "spacing"))
        )
        self.assertEqual(self.host.game_over_restart_rect.centerx, 100)
        self.assertEqual(self.host.game_over_restart_rect.top, 96)
        self.assertEqual(self.host.game_over_exit_rect.top, 121)
        self.assertEqual(self.host._layout_size, (200, 100))

    def test_layout_failure_preserves_exact_partial_state(self):
        self.host.game_over_restart_rect = "old-restart"
        self.host.game_over_exit_rect = "old-exit"
        self.host._layout_size = (1, 2)

        def fail_speed(*_args):
            self.events.append("speed-failure")
            raise RuntimeError("speed layout")

        with self.assertRaisesRegex(RuntimeError, "speed layout"):
            self.coordinator.prepare_layout(
                self.host,
                10,
                20,
                get_update_path_button_positions=lambda: (
                    lambda *_args: self.events.append("path")
                ),
                get_update_speed_button_positions=lambda: fail_speed,
                get_game_over_font_size=lambda: 1,
                get_rect_factory=lambda: RecordingRect,
                get_game_over_button_width=lambda: 2,
                get_game_over_button_height=lambda: 3,
                get_game_over_button_spacing=lambda: 4,
            )

        self.assertEqual(self.events, ["path", "speed-failure"])
        self.assertEqual(self.host.game_over_restart_rect, "old-restart")
        self.assertEqual(self.host.game_over_exit_rect, "old-exit")
        self.assertEqual(self.host._layout_size, (1, 2))

    def test_unlock_and_purchase_keep_old_progression_capture_points(self):
        old = RecordingProgression("old", self.events, unlocked=1, price=17)
        new = RecordingProgression("new", self.events, unlocked=99, price=3)
        self.host._progression = old
        self.host.time_ms = 73
        self.host.path_buttons = [
            RecordingButton(str(index), self.events) for index in range(4)
        ]

        def unlocked_query():
            self.events.append("query-unlocked")
            self.host._progression = new
            return 3

        self.host.get_unlocked_num_paths = unlocked_query
        self.coordinator.update_unlocked_num_paths(self.host)
        self.assertEqual(
            self.events,
            [
                "query-unlocked",
                ("set-unlocked", "old", 3),
                ("blink", "1", 73),
                ("blink", "2", 73),
                "update-locks",
            ],
        )
        self.assertEqual(new.unlocked_num_paths, 3)

        self.events.clear()
        self.host._progression = old
        self.host.get_next_path_button_idx_to_purchase = lambda: 2

        def price(_button_idx):
            self.events.append("price")
            self.host._progression = new
            return 17

        self.host.get_purchase_price_for_path_button_idx = price
        self.assertTrue(self.coordinator.can_purchase_path_button_idx(self.host, 2))
        self.assertEqual(
            self.events,
            ["price", ("can-purchase", "old", 2, 2, 17)],
        )

    def test_button_lock_and_purchase_effects_are_ordered(self):
        self.host._progression = RecordingProgression(
            "active", self.events, unlocked=2, price=9
        )
        buttons = [
            RecordingButton("0", self.events),
            RecordingButton("1", self.events),
            RecordingButton("2", self.events, locked=True),
        ]
        self.host.path_buttons = buttons
        self.coordinator.update_path_button_lock_states(self.host)
        self.assertEqual(
            self.events,
            [
                ("locked", "0", False),
                ("locked", "1", False),
                ("locked", "2", True),
            ],
        )

        self.events.clear()
        self.host.can_purchase_path_button_idx = lambda index: index == 2
        self.assertTrue(
            self.coordinator.try_purchase_path_button(self.host, buttons[2])
        )
        self.assertEqual(
            self.events,
            [("purchase", "active", 9), "update-unlocked"],
        )
        self.events.clear()
        self.assertTrue(
            self.coordinator.try_purchase_path_button_by_index(self.host, 2)
        )
        self.assertTrue(
            self.coordinator.try_purchase_path_button_by_index(self.host, True)
        )
        self.assertTrue(self.coordinator.try_purchase_path_button_by_index(self.host))
        self.assertFalse(
            self.coordinator.try_purchase_path_button_by_index(self.host, -1)
        )
        self.assertFalse(
            self.coordinator.try_purchase_path_button_by_index(self.host, len(buttons))
        )
        self.assertEqual(
            self.events,
            [
                ("try-button", buttons[2]),
                ("try-button", buttons[1]),
                ("try-button", buttons[2]),
            ],
        )

    def test_surface_render_and_terminal_click_contracts(self):
        class Numeric(int):
            def __int__(self):
                self.events.append("convert")
                return 31

        numeric = Numeric(7)
        numeric.events = self.events
        screen = SimpleNamespace(
            get_width=lambda: self.events.append("width") or numeric,
            get_height=lambda: self.events.append("height") or object(),
        )
        size = self.coordinator.get_surface_size(
            self.host,
            screen,
            get_screen_width=lambda: self.events.append("fallback-width") or 900,
            get_screen_height=lambda: self.events.append("fallback-height") or 500,
        )
        self.assertEqual(size, (31, 500))
        self.assertEqual(
            self.events,
            ["fallback-width", "fallback-height", "width", "height", "convert"],
        )

        self.events.clear()
        render_screen = object()
        self.host.get_surface_size = lambda _screen: (80, 60)
        self.host._layout_size = (1, 1)

        def renderer_factory():
            self.events.append("renderer-factory")
            return RecordingRenderer(self.events)

        self.coordinator.render(
            self.host,
            render_screen,
            alpha=0.25,
            get_renderer_factory=lambda: renderer_factory,
        )
        self.assertEqual(self.events[0], ("prepare", 80, 60))
        self.assertEqual(self.events[1], "renderer-factory")
        self.assertEqual(self.events[2][0], "draw")

        self.events.clear()
        self.host.is_game_over = True
        restart = RecordingRect(20, 10, self.events)
        restart.centerx = 10
        restart.top = 0
        self.host.game_over_restart_rect = restart
        self.host.game_over_exit_rect = restart
        point = Point((5, 5), self.events)
        self.assertEqual(
            self.coordinator.handle_game_over_click(self.host, point), "restart"
        )
        self.assertEqual(
            [entry for entry in self.events if entry[0] == "point"],
            [("point", (5, 5))],
        )

    def test_hit_testing_mouse_and_event_type_precedence(self):
        class Station:
            def __init__(self, result):
                self.result = result

            def contains(self, position):
                self.events.append(("station-contains", position))
                return self.result

        class PathButton:
            pass

        class SpeedButton:
            pass

        class Button:
            pass

        class DualButton(PathButton, SpeedButton):
            path = "line"
            is_locked = True
            action = "speed_4"

        Station.events = self.events
        first = Station(False)
        second = Station(True)
        self.host.stations = [first, second]
        self.host.buttons = [RecordingButton("button", self.events)]
        self.assertIs(
            self.coordinator.get_containing_entity(self.host, "position"), second
        )

        class MouseEventType:
            MOUSE_DOWN = "down"
            MOUSE_UP = "up"
            MOUSE_MOTION = "motion"

        dual = DualButton()
        self.host.get_containing_entity = lambda _position: dual
        self.host.is_mouse_down = True
        self.host.is_creating_path = False
        self.coordinator.react_mouse_event(
            self.host,
            event("up", position="point"),
            get_mouse_event_type=lambda: MouseEventType,
            get_station_type=lambda: Station,
            get_path_button_type=lambda: PathButton,
            get_speed_button_type=lambda: SpeedButton,
            get_button_type=lambda: Button,
        )
        self.assertFalse(self.host.is_mouse_down)
        self.assertIn(("remove", "line"), self.events)
        self.assertNotIn(("speed-action", "speed_4"), self.events)

        class Mouse:
            pass

        class Keyboard:
            pass

        class Both(Mouse, Keyboard):
            pass

        both = Both()
        self.host.react_mouse_event = lambda value: self.events.append(
            ("mouse-dispatch", value)
        )
        self.host.react_keyboard_event = lambda value: self.events.append(
            ("keyboard-dispatch", value)
        )
        self.coordinator.react(
            self.host,
            both,
            get_mouse_event_class=lambda: Mouse,
            get_keyboard_event_class=lambda: Keyboard,
        )
        self.assertIn(("mouse-dispatch", both), self.events)
        self.assertNotIn(("keyboard-dispatch", both), self.events)

    def test_keyboard_speed_time_and_structured_actions(self):
        class KeyboardEventType:
            KEY_UP = "up"

        self.coordinator.react_keyboard_event(
            self.host,
            event("up", key=10),
            get_keyboard_event_type=lambda: KeyboardEventType,
            get_pause_key=lambda: 10,
            get_speed_1_key=lambda: 11,
            get_speed_2_key=lambda: 12,
            get_speed_4_key=lambda: 13,
        )
        self.assertTrue(self.host.is_paused)
        self.coordinator.react_keyboard_event(
            self.host,
            event("up", key=13),
            get_keyboard_event_type=lambda: KeyboardEventType,
            get_pause_key=lambda: 10,
            get_speed_1_key=lambda: 11,
            get_speed_2_key=lambda: 12,
            get_speed_4_key=lambda: 13,
        )
        self.assertIn(("speed", 4), self.events)

        self.coordinator.step_time(self.host, 17)
        self.coordinator.apply_speed_action(self.host, "unknown")
        self.assertIn(("time", 17), self.events)
        self.assertIn(("paused", False), self.events)

        def active_states():
            return {
                action: self.coordinator.is_speed_button_active(self.host, action)
                for action in ("pause", "speed_1", "speed_2", "speed_4", "unknown")
            }

        self.assertEqual(
            active_states(),
            {
                "pause": False,
                "speed_1": False,
                "speed_2": False,
                "speed_4": True,
                "unknown": False,
            },
        )
        self.host.is_paused = True
        self.assertEqual(
            active_states(),
            {
                "pause": True,
                "speed_1": False,
                "speed_2": False,
                "speed_4": False,
                "unknown": False,
            },
        )
        self.host.is_paused = False
        self.host.game_speed_multiplier = 1
        self.assertTrue(self.coordinator.is_speed_button_active(self.host, "speed_1"))
        self.host.game_speed_multiplier = 2
        self.assertTrue(self.coordinator.is_speed_button_active(self.host, "speed_2"))

        class Action(dict):
            pass

        class ActionType(str):
            pass

        self.assertTrue(
            self.coordinator.apply_action(
                self.host,
                Action(type=ActionType("create_path"), stations=[0, 1], loop=True),
            )
        )
        self.assertTrue(
            self.coordinator.apply_action(
                self.host, Action(type=ActionType("remove_path"), path_id="id")
            )
        )
        self.assertFalse(
            self.coordinator.apply_action(
                self.host, Action(type=ActionType("buy_line"), path_index=True)
            )
        )
        self.assertTrue(
            self.coordinator.apply_action(self.host, Action(type=ActionType("noop")))
        )
        self.host.is_game_over = True
        self.assertFalse(
            self.coordinator.apply_action(self.host, Action(type=ActionType("noop")))
        )


if __name__ == "__main__":
    unittest.main()
