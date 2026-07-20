from types import SimpleNamespace

from test import mediator_test_support as support
from test.input_coordinator_direct_support import Host, Point, RecordingButton

# isort: split

from input_coordinator import InputCoordinator


class TestInputCoordinatorEdgeContract(support.MediatorTestCase):
    def setUp(self):
        self.events = []
        self.host = Host(self.events)
        self.coordinator = InputCoordinator()

    def test_purchase_missing_price_and_missing_next_index_short_circuit(self):
        button = RecordingButton("locked", self.events, locked=True)
        self.host.path_buttons = [button]
        self.host.can_purchase_path_button_idx = lambda index: index == 0
        self.host.get_purchase_price_for_path_button_idx = lambda index: (
            self.events.append(("price", index)) or None
        )

        self.assertFalse(self.coordinator.try_purchase_path_button(self.host, button))
        self.assertEqual(self.events, [("price", 0)])

        self.events.clear()
        self.host.get_next_path_button_idx_to_purchase = lambda: (
            self.events.append("next") or None
        )
        self.assertFalse(self.coordinator.try_purchase_path_button_by_index(self.host))
        self.assertEqual(self.events, ["next"])

    def test_nonterminal_click_and_locked_path_button_purchase(self):
        point = Point((4, 5), self.events)
        self.assertIsNone(self.coordinator.handle_game_over_click(self.host, point))
        self.assertEqual(self.events, [])

        class Station:
            pass

        class PathButton:
            path = None
            is_locked = True

        class SpeedButton:
            pass

        class Button:
            pass

        class MouseEventType:
            MOUSE_DOWN = "down"
            MOUSE_UP = "up"
            MOUSE_MOTION = "motion"

        entity = PathButton()
        self.host.is_mouse_down = True
        self.host.get_containing_entity = lambda _position: entity
        self.coordinator.react_mouse_event(
            self.host,
            SimpleNamespace(event_type="up", position=(9, 8)),
            get_mouse_event_type=lambda: MouseEventType,
            get_station_type=lambda: Station,
            get_path_button_type=lambda: PathButton,
            get_speed_button_type=lambda: SpeedButton,
            get_button_type=lambda: Button,
        )

        self.assertFalse(self.host.is_mouse_down)
        self.assertEqual(self.events, [("try-button", entity)])

    def test_speed_one_two_and_structured_action_fallthroughs(self):
        self.coordinator.apply_speed_action(self.host, "speed_1")
        self.coordinator.apply_speed_action(self.host, "speed_2")
        self.assertEqual(
            self.events,
            [
                ("speed", 1),
                ("paused", False),
                ("speed", 2),
                ("paused", False),
            ],
        )

        self.events.clear()
        self.assertFalse(
            self.coordinator.apply_action(self.host, {"type": "remove_path"})
        )
        self.assertFalse(self.coordinator.apply_action(self.host, {"type": "unknown"}))
        self.assertEqual(self.events, [])

    def test_hit_test_reads_replaced_buttons_after_station_scan(self):
        host = self.host

        class Button:
            def __init__(self, name, contains):
                self.name = name
                self.contains_result = contains

            def contains(self, position):
                self.events.append(("button", self.name, position))
                return self.contains_result

            @property
            def events(self):
                return host.events

        old_button = Button("old", True)
        new_button = Button("new", True)

        class ReplacingStation:
            def contains(self, position):
                host.events.append(("station", position))
                host.buttons = [new_button]
                return False

        host.stations = [ReplacingStation()]
        host.buttons = [old_button]

        self.assertIs(self.coordinator.get_containing_entity(host, (3, 7)), new_button)
        self.assertEqual(
            self.events,
            [("station", (3, 7)), ("button", "new", (3, 7))],
        )
