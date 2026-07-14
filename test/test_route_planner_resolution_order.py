import sys
import unittest
from pathlib import Path

from test import route_planner_test_support as support

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# isort: split

from route_planner import RoutePlanner


class TestRoutePlannerResolutionOrder(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RoutePlanner()
        self.start = support.station("start")
        self.destination = support.station("destination", "triangle")
        self.start_node = support.node(self.start)
        self.destination_node = support.node(self.destination)
        self.node_map = {
            self.start: self.start_node,
            self.destination: self.destination_node,
        }

    def test_reducer_is_resolved_before_copying_the_raw_node_path(self) -> None:
        events: list[str] = []

        def old_reducer(nodes):
            events.append("old-reducer")
            return nodes

        def new_reducer(nodes):
            events.append("new-reducer")
            return nodes

        reducers = [old_reducer]

        class RebindingRawPath(list[object]):
            def __iter__(self):
                events.append("copy")
                reducers[0] = new_reducer
                return super().__iter__()

        raw_path = RebindingRawPath(
            [
                self.start_node,
                support.node(support.station("middle")),
                self.destination_node,
            ]
        )
        result = self.planner.find_best_node_path(
            self.start,
            [self.destination],
            self.node_map,
            find_node_path=lambda _start, _end: raw_path,
            get_reduce_node_path=lambda: reducers[0],
        )

        self.assertIsNotNone(result)
        self.assertEqual(events, ["copy", "old-reducer"])

    def test_shared_path_is_resolved_before_indexing_the_reduced_path(self) -> None:
        events: list[str] = []
        allowed_path = support.path("required", self.start, self.destination)

        def old_shared(_start, _end):
            events.append("old-shared")
            return allowed_path

        def new_shared(_start, _end):
            events.append("new-shared")
            return allowed_path

        shared_resolvers = [old_shared]

        class RebindingReducedPath(list[object]):
            def __getitem__(self, key):
                if key == 1:
                    events.append("index")
                    shared_resolvers[0] = new_shared
                return super().__getitem__(key)

        reduced = RebindingReducedPath([self.start_node, self.destination_node])
        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [self.destination],
            self.node_map,
            get_required_first_path_id=lambda: "required",
            find_node_path=lambda start, end: [start, end],
            get_reduce_node_path=lambda: lambda _nodes: reduced,
            get_find_shared_path=lambda: shared_resolvers[0],
            get_plan_factory=lambda: support.FakeTravelPlan,
        )

        self.assertIsNotNone(result)
        self.assertEqual(events, ["index", "old-shared", "new-shared"])

    def test_plan_factory_is_resolved_before_slicing_the_selected_path(self) -> None:
        events: list[str] = []
        allowed_path = support.path("required", self.start, self.destination)

        def old_factory(nodes):
            events.append("old-factory")
            return support.FakeTravelPlan(nodes)

        def new_factory(nodes):
            events.append("new-factory")
            return support.FakeTravelPlan(nodes)

        factories = [old_factory]

        class RebindingReducedPath(list[object]):
            def __getitem__(self, key):
                if isinstance(key, slice):
                    events.append("slice")
                    factories[0] = new_factory
                return super().__getitem__(key)

        reduced = RebindingReducedPath([self.start_node, self.destination_node])
        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [self.destination],
            self.node_map,
            get_required_first_path_id=lambda: "required",
            find_node_path=lambda start, end: [start, end],
            get_reduce_node_path=lambda: lambda _nodes: reduced,
            get_find_shared_path=lambda: lambda _start, _end: allowed_path,
            get_plan_factory=lambda: factories[0],
        )

        self.assertIsNotNone(result)
        self.assertEqual(events, ["slice", "old-factory"])

    def test_reducer_callable_is_released_before_candidate_cost(self) -> None:
        events: list[str] = []

        class ReducedPath(list[object]):
            def __len__(self):
                events.append("cost")
                return super().__len__()

        reduced = ReducedPath([self.start_node, self.destination_node])

        class Reducer:
            def __call__(self, _nodes):
                events.append("call")
                return reduced

            def __del__(self):
                events.append("released")

        result = self.planner.find_best_node_path(
            self.start,
            [self.destination],
            self.node_map,
            find_node_path=lambda start, end: [start, end],
            get_reduce_node_path=lambda: Reducer(),
        )

        self.assertIs(result, reduced)
        self.assertEqual(events, ["call", "released", "cost"])

    def test_shared_callables_are_released_before_later_plan_reads(self) -> None:
        events: list[str] = []
        allowed_path = support.path("required", self.start, self.destination)
        labels = iter(["qualify", "wire"])

        class SharedPath:
            def __init__(self) -> None:
                self.label = next(labels)

            def __call__(self, _start, _end):
                events.append(f"{self.label}-call")
                return allowed_path

            def __del__(self):
                events.append(f"{self.label}-released")

        def required_path_id():
            events.append("required")
            return "required"

        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [self.destination],
            self.node_map,
            get_required_first_path_id=required_path_id,
            find_node_path=lambda start, end: [start, end],
            get_reduce_node_path=lambda: lambda nodes: nodes,
            get_find_shared_path=lambda: SharedPath(),
            get_plan_factory=lambda: support.FakeTravelPlan,
        )

        self.assertIsNotNone(result)
        self.assertEqual(
            events,
            [
                "qualify-call",
                "qualify-released",
                "required",
                "wire-call",
                "wire-released",
            ],
        )

    def test_plan_factory_is_released_before_plan_method_lookup(self) -> None:
        events: list[str] = []
        allowed_path = support.path("required", self.start, self.destination)

        class ObservingPlan(support.FakeTravelPlan):
            def get_next_station(self):
                events.append("next")
                return super().get_next_station()

        class Factory:
            def __call__(self, nodes):
                events.append("factory-call")
                return ObservingPlan(nodes)

            def __del__(self):
                events.append("factory-released")

        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [self.destination],
            self.node_map,
            get_required_first_path_id=lambda: "required",
            find_node_path=lambda start, end: [start, end],
            get_reduce_node_path=lambda: lambda nodes: nodes,
            get_find_shared_path=lambda: lambda _start, _end: allowed_path,
            get_plan_factory=lambda: Factory(),
        )

        self.assertIsNotNone(result)
        self.assertEqual(events, ["factory-call", "factory-released", "next"])


if __name__ == "__main__":
    unittest.main()
