import sys
import unittest
from pathlib import Path

from test.passenger_flow_direct_support import (
    FakeHost,
    FakeMetro,
    FakeNode,
    FakePassenger,
    FakePath,
    FakePlan,
    FakeSegment,
    FakeShape,
    FakeStation,
    RaisingAppendList,
    RaisingCounterMap,
    assert_component_boundary,
    assert_station_service_action,
)

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# isort: split

from passenger_flow import PassengerFlow


class TestPassengerFlow(unittest.TestCase):
    def setUp(self):
        self.flow = PassengerFlow()

    def test_component_is_stateless_non_retaining_and_import_isolated(self):
        assert_component_boundary(self, self.flow, PassengerFlow)

    def test_shape_types_and_spawn_probe_are_live_call_scoped_and_short_circuit(self):
        first = FakeHost(self.flow)
        first.stations = [
            FakeStation("a", "circle", first.events),
            FakeStation("b", "triangle", first.events),
            FakeStation("c", "circle", first.events),
        ]
        second = FakeHost(self.flow)
        second.stations = [FakeStation("x", "cross", second.events)]
        self.assertEqual(
            self.flow.get_station_shape_types(first), ["circle", "triangle"]
        )
        self.assertEqual(self.flow.get_station_shape_types(second), ["cross"])

        calls = []

        def due(station):
            calls.append(station.name)
            return station.name == "a"

        first.should_spawn_passenger_at_station = due
        self.assertTrue(self.flow.is_passenger_spawn_time(first))
        self.assertEqual(calls, ["a"])

    def test_spawn_state_samples_once_and_preserves_existing_entries(self):
        host = FakeHost(self.flow)
        a = FakeStation("a", "a", host.events)
        b = FakeStation("b", "b", host.events)
        c = FakeStation("c", "c", host.events)
        host.context.python_random.randint_values = [70, 130]
        host.station_spawn_interval_steps = {a: 99}
        host.station_steps_since_last_spawn = {c: 5}

        self.flow.initialize_station_spawning_state(host, [a, b, c])

        self.assertEqual(host.station_spawn_interval_steps, {a: 99, b: 70, c: 130})
        self.assertEqual(host.station_steps_since_last_spawn, {a: 99, b: 70, c: 5})
        self.assertEqual(
            [event for event in host.events if event[0] == "randint"],
            [("randint", 70, 130), ("randint", 70, 130)],
        )
        host.steps = host.passenger_spawning_step
        self.assertTrue(self.flow.should_spawn_passenger_at_station(host, b))
        host.steps = 0
        host.station_steps_since_last_spawn[b] = 69
        self.assertFalse(self.flow.should_spawn_passenger_at_station(host, b))

    def test_spawn_resolves_factories_and_values_per_due_station_and_resets_full(self):
        host = FakeHost(self.flow)
        a = FakeStation("a", "a", host.events)
        b = FakeStation("b", "b", host.events, capacity=0)
        c = FakeStation("c", "c", host.events)
        host.stations = [a, b, c]
        host.station_steps_since_last_spawn = {a: 10, b: 11, c: 12}
        host.should_spawn_passenger_at_station = lambda station: station is not c
        host.context.python_random.choice_values = ["b", "a"]
        resolution = []
        produced = []

        def shape_factory(label):
            def build(shape_type, color, size):
                resolution.append(("shape", label, shape_type, color, size))
                return FakeShape(shape_type)

            return build

        def passenger_factory(label):
            def build(shape):
                resolution.append(("passenger", label, shape.type))
                passenger = FakePassenger(label, shape.type, host.events)
                produced.append(passenger)
                return passenger

            return build

        shape_factories = iter([shape_factory("one"), shape_factory("two")])
        passenger_factories = iter([passenger_factory("one"), passenger_factory("two")])
        colors = iter(["red", "blue"])
        sizes = iter([1, 2])

        def resolve(label, values):
            resolution.append(("get", label))
            return next(values)

        self.flow.spawn_passengers(
            host,
            get_shape_factory=lambda: resolve("shape", shape_factories),
            get_passenger_factory=lambda: resolve("passenger", passenger_factories),
            get_passenger_color=lambda: resolve("color", colors),
            get_passenger_size=lambda: resolve("size", sizes),
        )

        self.assertEqual(
            [item[:2] for item in resolution],
            [
                ("get", "shape"),
                ("get", "color"),
                ("get", "size"),
                ("shape", "one"),
                ("get", "passenger"),
                ("passenger", "one"),
                ("get", "shape"),
                ("get", "color"),
                ("get", "size"),
                ("shape", "two"),
                ("get", "passenger"),
                ("passenger", "two"),
            ],
        )
        self.assertEqual(a.passengers, [produced[0]])
        self.assertEqual(host.passengers, [produced[0]])
        self.assertEqual(b.passengers, [])
        self.assertEqual(host.station_steps_since_last_spawn, {a: 0, b: 0, c: 12})

    def test_spawn_failures_preserve_exact_partial_state_and_due_counter(self):
        for failure in ("append", "counter"):
            with self.subTest(failure=failure):
                host = FakeHost(self.flow)
                a = FakeStation("a", "a", host.events)
                b = FakeStation("b", "b", host.events)
                host.stations = [a, b]
                host.should_spawn_passenger_at_station = lambda station: station is a
                if failure == "append":
                    host.passengers = RaisingAppendList()
                    host.station_steps_since_last_spawn = {a: 10, b: 0}
                    message = "append failed"
                else:
                    host.station_steps_since_last_spawn = RaisingCounterMap(
                        {a: 10, b: 1}
                    )
                    message = "counter reset failed"

                with self.assertRaisesRegex(RuntimeError, message):
                    host.spawn_passengers()

                self.assertEqual(len(a.passengers), 1)
                self.assertEqual(host.station_steps_since_last_spawn[a], 10)
                self.assertEqual(len(host.passengers), 0 if failure == "append" else 1)

    def test_increment_time_uses_three_fresh_ordered_graph_phases(self):
        host = FakeHost(self.flow)
        station = FakeStation("station", "a", host.events)
        metro = FakeMetro("metro", host.events)
        metro.current_segment = FakeSegment(station, station)
        path = FakePath("path", host.events, [metro])
        host.stations = [station]
        host.paths = [path]
        host.metros = [metro]
        host.station_spawn_interval_steps = {station: 10}
        host.station_steps_since_last_spawn = {station: 2}

        def graph(label):
            def build(stations, paths):
                host.events.append(("graph", label))
                return label

            return build

        host.graph_builder = graph("move")
        path.on_move = lambda: setattr(host, "graph_builder", graph("plan"))

        def bulk(*args, **kwargs):
            host.events.append(("bulk",))
            host.graph_builder = graph("exchange")
            return iter(())

        host.bulk_iterator = bulk
        host.should_stop_at_next_station = lambda metro, nodes: (
            host.events.append(("stop?", nodes)) or False
        )
        host.is_passenger_spawn_time = lambda: host.events.append(("spawn?",)) or False
        host.game_speed_multiplier = 2

        self.flow.increment_time(
            host, 100, get_graph_builder=lambda: host.graph_builder
        )

        self.assertEqual((host.time_ms, host.steps), (200, 2))
        self.assertEqual(host.station_steps_since_last_spawn[station], 4)
        markers = [event for event in host.events if event[0] in {"graph", "bulk"}]
        self.assertEqual(
            markers,
            [("graph", "move"), ("graph", "plan"), ("bulk",), ("graph", "exchange")],
        )
        self.assertIn(("stop?", "move"), host.events)
        self.assertIn(("path:move", "path", "metro", 200, False), host.events)

        paused = FakeHost(self.flow)
        paused.is_paused = True
        self.flow.increment_time(
            paused,
            100,
            get_graph_builder=lambda: (_ for _ in ()).throw(
                AssertionError("paused tick resolved graph")
            ),
        )

    def test_boarding_resolves_router_late_once_and_applies_before_resume(self):
        host = FakeHost(self.flow)
        station = FakeStation("station", "a", host.events)
        metro = FakeMetro("metro", host.events)
        self.assertEqual(
            self.flow.get_boarding_candidates_for_metro(
                host,
                metro,
                station,
                {},
                True,
                get_boarding_iterator=lambda: (_ for _ in ()).throw(
                    AssertionError("missing path resolved router")
                ),
            ),
            [],
        )

        path = FakePath("path", host.events)
        host.paths = [path]
        one = FakePassenger("one", "b", host.events)
        two = FakePassenger("two", "b", host.events)
        station.passengers = [one, two]
        plans = [FakePlan(next_path=path), FakePlan(next_path=path)]
        plan_calls = []

        def constrained(passenger, *args):
            plan_calls.append(passenger.name)
            return plans[len(plan_calls) - 1]

        host.get_travel_plan_starting_with_path = constrained

        def late_iterator(passengers, **callbacks):
            host.events.append(("iterator:start", callbacks["get_required_path_id"]()))
            yield one, callbacks["get_constrained_plan"](one)
            self.assertIs(host.travel_plans[one], plans[0])
            metro.path_id = "rebound"
            yield two, callbacks["get_constrained_plan"](two)
            host.events.append(("iterator:end", callbacks["get_required_path_id"]()))

        def resolve_path(path_id):
            host.events.append(("path:get", path_id))
            host.boarding_iterator = late_iterator
            return path

        host.get_path_by_id = resolve_path
        router_gets = []
        candidates = self.flow.get_boarding_candidates_for_metro(
            host,
            metro,
            station,
            {},
            True,
            get_boarding_iterator=lambda: (
                router_gets.append("get") or host.boarding_iterator
            ),
        )

        self.assertEqual(candidates, [one, two])
        self.assertEqual(plan_calls, ["one", "two"])
        self.assertEqual(router_gets, ["get"])
        self.assertEqual(host.events[-1], ("iterator:end", "rebound"))

    def test_navigation_unloading_capacity_and_stop_setup_semantics(self):
        host = FakeHost(self.flow)
        here = FakeStation("here", "a", host.events)
        there = FakeStation("there", "b", host.events)
        metro = FakeMetro("metro", host.events, capacity=2)
        metro.current_segment = FakeSegment(there, here)
        destination = FakePassenger("destination", "a", host.events)
        transfer = FakePassenger("transfer", "c", host.events)
        metro.passengers = [destination, transfer]
        host.travel_plans[transfer] = FakePlan([FakeNode(here)], host.events)
        path = FakePath("path", host.events)
        host.paths = [path]
        waiting = FakePassenger("waiting", "b", host.events)
        here.passengers = [waiting]
        host.travel_plans[waiting] = FakePlan(next_path=path)

        self.assertIs(self.flow.get_next_station_for_metro(host, metro), here)
        metro.is_forward = False
        self.assertIs(self.flow.get_next_station_for_metro(host, metro), there)
        metro.is_forward = True
        unload = self.flow.get_unloading_candidates_for_metro(host, metro, here)
        self.assertEqual(unload, ([destination], [transfer]))
        self.assertTrue(self.flow.can_board_at_station(host, metro, here))
        self.assertTrue(self.flow.should_stop_at_next_station(host, metro, {}))
        self.flow.start_station_stop_if_needed(host, metro, here, {})
        self.assertEqual(metro.stop_time_remaining_ms, 500)
        self.assertEqual(metro.boarding_progress_ms, 0)
        assert_station_service_action(self, metro, "destination", destination)
        self.assertEqual(metro.speed, 0)

    def test_move_prioritizes_delivery_transfer_then_board_and_reresolves_award(self):
        host = FakeHost(self.flow)
        here = FakeStation("here", "a", host.events)
        there = FakeStation("there", "b", host.events)
        path = FakePath("path", host.events)
        metro = FakeMetro("metro", host.events)
        metro.current_station = here
        metro.stop_time_remaining_ms = 2000
        delivered_one = FakePassenger("delivered-one", "a", host.events)
        delivered_two = FakePassenger("delivered-two", "a", host.events)
        transfer = FakePassenger("transfer", "c", host.events)
        boarding = FakePassenger("boarding", "b", host.events)
        metro.passengers = [delivered_one, delivered_two, transfer]
        here.passengers = [boarding]
        transfer.wait_ms = boarding.wait_ms = 99
        transfer_plan = FakePlan(
            [FakeNode(here), FakeNode(there)], host.events, next_path=path
        )
        host.travel_plans = {
            delivered_one: FakePlan(),
            delivered_two: FakePlan(),
            transfer: transfer_plan,
            boarding: FakePlan([FakeNode(there)], next_path=path),
        }
        host.passengers = [delivered_one, delivered_two, transfer, boarding]
        host.paths = [path]
        host.metros = [metro]
        awards = iter(
            [
                lambda: host.events.append(("award", "one")),
                lambda: host.events.append(("award", "two")),
            ]
        )

        self.flow.move_passengers(
            host,
            2000,
            get_graph_builder=lambda: lambda stations, paths: "graph",
            get_record_delivery=lambda: next(awards),
        )

        self.assertTrue(delivered_one.is_at_destination)
        self.assertTrue(delivered_two.is_at_destination)
        self.assertEqual(metro.passengers, [boarding])
        self.assertEqual(here.passengers, [transfer])
        self.assertEqual((transfer.wait_ms, boarding.wait_ms), (0, 0))
        self.assertNotIn(delivered_one, host.passengers)
        self.assertNotIn(delivered_two, host.travel_plans)
        expected = [
            ("award", "one"),
            ("unlock-paths",),
            ("unlock-stations",),
            ("award", "two"),
            ("metro:move", "metro", "transfer"),
            ("plan:increment",),
            ("next-path", "transfer", "here"),
            ("station:move", "here", "boarding"),
        ]
        positions = [host.events.index(event) for event in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (0, 0)
        )

    def test_blocked_transfer_clears_unused_dwell_without_moving_rider(self):
        host = FakeHost(self.flow)
        station = FakeStation("full", "a", host.events, capacity=0)
        metro = FakeMetro("metro", host.events, capacity=1)
        passenger = FakePassenger("transfer", "b", host.events)
        metro.passengers = [passenger]
        metro.current_station = station
        metro.stop_time_remaining_ms = 500
        host.travel_plans[passenger] = FakePlan([FakeNode(station)])
        host.metros = [metro]

        self.flow.move_passengers(
            host,
            500,
            get_graph_builder=lambda: lambda stations, paths: {},
            get_record_delivery=lambda: lambda: None,
        )

        self.assertEqual(metro.passengers, [passenger])
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (0, 0)
        )

    def test_waiting_uses_inclusive_limit_finishes_live_scan_and_then_short_circuits(
        self,
    ):
        host = FakeHost(self.flow)
        station = FakeStation("station", "a", host.events)
        one = FakePassenger("one", "b", host.events)
        two = FakePassenger("two", "b", host.events)
        later = FakePassenger("later", "b", host.events)
        one.wait_ms, two.wait_ms, later.wait_ms = 90, 99, 0
        station.passengers = [one, two, later]
        host.stations = [station]

        self.flow.update_waiting_and_game_over(host, 10)

        self.assertEqual((one.wait_ms, two.wait_ms, later.wait_ms), (100, 109, 10))
        self.assertTrue(host.is_game_over)
        self.flow.update_waiting_and_game_over(host, 10)
        self.assertEqual((one.wait_ms, two.wait_ms, later.wait_ms), (100, 109, 10))

    def test_bulk_proposals_apply_lazily_with_late_search_and_plan_factories(self):
        host = FakeHost(self.flow)
        old_station = FakeStation("old", "a", host.events)
        station = FakeStation("live", "a", host.events)
        arrival = FakePassenger("arrival", "a", host.events)
        routed = FakePassenger("routed", "b", host.events)
        fallback = FakePassenger("fallback", "c", host.events)
        station.passengers = [arrival, routed, fallback]
        host.stations = [old_station]
        host.passengers = [arrival, routed, fallback]
        host.travel_plans[arrival] = FakePlan()
        graph = object()
        plan_inputs = []

        def factory(label):
            def build(route):
                plan_inputs.append((label, [node.station.name for node in route]))
                return FakePlan(route, host.events)

            return build

        host.plan_factory = factory("route")
        host.search = lambda start, end: "first"

        def proposals(stations, **callbacks):
            self.assertEqual(stations, [station])
            self.assertIs(callbacks["node_map"], graph)
            self.assertEqual(callbacks["find_node_path"]("a", "b"), "first")
            host.search = lambda start, end: "second"
            self.assertEqual(callbacks["find_node_path"]("a", "b"), "second")
            yield station, arrival, [FakeNode(station)], "arrival"
            self.assertNotIn(arrival, host.passengers)
            self.assertTrue(arrival.is_at_destination)
            yield station, arrival, None, "fallback"
            route = [FakeNode(station), FakeNode(old_station)]
            yield station, routed, route, "route"
            self.assertIn(routed, host.travel_plans)
            host.plan_factory = factory("fallback")
            yield station, fallback, None, "fallback"
            self.assertIn(fallback, host.travel_plans)
            host.events.append(("bulk:finalized",))

        bulk_gets = []

        def get_bulk_iterator():
            bulk_gets.append("get")
            host.stations = [station]
            return proposals

        self.flow.find_travel_plan_for_passengers(
            host,
            get_graph_builder=lambda: (
                lambda stations, paths: host.events.append(("graph", stations)) or graph
            ),
            get_bulk_iterator=get_bulk_iterator,
            get_search=lambda: host.search,
            get_plan_factory=lambda: host.plan_factory,
        )

        self.assertEqual(bulk_gets, ["get"])
        self.assertEqual(host.events[0], ("graph", [old_station]))
        self.assertNotIn(arrival, host.travel_plans)
        self.assertEqual(plan_inputs, [("route", ["old"]), ("fallback", [])])
        self.assertEqual(host.travel_plans[fallback].node_path, [])
        self.assertEqual(host.events[-1], ("bulk:finalized",))


if __name__ == "__main__":
    unittest.main()
