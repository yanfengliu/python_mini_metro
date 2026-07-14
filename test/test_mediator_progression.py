from test import mediator_test_support as support

# isort: split

from config import (
    button_color,
    initial_num_stations,
    num_stations,
    path_unlock_milestones,
    station_unlock_milestones,
    unlock_blink_duration_ms,
)
from mediator import Mediator


class TestMediatorProgression(support.MediatorTestCase):
    def test_progress_counters_keep_writable_legacy_aliases(self):
        mediator = Mediator()

        mediator.deliveries = 7
        self.assertEqual(mediator.total_travels_handled, 7)
        mediator.total_travels_handled = 8
        self.assertEqual(mediator.deliveries, 8)

        mediator.line_credits = 11
        self.assertEqual(mediator.score, 11)
        mediator.score = 12
        self.assertEqual(mediator.line_credits, 12)

    def test_initial_path_button_locks_match_unlocked_lines(self):
        mediator = Mediator()
        self.assertEqual(mediator.unlocked_num_paths, 1)
        self.assertFalse(mediator.path_buttons[0].is_locked)
        for button in mediator.path_buttons[1:]:
            self.assertTrue(button.is_locked)
            self.assertEqual(button.shape.color, button_color)

    def test_update_unlocked_paths_updates_button_locks(self):
        mediator = Mediator()
        mediator.purchased_num_paths = 2
        mediator.update_unlocked_num_paths()
        self.assertEqual(mediator.unlocked_num_paths, 2)
        self.assertFalse(mediator.path_buttons[0].is_locked)
        self.assertFalse(mediator.path_buttons[1].is_locked)
        for button in mediator.path_buttons[2:]:
            self.assertTrue(button.is_locked)

    def test_update_unlocked_paths_starts_button_blink(self):
        mediator = Mediator()
        second_button = mediator.path_buttons[1]

        self.assertFalse(second_button.is_unlock_blink_active(mediator.time_ms))
        mediator.purchased_num_paths = 2
        mediator.update_unlocked_num_paths()

        self.assertTrue(second_button.is_unlock_blink_active(mediator.time_ms))
        self.assertTrue(second_button.is_unlock_blink_visible(mediator.time_ms))
        self.assertFalse(second_button.is_unlock_blink_visible(mediator.time_ms + 200))
        self.assertFalse(
            second_button.is_unlock_blink_active(
                mediator.time_ms + unlock_blink_duration_ms
            )
        )

    def test_path_purchase_prices_are_incremental_from_milestones(self):
        mediator = Mediator()
        expected_prices = [
            path_unlock_milestones[idx] - path_unlock_milestones[idx - 1]
            for idx in range(1, len(path_unlock_milestones))
        ]
        self.assertEqual(mediator.path_purchase_prices, expected_prices)

    def test_try_purchase_path_button_unlocks_next_slot(self):
        mediator = Mediator()
        second_button = mediator.path_buttons[1]
        self.assertTrue(second_button.is_locked)
        self.assertEqual(mediator.unlocked_num_paths, 1)
        mediator.deliveries = 125

        mediator.line_credits = mediator.path_purchase_prices[0]
        purchased = mediator.try_purchase_path_button(second_button)

        self.assertTrue(purchased)
        self.assertEqual(mediator.unlocked_num_paths, 2)
        self.assertFalse(second_button.is_locked)
        self.assertEqual(mediator.deliveries, 125)
        self.assertEqual(mediator.total_travels_handled, 125)
        self.assertEqual(mediator.line_credits, 0)
        self.assertEqual(mediator.score, 0)

    def test_try_purchase_path_button_requires_enough_score(self):
        mediator = Mediator()
        second_button = mediator.path_buttons[1]
        mediator.score = mediator.path_purchase_prices[0] - 1

        purchased = mediator.try_purchase_path_button(second_button)

        self.assertFalse(purchased)
        self.assertTrue(second_button.is_locked)
        self.assertEqual(mediator.unlocked_num_paths, 1)
        self.assertEqual(mediator.score, mediator.path_purchase_prices[0] - 1)

    def test_path_unlock_no_longer_follows_total_travels(self):
        mediator = Mediator()
        mediator.total_travels_handled = 650
        mediator.update_unlocked_num_paths()
        self.assertEqual(mediator.unlocked_num_paths, 1)

    def test_initial_station_unlock_state(self):
        mediator = Mediator()
        self.assertEqual(mediator.unlocked_num_stations, initial_num_stations)
        self.assertEqual(len(mediator.stations), initial_num_stations)

    def test_station_unlock_progression_uses_travel_thresholds(self):
        mediator = Mediator()
        self.assertEqual(station_unlock_milestones[:5], [10, 40, 90, 160, 250])

        mediator.total_travels_handled = 9
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, 3)
        self.assertEqual(len(mediator.stations), 3)

        mediator.total_travels_handled = 10
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, 4)
        self.assertEqual(len(mediator.stations), 4)

        mediator.total_travels_handled = 40
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, 5)
        self.assertEqual(len(mediator.stations), 5)

        mediator.total_travels_handled = station_unlock_milestones[-1]
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, num_stations)
        self.assertEqual(len(mediator.stations), num_stations)

    def test_station_unlock_starts_new_station_blink(self):
        mediator = Mediator()
        first_new_station = mediator.all_stations[initial_num_stations]
        initial_station = mediator.stations[0]

        self.assertFalse(initial_station.is_unlock_blink_active(mediator.time_ms))
        self.assertFalse(first_new_station.is_unlock_blink_active(mediator.time_ms))

        mediator.total_travels_handled = station_unlock_milestones[0]
        mediator.update_unlocked_num_stations()

        self.assertIn(first_new_station, mediator.stations)
        self.assertTrue(first_new_station.is_unlock_blink_active(mediator.time_ms))
        self.assertTrue(first_new_station.is_unlock_blink_visible(mediator.time_ms))
        self.assertFalse(
            first_new_station.is_unlock_blink_visible(mediator.time_ms + 200)
        )
        self.assertFalse(
            first_new_station.is_unlock_blink_active(
                mediator.time_ms + unlock_blink_duration_ms
            )
        )
