import inspect
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from test import mediator_test_support as support

# isort: split

import mediator as mediator_module

# isort: split

from mediator import Mediator


def bare_mediator():
    mediator = Mediator.__new__(Mediator)
    coordinator = getattr(mediator_module, "InputCoordinator", None)
    if coordinator is not None:
        mediator._input = coordinator()
    return mediator


class RecordingRect:
    def __init__(self, width, height, events):
        self.width = width
        self.height = height
        self._centerx = 0
        self._top = 0
        self.events = events

    @property
    def centerx(self):
        return self._centerx

    @centerx.setter
    def centerx(self, value):
        self.events.append(("centerx", value))
        self._centerx = value

    @property
    def top(self):
        return self._top

    @top.setter
    def top(self, value):
        self.events.append(("top", value))
        self._top = value

    @property
    def bottom(self):
        return self._top + self.height

    def copy(self):
        self.events.append(("copy", self._top))
        mediator_module.game_over_button_spacing = 13
        copied = RecordingRect(self.width, self.height, self.events)
        copied._centerx = self._centerx
        copied._top = self._top
        return copied


class RecordingButton:
    def __init__(self, index, events):
        self.index = index
        self.events = events

    def start_unlock_blink(self, time_ms):
        self.events.append(("blink", self.index, time_ms))


class RecordingProgression:
    def __init__(self, name, unlocked_num_paths, events):
        self.name = name
        self.unlocked_num_paths = unlocked_num_paths
        self.events = events

    def set_unlocked_num_paths(self, value):
        self.events.append(("set", self.name, value))
        return self.unlocked_num_paths, value

    def can_purchase_resolved_path_button_idx(
        self, button_idx, *, next_button_idx, price
    ):
        self.events.append(("can", self.name, button_idx, next_button_idx, price))
        return self.name == "old"


class TestMediatorInputContract(support.MediatorTestCase):
    def test_public_input_coordinator_signatures_are_frozen(self):
        expected = {
            "prepare_layout": "(self, width: 'int', height: 'int') -> 'None'",
            "update_unlocked_num_paths": "(self) -> 'None'",
            "update_path_button_lock_states": "(self) -> 'None'",
            "can_purchase_path_button_idx": "(self, button_idx: 'int') -> 'bool'",
            "try_purchase_path_button": "(self, button: 'PathButton') -> 'bool'",
            "try_purchase_path_button_by_index": "(self, button_idx: 'int | None' = None) -> 'bool'",
            "step_time": "(self, dt_ms: 'int') -> 'None'",
            "get_surface_size": "(self, screen: 'pygame.surface.Surface') -> 'tuple[int, int]'",
            "render": "(self, screen: 'pygame.surface.Surface', renderer: 'object | None' = None, alpha: 'float' = 1.0) -> 'None'",
            "handle_game_over_click": "(self, position: 'Point') -> 'str | None'",
            "react_mouse_event": "(self, event: 'MouseEvent') -> 'None'",
            "react_keyboard_event": "(self, event: 'KeyboardEvent') -> 'None'",
            "react": "(self, event: 'Event | None') -> 'None'",
            "get_containing_entity": "(self, position: 'Point')",
            "set_paused": "(self, paused: 'bool') -> 'None'",
            "set_game_speed": "(self, speed_multiplier: 'int') -> 'None'",
            "apply_speed_action": "(self, action: 'SpeedAction') -> 'None'",
            "is_speed_button_active": "(self, action: 'SpeedAction') -> 'bool'",
            "apply_action": "(self, action: 'object') -> 'bool'",
        }

        self.assertEqual(
            {
                name: str(inspect.signature(getattr(Mediator, name)))
                for name in expected
            },
            expected,
        )

    def test_layout_dependencies_are_resolved_at_original_effect_points(self):
        mediator = bare_mediator()
        mediator.path_buttons = [object()]
        mediator.speed_buttons = [object()]
        mediator.game_over_restart_rect = None
        mediator.game_over_exit_rect = None
        mediator._layout_size = None
        events = []

        def late_speed(buttons, width, height):
            events.append(("speed", buttons, width, height))
            mediator_module.game_over_button_width = 44
            mediator_module.game_over_button_height = 12

        def path_positions(buttons, width, height):
            events.append(("path", buttons, width, height))
            mediator_module.update_speed_button_positions = late_speed
            mediator_module.game_over_font_size = 18

        def validate_layout(width, height):
            events.append(("validate", width, height))

        def early_speed(*_args):
            raise AssertionError("speed updater captured before path updater")

        def rect_factory(_x, _y, width, height):
            events.append(("rect", width, height))
            return RecordingRect(width, height, events)

        with (
            patch.multiple(
                mediator_module,
                update_path_button_positions=path_positions,
                update_speed_button_positions=early_speed,
                validate_resource_control_layout=validate_layout,
                game_over_font_size=3,
                game_over_button_width=10,
                game_over_button_height=6,
                game_over_button_spacing=2,
            ),
            patch.object(mediator_module.pygame, "Rect", rect_factory),
        ):
            Mediator.prepare_layout(mediator, 200, 100)

        self.assertEqual(events[0], ("validate", 200, 100))
        self.assertEqual(events[1], ("path", mediator.path_buttons, 200, 100))
        self.assertEqual(events[2], ("speed", mediator.speed_buttons, 200, 100))
        self.assertEqual(events[3], ("rect", 44, 12))
        self.assertEqual(mediator.game_over_restart_rect.centerx, 100)
        self.assertEqual(mediator.game_over_restart_rect.top, 96)
        self.assertEqual(mediator.game_over_exit_rect.top, 121)
        self.assertEqual(mediator._layout_size, (200, 100))

    def test_surface_size_preserves_isinstance_and_independent_fallbacks(self):
        events = []

        class NumericSubclass(int):
            def __int__(self):
                events.append("int-width")
                return 23

        class Screen:
            def get_width(self):
                events.append("width")
                return NumericSubclass(17)

            def get_height(self):
                events.append("height")
                return object()

        mediator = bare_mediator()
        with patch.multiple(mediator_module, screen_width=901, screen_height=502):
            size = Mediator.get_surface_size(mediator, Screen())

        self.assertEqual(size, (23, 502))
        self.assertEqual(events, ["width", "height", "int-width"])

        bool_screen = SimpleNamespace(
            get_width=lambda: True,
            get_height=lambda: 12.9,
        )
        self.assertEqual(Mediator.get_surface_size(mediator, bool_screen), (1, 12))

    def test_unlock_update_binds_old_progression_before_public_query(self):
        events = []
        old = RecordingProgression("old", 1, events)
        new = RecordingProgression("new", 99, events)
        mediator = bare_mediator()
        mediator._progression = old
        mediator.path_buttons = [RecordingButton(i, events) for i in range(4)]
        mediator.time_ms = 77

        def query():
            events.append("query")
            mediator._progression = new
            return 3

        mediator.get_unlocked_num_paths = query
        mediator.update_path_button_lock_states = lambda: events.append("locks")

        Mediator.update_unlocked_num_paths(mediator)

        self.assertEqual(
            events,
            [
                "query",
                ("set", "old", 3),
                ("blink", 1, 77),
                ("blink", 2, 77),
                "locks",
            ],
        )
        self.assertEqual(old.unlocked_num_paths, 1)
        self.assertEqual(new.unlocked_num_paths, 3)
        self.assertEqual(mediator.unlocked_num_paths, 3)

    def test_purchase_check_binds_old_progression_before_public_price_hook(self):
        events = []
        old = RecordingProgression("old", 1, events)
        new = RecordingProgression("new", 1, events)
        mediator = bare_mediator()
        mediator._progression = old
        mediator.get_next_path_button_idx_to_purchase = lambda: 2

        def price(button_idx):
            events.append(("price", button_idx))
            mediator._progression = new
            return 17

        mediator.get_purchase_price_for_path_button_idx = price

        self.assertTrue(Mediator.can_purchase_path_button_idx(mediator, 2))
        self.assertEqual(
            events,
            [("price", 2), ("can", "old", 2, 2, 17)],
        )
        self.assertIs(mediator._progression, new)

    def test_dispatch_preserves_isinstance_subclasses_and_mouse_precedence(self):
        class MouseType:
            pass

        class KeyboardType:
            pass

        class BothEvents(MouseType, KeyboardType):
            pass

        mediator = bare_mediator()
        mediator.react_mouse_event = MagicMock()
        mediator.react_keyboard_event = MagicMock()
        event = BothEvents()

        with patch.multiple(
            mediator_module,
            MouseEvent=MouseType,
            KeyboardEvent=KeyboardType,
        ):
            Mediator.react(mediator, event)

        mediator.react_mouse_event.assert_called_once_with(event)
        mediator.react_keyboard_event.assert_not_called()

    def test_mouse_up_prefers_path_button_for_dual_class_entity(self):
        class StationType:
            pass

        class PathButtonType:
            pass

        class SpeedButtonType:
            pass

        class ButtonType:
            pass

        class DualButton(PathButtonType, SpeedButtonType):
            path = "path"
            is_locked = True
            action = "speed_4"

        class MouseEventType:
            MOUSE_DOWN = "down"
            MOUSE_UP = "up"
            MOUSE_MOTION = "motion"

        entity = DualButton()
        event = SimpleNamespace(event_type="up", position=object())
        mediator = bare_mediator()
        mediator.get_containing_entity = lambda _position: entity
        mediator.is_mouse_down = True
        mediator.is_creating_path = False
        mediator.remove_path = MagicMock()
        mediator.try_purchase_path_button = MagicMock()
        mediator.apply_speed_action = MagicMock()

        with patch.multiple(
            mediator_module,
            Station=StationType,
            PathButton=PathButtonType,
            SpeedButton=SpeedButtonType,
            Button=ButtonType,
            MouseEventType=MouseEventType,
        ):
            Mediator.react_mouse_event(mediator, event)

        self.assertFalse(mediator.is_mouse_down)
        mediator.remove_path.assert_called_once_with("path")
        mediator.try_purchase_path_button.assert_not_called()
        mediator.apply_speed_action.assert_not_called()

    def test_mouse_station_type_is_resolved_after_public_hit_test(self):
        class EarlyStation:
            pass

        class LateStation:
            pass

        class MouseEventType:
            MOUSE_DOWN = "down"
            MOUSE_UP = "up"
            MOUSE_MOTION = "motion"

        entity = LateStation()
        mediator = bare_mediator()
        mediator.is_mouse_down = False
        mediator.start_path_on_station = MagicMock()

        def hit_test(_position):
            mediator_module.Station = LateStation
            return entity

        mediator.get_containing_entity = hit_test
        with patch.multiple(
            mediator_module,
            Station=EarlyStation,
            MouseEventType=MouseEventType,
        ):
            Mediator.react_mouse_event(
                mediator,
                SimpleNamespace(event_type="down", position=(1, 2)),
            )

        self.assertTrue(mediator.is_mouse_down)
        mediator.start_path_on_station.assert_called_once_with(entity)

    def test_action_and_keyboard_subclasses_keep_public_dispatch(self):
        class Action(dict):
            pass

        class ActionType(str):
            pass

        mediator = bare_mediator()
        mediator.is_game_over = False
        self.assertTrue(
            Mediator.apply_action(mediator, Action(type=ActionType("noop")))
        )

        mediator.try_purchase_path_button_by_index = MagicMock(return_value=True)
        self.assertFalse(
            Mediator.apply_action(
                mediator,
                Action(type=ActionType("buy_line"), path_index=True),
            )
        )
        mediator.try_purchase_path_button_by_index.assert_not_called()

        class KeyboardEventType:
            KEY_UP = "up"

        fake_pygame = SimpleNamespace(K_SPACE=10, K_1=11, K_2=12, K_3=13)
        mediator.is_paused = False
        mediator.set_game_speed = MagicMock()
        with (
            patch.object(mediator_module, "KeyboardEventType", KeyboardEventType),
            patch.object(mediator_module, "pygame", fake_pygame),
        ):
            Mediator.react_keyboard_event(
                mediator, SimpleNamespace(event_type="up", key=10)
            )
            Mediator.react_keyboard_event(
                mediator, SimpleNamespace(event_type="up", key=13)
            )

        self.assertTrue(mediator.is_paused)
        mediator.set_game_speed.assert_called_once_with(4)

    def test_step_time_and_speed_actions_resolve_public_hooks_dynamically(self):
        mediator = bare_mediator()
        events = []
        mediator.increment_time = lambda dt_ms: events.append(("time", dt_ms))
        Mediator.step_time(mediator, 17)

        def set_paused(paused):
            events.append(("paused", paused))
            mediator.set_game_speed = lambda speed: events.append(("late-speed", speed))

        mediator.set_paused = set_paused
        mediator.set_game_speed = lambda speed: events.append(("early-speed", speed))
        Mediator.apply_speed_action(mediator, "pause")
        Mediator.apply_speed_action(mediator, "speed_4")

        self.assertEqual(
            events,
            [
                ("time", 17),
                ("paused", True),
                ("late-speed", 4),
                ("paused", False),
            ],
        )
