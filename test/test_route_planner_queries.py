import os
import subprocess
import sys
import unittest
from pathlib import Path

from test.route_planner_test_support import (
    FakePath,
    FakeTravelPlan,
    LoggingMapping,
    node,
    path,
    station,
)

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from route_planner import RoutePlanner


class TestRoutePlannerQueries(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RoutePlanner()

    def test_station_filter_preserves_order_returns_new_list_and_reads_live_input(self):
        first_circle = station("first-circle")
        triangle = station("triangle", "triangle")
        second_circle = station("second-circle")
        stations = [first_circle, triangle, second_circle]

        first_result = self.planner.get_stations_for_shape_type(stations, "circle")

        self.assertIsNot(first_result, stations)
        self.assertEqual(len(first_result), 2)
        self.assertIs(first_result[0], first_circle)
        self.assertIs(first_result[1], second_circle)

        third_circle = station("third-circle")
        stations.remove(first_circle)
        stations.append(third_circle)
        second_result = self.planner.get_stations_for_shape_type(stations, "circle")

        self.assertEqual(len(first_result), 2)
        self.assertEqual(len(second_result), 2)
        self.assertIs(second_result[0], second_circle)
        self.assertIs(second_result[1], third_circle)

    def test_shared_path_returns_first_exact_object_and_observes_reordering(self):
        station_a = station("a")
        station_b = station("b")
        first_path = path("first", station_a, station_b)
        second_path = path("second", station_a, station_b)
        paths = [first_path, second_path]

        self.assertIs(
            self.planner.find_shared_path(paths, station_a, station_b), first_path
        )

        paths.reverse()
        self.assertIs(
            self.planner.find_shared_path(paths, station_a, station_b), second_path
        )
        self.assertIsNone(
            self.planner.find_shared_path(paths, station_a, station("missing"))
        )

    def test_cached_plan_is_eligible_only_when_next_path_is_present(self):
        passenger = object()
        travel_plans: LoggingMapping[object, FakeTravelPlan] = LoggingMapping({})

        self.assertFalse(
            self.planner.passenger_has_travel_plan(
                contains_travel_plan=lambda: passenger in travel_plans,
                get_travel_plan=lambda: travel_plans[passenger],
            )
        )
        self.assertEqual(travel_plans.accesses, [])

        cached_plan = FakeTravelPlan([])
        travel_plans[passenger] = cached_plan
        self.assertFalse(
            self.planner.passenger_has_travel_plan(
                contains_travel_plan=lambda: passenger in travel_plans,
                get_travel_plan=lambda: travel_plans[passenger],
            )
        )
        self.assertEqual(travel_plans.accesses, [passenger])

        cached_plan.next_path = FakePath("active", [])
        self.assertTrue(
            self.planner.passenger_has_travel_plan(
                contains_travel_plan=lambda: passenger in travel_plans,
                get_travel_plan=lambda: travel_plans[passenger],
            )
        )
        self.assertEqual(travel_plans.accesses, [passenger, passenger])

    def test_cached_plan_resolvers_observe_mapping_rebind_between_reads(self):
        passenger = object()
        old_plan = FakeTravelPlan([])
        active_plan = FakeTravelPlan([])
        active_plan.next_path = FakePath("active", [])
        old_plans = {passenger: old_plan}
        active_plans = [{passenger: active_plan}]

        def contains_travel_plan():
            active_plans[0] = {passenger: active_plan}
            return passenger in old_plans

        self.assertTrue(
            self.planner.passenger_has_travel_plan(
                contains_travel_plan=contains_travel_plan,
                get_travel_plan=lambda: active_plans[0][passenger],
            )
        )

    def test_path_id_lookup_returns_first_exact_object_and_reads_live_input(self):
        station_a = station("a")
        first_match = path("shared-id", station_a)
        second_match = path("shared-id", station_a)
        paths = [first_match, second_match]

        self.assertIs(self.planner.get_path_by_id(paths, "shared-id"), first_match)
        self.assertIsNone(self.planner.get_path_by_id(paths, "missing"))

        paths.remove(first_match)
        self.assertIs(self.planner.get_path_by_id(paths, "shared-id"), second_match)

    def test_compression_mutates_exact_list_and_retains_node_and_path_set_identity(
        self,
    ):
        station_a = station("a")
        station_b = station("b")
        station_c = station("c")
        shared_path = path("shared", station_a, station_b, station_c)
        start_node = node(station_a, shared_path)
        middle_node = node(station_b, shared_path)
        end_node = node(station_c, shared_path)
        start_paths = start_node.paths
        middle_paths = middle_node.paths
        end_paths = end_node.paths
        node_path = [start_node, middle_node, end_node]

        result = self.planner.skip_stations_on_same_path(node_path)

        self.assertIs(result, node_path)
        self.assertEqual(len(result), 2)
        self.assertIs(result[0], start_node)
        self.assertIs(result[1], end_node)
        self.assertIs(start_node.paths, start_paths)
        self.assertIs(middle_node.paths, middle_paths)
        self.assertIs(end_node.paths, end_paths)
        self.assertIs(next(iter(start_node.paths)), shared_path)
        self.assertIs(next(iter(middle_node.paths)), shared_path)
        self.assertIs(next(iter(end_node.paths)), shared_path)

    def test_isolated_import_does_not_load_pygame_or_domain_modules(self):
        repo_root = Path(__file__).resolve().parents[1]
        source_root = repo_root / "src"
        blocked_roots = ("pygame", "mediator", "travel_plan", "entity", "graph")
        script = f"""
import sys
import route_planner

blocked_roots = {blocked_roots!r}
loaded = sorted(
    name
    for name in sys.modules
    if any(name == root or name.startswith(f"{{root}}.") for root in blocked_roots)
)
if loaded:
    raise AssertionError(loaded)
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(source_root), environment.get("PYTHONPATH")])
        )

        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
