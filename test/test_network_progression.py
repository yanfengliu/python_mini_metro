import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from progression import NetworkProgression


def make_progression() -> NetworkProgression:
    return NetworkProgression(
        num_paths=4,
        path_unlock_milestones=[650, 0, 300, 90],
        num_stations=8,
        initial_num_stations=3,
        station_unlock_milestones=[90, 10, 40, 160, 250],
    )


class TestNetworkProgression(unittest.TestCase):
    def test_initializes_sorted_rule_copies_prices_and_cached_counts(self):
        path_milestones = [650, 0, 300, 90]
        station_milestones = [90, 10, 40, 160, 250]

        progression = NetworkProgression(
            num_paths=4,
            path_unlock_milestones=path_milestones,
            num_stations=8,
            initial_num_stations=3,
            station_unlock_milestones=station_milestones,
        )

        self.assertEqual(progression.path_unlock_milestones, [0, 90, 300, 650])
        self.assertEqual(progression.path_purchase_prices, [90, 210, 350])
        self.assertEqual(progression.station_unlock_milestones, [10, 40, 90, 160, 250])
        self.assertIsNot(progression.path_unlock_milestones, path_milestones)
        self.assertIsNot(progression.station_unlock_milestones, station_milestones)
        self.assertEqual(progression.deliveries, 0)
        self.assertEqual(progression.line_credits, 0)
        self.assertEqual(progression.purchased_num_paths, 1)
        self.assertEqual(progression.unlocked_num_paths, 1)
        self.assertEqual(progression.unlocked_num_stations, 3)

    def test_delivery_awards_both_counters_without_eager_unlock_updates(self):
        progression = make_progression()
        progression.deliveries = 9
        progression.line_credits = 4

        progression.record_delivery()

        self.assertEqual(progression.deliveries, 10)
        self.assertEqual(progression.line_credits, 5)
        self.assertEqual(progression.unlocked_num_stations, 3)
        self.assertEqual(progression.unlocked_num_paths, 1)

    def test_station_unlock_count_uses_deliveries_and_clamps_to_limit(self):
        progression = make_progression()

        progression.deliveries = 9
        self.assertEqual(progression.get_unlocked_num_stations(), 3)
        progression.deliveries = 10
        self.assertEqual(progression.get_unlocked_num_stations(), 4)
        progression.deliveries = 90
        self.assertEqual(progression.get_unlocked_num_stations(), 6)
        progression.deliveries = 10_000
        self.assertEqual(progression.get_unlocked_num_stations(), 8)

    def test_path_unlock_count_uses_purchases_not_deliveries(self):
        progression = make_progression()
        progression.deliveries = 10_000

        self.assertEqual(progression.get_unlocked_num_paths(), 1)
        progression.purchased_num_paths = 0
        self.assertEqual(progression.get_unlocked_num_paths(), 1)
        progression.purchased_num_paths = 3
        self.assertEqual(progression.get_unlocked_num_paths(), 3)
        progression.purchased_num_paths = 10
        self.assertEqual(progression.get_unlocked_num_paths(), 4)

    def test_cached_unlock_transition_requires_an_explicit_target(self):
        progression = make_progression()
        progression.deliveries = 40
        progression.purchased_num_paths = 3

        station_change = progression.set_unlocked_num_stations(
            progression.get_unlocked_num_stations()
        )
        path_change = progression.set_unlocked_num_paths(
            progression.get_unlocked_num_paths()
        )

        self.assertEqual(station_change, (3, 5))
        self.assertEqual(path_change, (1, 3))
        self.assertEqual(progression.unlocked_num_stations, 5)
        self.assertEqual(progression.unlocked_num_paths, 3)

    def test_purchase_queries_are_sequential_and_validate_indices(self):
        progression = make_progression()
        progression.line_credits = 90

        self.assertEqual(progression.get_next_path_button_idx_to_purchase(), 1)
        self.assertIsNone(progression.get_purchase_price_for_path_button_idx(-1))
        self.assertIsNone(progression.get_purchase_price_for_path_button_idx(0))
        self.assertEqual(progression.get_purchase_price_for_path_button_idx(1), 90)
        self.assertIsNone(progression.get_purchase_price_for_path_button_idx(4))
        self.assertTrue(progression.can_purchase_path_button_idx(1))
        self.assertFalse(progression.can_purchase_path_button_idx(2))

        progression.line_credits = 89
        self.assertFalse(progression.can_purchase_path_button_idx(1))

    def test_record_path_purchase_spends_only_credits_and_leaves_cache_stale(self):
        progression = make_progression()
        progression.deliveries = 125
        progression.line_credits = 90

        progression.record_path_purchase(90)

        self.assertEqual(progression.deliveries, 125)
        self.assertEqual(progression.line_credits, 0)
        self.assertEqual(progression.purchased_num_paths, 2)
        self.assertEqual(progression.unlocked_num_paths, 1)

    def test_one_path_configuration_has_no_purchase_price(self):
        progression = NetworkProgression(
            num_paths=1,
            path_unlock_milestones=[0],
            num_stations=3,
            initial_num_stations=3,
            station_unlock_milestones=[],
        )

        self.assertEqual(progression.path_purchase_prices, [])
        self.assertIsNone(progression.get_next_path_button_idx_to_purchase())
        self.assertIsNone(progression.get_purchase_price_for_path_button_idx(1))


if __name__ == "__main__":
    unittest.main()
