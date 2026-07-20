from __future__ import annotations

import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from path_redraw import PathRedrawGesture


class _EqualStation:
    def __init__(self, name: str) -> None:
        self.name = name
        self.position = (name, "position")

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _EqualStation)

    __hash__ = None


class TestPathRedrawGesture(unittest.TestCase):
    def setUp(self) -> None:
        self.path = object()
        self.a = _EqualStation("a")
        self.b = _EqualStation("b")
        self.c = _EqualStation("c")
        self.d = _EqualStation("d")

    def test_linear_unique_order_and_consecutive_identity_repeat(self) -> None:
        empty = PathRedrawGesture(self.path)
        first = empty.enter_station(self.a, (1, 2))
        repeated = first.enter_station(self.a, (3, 4))
        linear = repeated.enter_station(self.b, (5, 6))

        self.assertEqual(empty.stations, ())
        self.assertEqual(first.stations, (self.a,))
        self.assertEqual(repeated.stations, (self.a,))
        self.assertEqual(repeated.temp_point, self.a.position)
        self.assertEqual(linear.stations, (self.a, self.b))
        self.assertFalse(linear.loop)
        self.assertFalse(linear.invalid)

    def test_station_capture_snaps_to_position_with_pointer_fallback(self) -> None:
        positioned = PathRedrawGesture(self.path).enter_station(self.a, (9, 10))
        station_double = object()
        fallback = positioned.enter_station(station_double, (11, 12))

        self.assertEqual(positioned.temp_point, self.a.position)
        self.assertEqual(fallback.temp_point, (11, 12))
        self.assertEqual(fallback.move_to((13, 14)).temp_point, (13, 14))

    def test_first_station_closes_loop_and_new_unique_reopens(self) -> None:
        linear = (
            PathRedrawGesture(self.path).enter_station(self.a).enter_station(self.b)
        )
        loop = linear.enter_station(self.a)
        reopened = loop.move_to((10, 11)).enter_station(self.c)

        self.assertTrue(loop.loop)
        self.assertEqual(loop.stations, (self.a, self.b))
        self.assertFalse(reopened.loop)
        self.assertEqual(reopened.stations, (self.a, self.b, self.c))

    def test_nonfirst_duplicate_invalidates_without_reordering(self) -> None:
        linear = (
            PathRedrawGesture(self.path)
            .enter_station(self.a)
            .enter_station(self.b)
            .enter_station(self.c)
        )
        invalid = linear.enter_station(self.b)
        still_invalid = invalid.enter_station(self.d)

        self.assertTrue(invalid.invalid)
        self.assertEqual(invalid.stations, linear.stations)
        self.assertTrue(still_invalid.invalid)
        self.assertEqual(still_invalid.stations, linear.stations)

    def test_active_station_resolution_is_identity_only_and_fail_closed(self) -> None:
        gesture = (
            PathRedrawGesture(self.path).enter_station(self.a).enter_station(self.b)
        )

        self.assertEqual(gesture.station_indices([self.c, self.a, self.b]), [1, 2])
        self.assertIsNone(gesture.station_indices([self.c, self.d]))
        self.assertIsNone(gesture.station_indices([self.a, self.a, self.b]))

    def test_updates_do_not_mutate_supplied_path_stations_or_prior_values(self) -> None:
        path_state = {"stations": [self.a, self.b]}
        station_state = [self.a.name, self.b.name]
        initial = PathRedrawGesture(path_state)

        moved = initial.move_to((20, 30))
        updated = moved.enter_station(self.a).enter_station(self.b)

        self.assertEqual(path_state, {"stations": [self.a, self.b]})
        self.assertEqual([self.a.name, self.b.name], station_state)
        self.assertIs(updated.path, path_state)
        self.assertIsNone(initial.temp_point)
        self.assertEqual(initial.stations, ())


if __name__ == "__main__":
    unittest.main()
