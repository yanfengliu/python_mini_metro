import sys
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock

from test import route_planner_test_support as support

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# isort: split

from route_planner import RoutePlanner


def _node_path(start_node, end_node, length: int, label: str):
    middle = [
        support.node(support.station(f"{label}-{index}")) for index in range(length - 2)
    ]
    return [start_node, *middle, end_node]


class _SelectionTestCase(TestCase):
    def setUp(self) -> None:
        self.planner = RoutePlanner()
        self.start = support.station("start")
        self.first_destination = support.station("first", "triangle")
        self.second_destination = support.station("second", "triangle")
        self.start_node = support.node(self.start)
        self.first_node = support.node(self.first_destination)
        self.second_node = support.node(self.second_destination)

    def ranking_fixture(self, name: str, costs: list[tuple[int, int]]):
        destinations = [
            support.station(f"{name}-first", "triangle"),
            support.station(f"{name}-second", "triangle"),
        ]
        destination_nodes = [support.node(value) for value in destinations]
        raw_paths = [
            _node_path(self.start_node, end, cost[0], f"{name}-raw-{index}")
            for index, (end, cost) in enumerate(zip(destination_nodes, costs))
        ]
        reduced_paths = [
            _node_path(self.start_node, end, cost[1], f"{name}-reduced-{index}")
            for index, (end, cost) in enumerate(zip(destination_nodes, costs))
        ]
        node_map = {self.start: self.start_node} | dict(
            zip(destinations, destination_nodes)
        )
        return destinations, destination_nodes, raw_paths, reduced_paths, node_map


class TestFindBestNodePath(_SelectionTestCase):
    def test_unreachable_lookup_order_includes_empty_destination_case(self) -> None:
        node_map = support.LoggingMapping(
            {
                self.start: self.start_node,
                self.first_destination: self.first_node,
                self.second_destination: self.second_node,
            }
        )
        find_node_path = Mock(return_value=[])
        reduce_node_path = Mock(side_effect=AssertionError("must not reduce"))

        empty_result = self.planner.find_best_node_path(
            self.start,
            [],
            node_map,
            find_node_path=find_node_path,
            get_reduce_node_path=lambda: reduce_node_path,
        )
        self.assertIsNone(empty_result)
        self.assertEqual(node_map.accesses, [])

        result = self.planner.find_best_node_path(
            self.start,
            [self.first_destination, self.second_destination],
            node_map,
            find_node_path=find_node_path,
            get_reduce_node_path=lambda: reduce_node_path,
        )

        self.assertIsNone(result)
        self.assertEqual(
            node_map.accesses,
            [
                self.start,
                self.first_destination,
                self.start,
                self.second_destination,
            ],
        )

    def test_one_node_arrival_is_exact_and_overrides_an_earlier_route(self) -> None:
        third_destination = support.station("third", "triangle")
        third_node = support.node(third_destination)
        earlier_route = [self.start_node, self.first_node]
        arrival = [self.second_node]
        searches: list[object] = []

        def find_node_path(_start, end):
            searches.append(end)
            if end is self.first_node:
                return earlier_route
            if end is self.second_node:
                return arrival
            raise AssertionError("arrival must short-circuit later destinations")

        result = self.planner.find_best_node_path(
            self.start,
            [self.first_destination, self.second_destination, third_destination],
            {
                self.start: self.start_node,
                self.first_destination: self.first_node,
                self.second_destination: self.second_node,
                third_destination: third_node,
            },
            find_node_path=find_node_path,
            get_reduce_node_path=lambda: lambda _nodes: list(earlier_route),
        )

        self.assertIs(result, arrival)
        self.assertEqual(searches, [self.first_node, self.second_node])

    def test_ranking_uses_raw_then_reduced_cost_and_keeps_first_tie(self) -> None:
        cases = [
            ("raw", [(4, 2), (3, 3)], 1),
            ("reduced", [(3, 3), (3, 2)], 1),
            ("tie", [(3, 2), (3, 2)], 0),
        ]
        for name, costs, expected_index in cases:
            with self.subTest(name=name):
                destinations, nodes, raw, reduced, node_map = self.ranking_fixture(
                    name, costs
                )
                raw_by_end = dict(zip(nodes, raw))
                reduced_by_end = dict(zip(nodes, reduced))

                result = self.planner.find_best_node_path(
                    self.start,
                    destinations,
                    node_map,
                    find_node_path=lambda _start, end: raw_by_end[end],
                    get_reduce_node_path=lambda: lambda path: reduced_by_end[path[-1]],
                )

                self.assertIs(result, reduced[expected_index])

    def test_reducer_receives_a_copy_containing_the_exact_nodes(self) -> None:
        middle_node = support.node(support.station("middle"))
        raw = [self.start_node, middle_node, self.first_node]
        received: list[list[object]] = []

        def reduce_node_path(candidate):
            self.assertIsNot(candidate, raw)
            self.assertTrue(
                all(got is expected for got, expected in zip(candidate, raw))
            )
            received.append(candidate)
            candidate.pop(1)
            return candidate

        result = self.planner.find_best_node_path(
            self.start,
            [self.first_destination],
            {self.start: self.start_node, self.first_destination: self.first_node},
            find_node_path=lambda _start, _end: raw,
            get_reduce_node_path=lambda: reduce_node_path,
        )

        self.assertIs(result, received[0])
        self.assertEqual(raw, [self.start_node, middle_node, self.first_node])

    def test_resolver_thunks_observe_rebinding_between_destinations(self) -> None:
        events: list[str] = []
        first_reduced = [self.start_node, self.first_node]
        second_reduced = [self.start_node, self.second_node]

        def second_find(start_node, end_node):
            events.append("find-2")
            return [start_node, end_node]

        def first_find(start_node, end_node):
            events.append("find-1")
            finders[0] = second_find
            return [start_node, end_node]

        def second_reduce(_nodes):
            events.append("reduce-2")
            return second_reduced

        def first_reduce(_nodes):
            events.append("reduce-1")
            reducers[0] = second_reduce
            return first_reduced

        finders = [first_find]
        reducers = [first_reduce]
        result = self.planner.find_best_node_path(
            self.start,
            [self.first_destination, self.second_destination],
            {
                self.start: self.start_node,
                self.first_destination: self.first_node,
                self.second_destination: self.second_node,
            },
            find_node_path=lambda start, end: finders[0](start, end),
            get_reduce_node_path=lambda: reducers[0],
        )

        self.assertIs(result, first_reduced)
        self.assertEqual(events, ["find-1", "reduce-1", "find-2", "reduce-2"])


class TestRequiredFirstPathSelection(_SelectionTestCase):
    def test_start_lookup_is_once_then_each_destination_is_looked_up(self) -> None:
        node_map = support.LoggingMapping(
            {
                self.start: self.start_node,
                self.first_destination: self.first_node,
                self.second_destination: self.second_node,
            }
        )
        reduce_node_path = Mock(side_effect=AssertionError("must not reduce"))
        find_shared_path = Mock(side_effect=AssertionError("must not inspect paths"))
        make_plan = Mock(side_effect=AssertionError("must not make a plan"))

        empty_result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [],
            node_map,
            get_required_first_path_id=lambda: "required",
            find_node_path=Mock(side_effect=AssertionError("must not search")),
            get_reduce_node_path=lambda: reduce_node_path,
            get_find_shared_path=lambda: find_shared_path,
            get_plan_factory=lambda: make_plan,
        )
        self.assertIsNone(empty_result)
        self.assertEqual(node_map.accesses, [self.start])

        node_map.accesses.clear()
        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [self.first_destination, self.second_destination],
            node_map,
            get_required_first_path_id=lambda: "required",
            find_node_path=Mock(return_value=[]),
            get_reduce_node_path=lambda: reduce_node_path,
            get_find_shared_path=lambda: find_shared_path,
            get_plan_factory=lambda: make_plan,
        )

        self.assertIsNone(result)
        self.assertEqual(
            node_map.accesses,
            [self.start, self.first_destination, self.second_destination],
        )

    def test_rejects_short_reduced_missing_and_wrong_first_paths(self) -> None:
        destinations = [
            support.station("one", "triangle"),
            support.station("reduced-one", "triangle"),
            support.station("missing", "triangle"),
            support.station("wrong", "triangle"),
        ]
        nodes = [support.node(destination) for destination in destinations]
        raw_by_end = {nodes[0]: [nodes[0]]}
        raw_by_end.update({end: [self.start_node, end] for end in nodes[1:]})
        wrong_path = support.path("wrong", self.start, destinations[-1])
        shared_calls: list[object] = []

        def reduce_node_path(node_path):
            return [self.start_node] if node_path[-1] is nodes[1] else node_path

        def find_shared_path(_start, end):
            shared_calls.append(end)
            return wrong_path if end is destinations[-1] else None

        make_plan = Mock(side_effect=AssertionError("must not make a plan"))
        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            destinations,
            {self.start: self.start_node} | dict(zip(destinations, nodes)),
            get_required_first_path_id=lambda: "required",
            find_node_path=lambda _start, end: raw_by_end[end],
            get_reduce_node_path=lambda: reduce_node_path,
            get_find_shared_path=lambda: find_shared_path,
            get_plan_factory=lambda: make_plan,
        )

        self.assertIsNone(result)
        self.assertEqual(shared_calls, [destinations[2], destinations[3]])

    def test_required_ranking_uses_raw_reduced_and_first_tie_costs(self) -> None:
        cases = [
            ("raw", [(4, 2), (3, 3)], 1),
            ("reduced", [(3, 3), (3, 2)], 1),
            ("tie", [(3, 2), (3, 2)], 0),
        ]
        allowed_path = support.path("required", self.start)
        for name, costs, expected_index in cases:
            with self.subTest(name=name):
                destinations, nodes, raw, reduced, node_map = self.ranking_fixture(
                    name, costs
                )
                raw_by_end = dict(zip(nodes, raw))
                reduced_by_end = dict(zip(nodes, reduced))

                result = self.planner.get_travel_plan_starting_with_path(
                    self.start,
                    destinations,
                    node_map,
                    get_required_first_path_id=lambda: "required",
                    find_node_path=lambda _start, end: raw_by_end[end],
                    get_reduce_node_path=lambda: lambda path: reduced_by_end[path[-1]],
                    get_find_shared_path=lambda: lambda _start, _end: allowed_path,
                    get_plan_factory=lambda: support.FakeTravelPlan,
                )

                self.assertIsNotNone(result)
                assert result is not None
                expected = reduced[expected_index][1:]
                self.assertTrue(
                    all(
                        got is wanted for got, wanted in zip(result.node_path, expected)
                    )
                )

    def test_factory_once_wires_unowned_plan_with_fresh_shared_resolver(self) -> None:
        qualifying_path = support.path("required", self.start, self.first_destination)
        final_path = support.path("final", self.start, self.first_destination)
        reduced = [self.start_node, self.first_node]
        owned_plans: dict[str, support.FakeTravelPlan] = {}
        events: list[str] = []
        case = self

        class ObservingPlan(support.FakeTravelPlan):
            def get_next_station(self):
                events.append("next")
                case.assertFalse(any(self is plan for plan in owned_plans.values()))
                return super().get_next_station()

        def first_shared(_start, _end):
            events.append("qualify")
            shared_resolvers[0] = final_shared
            return qualifying_path

        def final_shared(_start, _end):
            events.append("wire")
            return final_path

        def make_plan(nodes):
            events.append("make")
            self.assertIsNot(nodes, reduced)
            self.assertEqual(nodes, [self.first_node])
            return ObservingPlan(nodes)

        shared_resolvers = [first_shared]
        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [self.first_destination],
            {self.start: self.start_node, self.first_destination: self.first_node},
            get_required_first_path_id=lambda: "required",
            find_node_path=lambda start, end: [start, end],
            get_reduce_node_path=lambda: lambda _nodes: reduced,
            get_find_shared_path=lambda: shared_resolvers[0],
            get_plan_factory=lambda: make_plan,
        )

        self.assertIsInstance(result, ObservingPlan)
        assert result is not None
        self.assertEqual(events, ["qualify", "make", "next", "wire"])
        self.assertIs(result.next_path, final_path)

    def test_required_path_id_is_resolved_after_the_shared_path_callback(self) -> None:
        shared_path = support.path("initial", self.start, self.first_destination)
        events: list[str] = []

        def find_shared_path(_start, _end):
            events.append("shared")
            shared_path.id = "rebound"
            return shared_path

        def get_required_first_path_id():
            events.append("required-id")
            return "rebound"

        result = self.planner.get_travel_plan_starting_with_path(
            self.start,
            [self.first_destination],
            {self.start: self.start_node, self.first_destination: self.first_node},
            get_required_first_path_id=get_required_first_path_id,
            find_node_path=lambda start, end: [start, end],
            get_reduce_node_path=lambda: lambda nodes: nodes,
            get_find_shared_path=lambda: find_shared_path,
            get_plan_factory=lambda: support.FakeTravelPlan,
        )

        self.assertIsNotNone(result)
        self.assertEqual(events, ["shared", "required-id", "shared"])


class TestUpdateNextPathForPlan(_SelectionTestCase):
    def test_fresh_plan_lookup_is_used_for_next_path_write(self) -> None:
        read_plan = support.FakeTravelPlan([support.node(self.first_destination)])
        write_plan = support.FakeTravelPlan([])
        next_path = support.path("line", self.start, self.first_destination)
        plans = iter([read_plan, write_plan])
        events: list[str] = []

        def get_plan():
            events.append("get")
            return next(plans)

        def find_shared_path(start, end):
            events.append("find")
            self.assertIs(start, self.start)
            self.assertIs(end, self.first_destination)
            return next_path

        result = self.planner.update_next_path_for_plan(
            self.start,
            get_plan=get_plan,
            find_shared_path=find_shared_path,
        )

        self.assertIsNone(result)
        self.assertEqual(events, ["get", "find", "get"])
        self.assertIsNone(read_plan.next_path)
        self.assertIs(write_plan.next_path, next_path)

    def test_missing_path_re_resolves_plan_for_each_field_write(self) -> None:
        read_plan = support.FakeTravelPlan([support.node(self.first_destination)])
        path_plan = support.FakeTravelPlan([])
        station_plan = support.FakeTravelPlan([])
        old_path = support.path("old", self.start)
        old_station = support.station("old-next")
        path_plan.next_path = old_path
        path_plan.next_station = old_station
        station_plan.next_path = old_path
        station_plan.next_station = old_station
        plans = iter([read_plan, path_plan, station_plan])
        events: list[str] = []

        def get_plan():
            events.append("get")
            return next(plans)

        def find_shared_path(_start, _end):
            events.append("find")
            return None

        self.planner.update_next_path_for_plan(
            self.start,
            get_plan=get_plan,
            find_shared_path=find_shared_path,
        )

        self.assertEqual(events, ["get", "find", "get", "get"])
        self.assertIsNone(path_plan.next_path)
        self.assertIs(path_plan.next_station, old_station)
        self.assertIs(station_plan.next_path, old_path)
        self.assertIsNone(station_plan.next_station)
