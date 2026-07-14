from __future__ import annotations

import sys
import unittest
from pathlib import Path

from test.route_planner_test_support import (
    FakePassenger,
    FakeTravelPlan,
    LoggingMapping,
    node,
    path,
    station,
)

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# isort: split

from route_planner import RoutePlanner


class TestBoardingCandidateIterator(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RoutePlanner()

    def test_is_lazy_reuses_matching_plan_and_computes_an_exact_plan_once(self) -> None:
        matching_passenger = FakePassenger("matching", "triangle")
        proposed_passenger = FakePassenger("proposed", "triangle")
        passengers = [matching_passenger, proposed_passenger]
        matching_plan = FakeTravelPlan([])
        matching_plan.next_path = path("red")
        proposed_plan = FakeTravelPlan([])
        plans = {matching_passenger: matching_plan}
        calls: list[tuple[str, FakePassenger]] = []

        def get_current_plan(passenger: FakePassenger) -> FakeTravelPlan | None:
            calls.append(("current", passenger))
            return plans.get(passenger)

        def get_constrained_plan(passenger: FakePassenger) -> FakeTravelPlan | None:
            calls.append(("constrained", passenger))
            return proposed_plan

        candidates = self.planner.iter_boarding_candidates(
            passengers,
            get_required_path_id=lambda: "red",
            get_current_plan=get_current_plan,
            get_constrained_plan=get_constrained_plan,
        )

        self.assertEqual(calls, [])
        first_passenger, first_plan = next(candidates)
        self.assertIs(first_passenger, matching_passenger)
        self.assertIsNone(first_plan)
        self.assertEqual(calls, [("current", matching_passenger)])

        second_passenger, second_plan = next(candidates)
        self.assertIs(second_passenger, proposed_passenger)
        self.assertIs(second_plan, proposed_plan)
        self.assertEqual(
            calls,
            [
                ("current", matching_passenger),
                ("current", proposed_passenger),
                ("constrained", proposed_passenger),
            ],
        )
        with self.assertRaises(StopIteration):
            next(candidates)

        self.assertNotIn(proposed_passenger, plans)
        self.assertEqual(passengers, [matching_passenger, proposed_passenger])
        self.assertEqual(calls.count(("constrained", proposed_passenger)), 1)

    def test_observes_rebound_plan_map_and_skips_ineligible_passengers(self) -> None:
        first = FakePassenger("first", "triangle")
        matching = FakePassenger("matching", "triangle")
        ineligible = FakePassenger("ineligible", "triangle")
        passengers = [first, matching, ineligible]
        first_proposal = FakeTravelPlan([])
        matching_plan = FakeTravelPlan([])
        matching_plan.next_path = path("red")
        active_plans: list[dict[FakePassenger, FakeTravelPlan]] = [{}]
        calls: list[tuple[str, FakePassenger]] = []

        def get_current_plan(passenger: FakePassenger) -> FakeTravelPlan | None:
            calls.append(("current", passenger))
            return active_plans[0].get(passenger)

        def get_constrained_plan(passenger: FakePassenger) -> FakeTravelPlan | None:
            calls.append(("constrained", passenger))
            if passenger is first:
                return first_proposal
            return None

        candidates = self.planner.iter_boarding_candidates(
            passengers,
            get_required_path_id=lambda: "red",
            get_current_plan=get_current_plan,
            get_constrained_plan=get_constrained_plan,
        )

        proposed_passenger, proposed_plan = next(candidates)
        self.assertIs(proposed_passenger, first)
        self.assertIs(proposed_plan, first_proposal)

        # The caller applies the yielded proposal and can replace its map before resume.
        active_plans[0] = {first: first_proposal, matching: matching_plan}
        matched_passenger, marker = next(candidates)
        self.assertIs(matched_passenger, matching)
        self.assertIsNone(marker)
        with self.assertRaises(StopIteration):
            next(candidates)

        self.assertNotIn(("constrained", matching), calls)
        self.assertEqual(calls.count(("constrained", first)), 1)
        self.assertEqual(calls.count(("constrained", ineligible)), 1)
        self.assertEqual(passengers, [first, matching, ineligible])

    def test_required_path_id_is_resolved_after_each_current_plan_lookup(self) -> None:
        first = FakePassenger("first", "triangle")
        second = FakePassenger("second", "triangle")
        first_plan = FakeTravelPlan([])
        second_plan = FakeTravelPlan([])
        first_plan.next_path = path("first-line")
        second_plan.next_path = path("second-line")
        plans = {first: first_plan, second: second_plan}
        required_ids = iter(["first-line", "second-line"])

        candidates = self.planner.iter_boarding_candidates(
            [first, second],
            get_required_path_id=lambda: next(required_ids),
            get_current_plan=lambda passenger: plans[passenger],
            get_constrained_plan=lambda _passenger: (_ for _ in ()).throw(
                AssertionError("matching plans must not be recomputed")
            ),
        )

        self.assertEqual(list(candidates), [(first, None), (second, None)])

    def test_delays_callback_exception_until_iteration_without_mutation(self) -> None:
        passenger = FakePassenger("waiting", "triangle")
        passengers = [passenger]
        calls: list[str] = []

        def get_current_plan(_passenger: FakePassenger) -> None:
            calls.append("current")
            return None

        def get_constrained_plan(_passenger: FakePassenger) -> None:
            calls.append("constrained")
            raise RuntimeError("late constrained failure")

        candidates = self.planner.iter_boarding_candidates(
            passengers,
            get_required_path_id=lambda: "red",
            get_current_plan=get_current_plan,
            get_constrained_plan=get_constrained_plan,
        )

        self.assertEqual(calls, [])
        with self.assertRaisesRegex(RuntimeError, "late constrained failure"):
            next(candidates)
        self.assertEqual(calls, ["current", "constrained"])
        self.assertEqual(passengers, [passenger])


class TestBulkRouteProposalIterator(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RoutePlanner()

    def test_is_lazy_and_preserves_arrival_reachable_and_unreachable_markers(
        self,
    ) -> None:
        source = station("source", "circle")
        reachable_destination = station("reachable", "triangle")
        unreachable_destination = station("unreachable", "triangle")
        middle = station("middle", "square")
        arrived = FakePassenger("arrived", "circle")
        reachable = FakePassenger("reachable", "triangle")
        unreachable = FakePassenger("unreachable", "triangle")
        source.passengers[:] = [arrived, reachable, unreachable]

        source_node = node(source)
        middle_node = node(middle)
        reachable_node = node(reachable_destination)
        unreachable_node = node(unreachable_destination)
        arrival_path = [source_node]
        raw_reachable_path = [source_node, middle_node, reachable_node]
        reduced_reachable_path = [source_node, reachable_node]
        node_map = LoggingMapping(
            {
                source: source_node,
                reachable_destination: reachable_node,
                unreachable_destination: unreachable_node,
            }
        )
        destinations = {
            arrived: [source],
            reachable: [reachable_destination],
            unreachable: [unreachable_destination],
        }
        calls: list[tuple[str, object]] = []

        def has_travel_plan(passenger: FakePassenger) -> bool:
            calls.append(("planned", passenger))
            return False

        def get_destination_stations(passenger: FakePassenger):
            calls.append(("destinations", passenger))
            return destinations[passenger]

        def find_node_path(start, end):
            calls.append(("find", end))
            if end is source_node:
                return arrival_path
            if end is reachable_node:
                return raw_reachable_path
            return []

        def reduce_node_path(node_path):
            calls.append(("reduce", tuple(node_path)))
            return reduced_reachable_path

        proposals = self.planner.iter_bulk_route_proposals(
            [source],
            has_travel_plan=has_travel_plan,
            get_destination_stations=get_destination_stations,
            node_map=node_map,
            find_node_path=find_node_path,
            get_reduce_node_path=lambda: reduce_node_path,
        )

        self.assertEqual(calls, [])
        self.assertEqual(node_map.accesses, [])

        first_station, first_passenger, first_path, first_kind = next(proposals)
        self.assertIs(first_station, source)
        self.assertIs(first_passenger, arrived)
        self.assertIs(first_path, arrival_path)
        self.assertEqual(first_kind, "arrival")
        self.assertNotIn(("planned", reachable), calls)

        second_station, second_passenger, second_path, second_kind = next(proposals)
        self.assertIs(second_station, source)
        self.assertIs(second_passenger, arrived)
        self.assertIsNone(second_path)
        self.assertEqual(second_kind, "fallback")
        self.assertNotIn(("planned", reachable), calls)

        third_station, third_passenger, third_path, third_kind = next(proposals)
        self.assertIs(third_station, source)
        self.assertIs(third_passenger, reachable)
        self.assertIs(third_path, reduced_reachable_path)
        self.assertEqual(third_kind, "route")
        self.assertNotIn(("planned", unreachable), calls)

        fourth_station, fourth_passenger, fourth_path, fourth_kind = next(proposals)
        self.assertIs(fourth_station, source)
        self.assertIs(fourth_passenger, unreachable)
        self.assertIsNone(fourth_path)
        self.assertEqual(fourth_kind, "fallback")
        with self.assertRaises(StopIteration):
            next(proposals)

        self.assertEqual(source.passengers, [arrived, reachable, unreachable])
        self.assertEqual(raw_reachable_path, [source_node, middle_node, reachable_node])
        self.assertEqual(node_map[source], source_node)

    def test_skips_planned_passenger_and_empty_destinations_do_not_lookup_nodes(
        self,
    ) -> None:
        source = station("source")
        planned = FakePassenger("planned", "triangle")
        empty = FakePassenger("empty", "triangle")
        source.passengers[:] = [planned, empty]
        node_map: LoggingMapping[object, object] = LoggingMapping({})
        destination_calls: list[FakePassenger] = []
        path_calls: list[tuple[object, object]] = []
        reduce_calls: list[list[object]] = []

        def get_destination_stations(passenger: FakePassenger):
            destination_calls.append(passenger)
            return []

        proposals = self.planner.iter_bulk_route_proposals(
            [source],
            has_travel_plan=lambda passenger: passenger is planned,
            get_destination_stations=get_destination_stations,
            node_map=node_map,
            find_node_path=lambda start, end: path_calls.append((start, end)),
            get_reduce_node_path=lambda: lambda nodes: reduce_calls.append(nodes),
        )

        result_station, result_passenger, result_path, result_kind = next(proposals)
        self.assertIs(result_station, source)
        self.assertIs(result_passenger, empty)
        self.assertIsNone(result_path)
        self.assertEqual(result_kind, "fallback")
        with self.assertRaises(StopIteration):
            next(proposals)

        self.assertEqual(destination_calls, [empty])
        self.assertEqual(node_map.accesses, [])
        self.assertEqual(path_calls, [])
        self.assertEqual(reduce_calls, [])
        self.assertEqual(source.passengers, [planned, empty])

    def test_retains_destination_iterable_through_the_fallback_guard(self) -> None:
        source = station("source")
        passenger = FakePassenger("waiting", "triangle")
        source.passengers.append(passenger)
        events: list[str] = []

        class Destinations:
            def __iter__(self):
                return iter(())

            def __del__(self):
                events.append("released")

        proposals = self.planner.iter_bulk_route_proposals(
            [source],
            has_travel_plan=lambda _passenger: False,
            get_destination_stations=lambda _passenger: Destinations(),
            node_map={},
            find_node_path=lambda _start, _end: [],
            get_reduce_node_path=lambda: lambda nodes: nodes,
        )

        self.assertEqual(next(proposals)[3], "fallback")
        self.assertEqual(events, [])
        with self.assertRaises(StopIteration):
            next(proposals)
        self.assertEqual(events, ["released"])

    def test_caller_removal_before_resume_preserves_live_adjacent_skip(self) -> None:
        source = station("source")
        first = FakePassenger("first", "triangle")
        adjacent = FakePassenger("adjacent", "triangle")
        third = FakePassenger("third", "triangle")
        source.passengers[:] = [first, adjacent, third]
        visited: list[FakePassenger] = []

        def has_travel_plan(passenger: FakePassenger) -> bool:
            visited.append(passenger)
            return False

        proposals = self.planner.iter_bulk_route_proposals(
            [source],
            has_travel_plan=has_travel_plan,
            get_destination_stations=lambda _passenger: [],
            node_map={},
            find_node_path=lambda _start, _end: [],
            get_reduce_node_path=lambda: lambda nodes: nodes,
        )

        _, first_passenger, first_path, first_kind = next(proposals)
        self.assertIs(first_passenger, first)
        self.assertIsNone(first_path)
        self.assertEqual(first_kind, "fallback")

        source.passengers.remove(first)
        _, next_passenger, next_path, next_kind = next(proposals)
        self.assertIs(next_passenger, third)
        self.assertIsNone(next_path)
        self.assertEqual(next_kind, "fallback")
        with self.assertRaises(StopIteration):
            next(proposals)

        self.assertEqual(visited, [first, third])
        self.assertEqual(source.passengers, [adjacent, third])

    def test_observes_rebound_plan_state_before_resuming(self) -> None:
        source = station("source")
        first = FakePassenger("first", "triangle")
        second = FakePassenger("second", "triangle")
        source.passengers[:] = [first, second]
        active_plans: list[set[FakePassenger]] = [set()]
        destination_calls: list[FakePassenger] = []

        def has_travel_plan(passenger: FakePassenger) -> bool:
            return passenger in active_plans[0]

        def get_destination_stations(passenger: FakePassenger):
            destination_calls.append(passenger)
            return []

        proposals = self.planner.iter_bulk_route_proposals(
            [source],
            has_travel_plan=has_travel_plan,
            get_destination_stations=get_destination_stations,
            node_map={},
            find_node_path=lambda _start, _end: [],
            get_reduce_node_path=lambda: lambda nodes: nodes,
        )

        _, yielded_passenger, node_path, kind = next(proposals)
        self.assertIs(yielded_passenger, first)
        self.assertIsNone(node_path)
        self.assertEqual(kind, "fallback")

        active_plans[0] = {first, second}
        with self.assertRaises(StopIteration):
            next(proposals)
        self.assertEqual(destination_calls, [first])
        self.assertEqual(source.passengers, [first, second])

    def test_delays_mapping_exception_until_the_failing_passenger_is_requested(
        self,
    ) -> None:
        source = station("source")
        destination = station("destination", "triangle")
        first = FakePassenger("first", "triangle")
        failing = FakePassenger("failing", "triangle")
        source.passengers[:] = [first, failing]
        node_map: LoggingMapping[object, object] = LoggingMapping({})

        def get_destination_stations(passenger: FakePassenger):
            if passenger is first:
                return []
            return [destination]

        proposals = self.planner.iter_bulk_route_proposals(
            [source],
            has_travel_plan=lambda _passenger: False,
            get_destination_stations=get_destination_stations,
            node_map=node_map,
            find_node_path=lambda _start, _end: [],
            get_reduce_node_path=lambda: lambda nodes: nodes,
        )

        self.assertEqual(node_map.accesses, [])
        _, yielded_passenger, node_path, kind = next(proposals)
        self.assertIs(yielded_passenger, first)
        self.assertIsNone(node_path)
        self.assertEqual(kind, "fallback")
        self.assertEqual(node_map.accesses, [])

        with self.assertRaises(KeyError) as raised:
            next(proposals)
        self.assertIs(raised.exception.args[0], source)
        self.assertEqual(node_map.accesses, [source])
        self.assertEqual(source.passengers, [first, failing])


if __name__ == "__main__":
    unittest.main()
