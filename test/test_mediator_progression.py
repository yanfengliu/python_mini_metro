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
    def test_constructor_uses_public_progression_queries_for_cached_state(self):
        class CustomizedMediator(Mediator):
            def get_path_purchase_prices(self):
                return [5, 6, 7]

            def get_unlocked_num_paths(self):
                return 2

            def get_unlocked_num_stations(self):
                return self.initial_num_stations + 1

        mediator = CustomizedMediator(seed=3)

        self.assertEqual(mediator.path_purchase_prices, [5, 6, 7])
        self.assertEqual(mediator.unlocked_num_paths, 2)
        self.assertEqual(
            mediator.unlocked_num_stations, mediator.initial_num_stations + 1
        )

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

    def test_progression_lists_remain_live_and_cache_updates_are_explicit(self):
        mediator = Mediator(seed=5)
        original_prices = mediator.path_purchase_prices
        replacement_path_milestones = [0, 5, 15, 30]
        replacement_station_milestones = [2, 4, 6]

        mediator.path_unlock_milestones = replacement_path_milestones
        mediator.station_unlock_milestones = replacement_station_milestones
        mediator.deliveries = 6
        mediator.purchased_num_paths = 3

        self.assertIs(mediator.path_unlock_milestones, replacement_path_milestones)
        self.assertIs(
            mediator.station_unlock_milestones, replacement_station_milestones
        )
        self.assertIs(mediator.path_purchase_prices, original_prices)
        self.assertEqual(mediator.get_path_purchase_prices(), [5, 10, 15])
        self.assertEqual(mediator.unlocked_num_paths, 1)
        self.assertEqual(mediator.unlocked_num_stations, initial_num_stations)

        replacement_prices = [1, 2, 3]
        mediator.path_purchase_prices = replacement_prices
        self.assertIs(mediator.path_purchase_prices, replacement_prices)

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

    def test_multi_path_jump_blinks_new_slots_and_every_update_refreshes_locks(self):
        mediator = Mediator(seed=7)
        mediator.time_ms = 1_234
        mediator.purchased_num_paths = 3

        mediator.update_unlocked_num_paths()

        self.assertEqual(mediator.unlocked_num_paths, 3)
        self.assertEqual(
            [button.unlock_blink_start_time_ms for button in mediator.path_buttons],
            [None, 1_234, 1_234, None],
        )
        mediator.path_buttons[1].set_locked(True)
        mediator.update_unlocked_num_paths()
        self.assertFalse(mediator.path_buttons[1].is_locked)

        mediator.purchased_num_paths = 1
        mediator.update_unlocked_num_paths()
        self.assertEqual(mediator.unlocked_num_paths, 1)
        self.assertTrue(mediator.path_buttons[1].is_locked)
        self.assertTrue(mediator.path_buttons[2].is_locked)
        self.assertEqual(mediator.path_buttons[1].unlock_blink_start_time_ms, 1_234)

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

    def test_purchase_affordability_uses_public_query_overrides(self):
        mediator = Mediator(seed=10)
        mediator.line_credits = 90
        mediator.get_purchase_price_for_path_button_idx = lambda _: 999

        self.assertFalse(mediator.can_purchase_path_button_idx(1))
        self.assertFalse(mediator.try_purchase_path_button(mediator.path_buttons[1]))
        self.assertEqual(mediator.line_credits, 90)

        mediator.line_credits = 0
        mediator.get_purchase_price_for_path_button_idx = lambda _: 0

        self.assertTrue(mediator.can_purchase_path_button_idx(1))

        mediator.get_next_path_button_idx_to_purchase = lambda: 2
        self.assertFalse(mediator.can_purchase_path_button_idx(1))
        self.assertTrue(mediator.can_purchase_path_button_idx(2))

    def test_purchase_affordability_short_circuits_before_price_query(self):
        mediator = Mediator(seed=11)
        price_queries = []

        def unexpected_price_query(button_idx):
            price_queries.append(button_idx)
            raise AssertionError("price must not be queried for a non-next line")

        mediator.get_purchase_price_for_path_button_idx = unexpected_price_query

        self.assertFalse(mediator.can_purchase_path_button_idx(2))
        self.assertEqual(price_queries, [])

        mediator.purchased_num_paths = mediator.num_paths
        mediator.update_unlocked_num_paths()
        self.assertFalse(mediator.can_purchase_path_button_idx(1))
        self.assertEqual(price_queries, [])

    def test_invalid_or_foreign_path_purchases_do_not_mutate_progression(self):
        mediator = Mediator(seed=11)
        mediator.line_credits = 10_000
        foreign_button = Mediator(seed=12).path_buttons[1]
        before = (
            mediator.deliveries,
            mediator.line_credits,
            mediator.purchased_num_paths,
            mediator.unlocked_num_paths,
            [button.is_locked for button in mediator.path_buttons],
        )

        self.assertFalse(mediator.try_purchase_path_button(mediator.path_buttons[0]))
        self.assertFalse(mediator.try_purchase_path_button(foreign_button))
        self.assertFalse(mediator.try_purchase_path_button_by_index(-1))
        self.assertFalse(
            mediator.try_purchase_path_button_by_index(len(mediator.path_buttons))
        )
        self.assertFalse(mediator.try_purchase_path_button_by_index(2))

        after = (
            mediator.deliveries,
            mediator.line_credits,
            mediator.purchased_num_paths,
            mediator.unlocked_num_paths,
            [button.is_locked for button in mediator.path_buttons],
        )
        self.assertEqual(after, before)

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

    def test_multi_station_jump_preserves_pool_identity_rng_and_rewind_semantics(self):
        mediator = Mediator(seed=13)
        python_rng_state = mediator.context.python_random.getstate()
        numpy_rng_state = repr(mediator.context.numpy_random.bit_generator.state)
        spawn_intervals = dict(mediator.station_spawn_interval_steps)
        mediator.time_ms = 2_468
        mediator.deliveries = station_unlock_milestones[2]

        mediator.update_unlocked_num_stations()

        expected_count = initial_num_stations + 3
        self.assertEqual(mediator.unlocked_num_stations, expected_count)
        self.assertEqual(len(mediator.stations), expected_count)
        for index, station in enumerate(mediator.stations):
            self.assertIs(station, mediator.all_stations[index])
        self.assertEqual(
            [
                station.unlock_blink_start_time_ms
                for station in mediator.stations[initial_num_stations:]
            ],
            [2_468, 2_468, 2_468],
        )
        self.assertEqual(mediator.context.python_random.getstate(), python_rng_state)
        self.assertEqual(
            repr(mediator.context.numpy_random.bit_generator.state), numpy_rng_state
        )
        self.assertEqual(mediator.station_spawn_interval_steps, spawn_intervals)

        active_stations = mediator.stations
        mediator.deliveries = 0
        mediator.update_unlocked_num_stations()
        self.assertEqual(mediator.unlocked_num_stations, initial_num_stations)
        self.assertIs(mediator.stations, active_stations)
        self.assertEqual(len(mediator.stations), expected_count)

    def test_station_update_repairs_short_prefix_without_replaying_blinks(self):
        mediator = Mediator(seed=17)
        mediator.stations = mediator.all_stations[:1]

        mediator.update_unlocked_num_stations()

        self.assertEqual(
            mediator.stations, mediator.all_stations[:initial_num_stations]
        )
        self.assertTrue(
            all(
                station.unlock_blink_start_time_ms is None
                for station in mediator.stations
            )
        )
