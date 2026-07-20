from __future__ import annotations

import inspect
from types import SimpleNamespace
from unittest.mock import patch

from test import mediator_test_support as support

# isort: split

import mediator as mediator_module
from mediator import Mediator


class _SpawnStation:
    def __init__(self, name: str, events: list[object], *, capacity: int = 3) -> None:
        self.name = name
        self.shape = SimpleNamespace(type="origin")
        self.passengers: list[object] = []
        self.capacity = capacity
        self.events = events

    def has_room(self) -> bool:
        self.events.append(("room", self.name))
        return len(self.passengers) < self.capacity

    def add_passenger(self, passenger: object) -> None:
        self.events.append(("station-add", self.name, passenger))
        self.passengers.append(passenger)


class TestPassengerFlowFacadeContract(support.MediatorTestCase):
    def test_all_extracted_public_signatures_match_the_frozen_baseline(self) -> None:
        expected = {
            "get_station_shape_types": "(self) -> 'List[ShapeType]'",
            "is_passenger_spawn_time": "(self) -> 'bool'",
            "initialize_station_spawning_state": (
                "(self, stations: 'List[Station]') -> 'None'"
            ),
            "get_station_spawn_interval_step": "(self) -> 'int'",
            "should_spawn_passenger_at_station": (
                "(self, station: 'Station') -> 'bool'"
            ),
            "spawn_passengers": "(self) -> 'None'",
            "increment_time": "(self, dt_ms: 'int') -> 'None'",
            "get_next_station_for_metro": (
                "(self, metro: 'Metro') -> 'Station | None'"
            ),
            "get_boarding_candidates_for_metro": (
                "(self, metro: 'Metro', station: 'Station', "
                "station_nodes_dict: 'Dict[Station, Node]', "
                "mutate_travel_plans: 'bool') -> 'List[Passenger]'"
            ),
            "get_unloading_candidates_for_metro": (
                "(self, metro: 'Metro', station: 'Station') -> "
                "'tuple[List[Passenger], List[Passenger]]'"
            ),
            "should_stop_at_next_station": (
                "(self, metro: 'Metro', station_nodes_dict: "
                "'Dict[Station, Node]') -> 'bool'"
            ),
            "start_station_stop_if_needed": (
                "(self, metro: 'Metro', station: 'Station', "
                "station_nodes_dict: 'Dict[Station, Node]') -> 'None'"
            ),
            "can_board_at_station": (
                "(self, metro: 'Metro', station: 'Station') -> 'bool'"
            ),
            "move_passengers": "(self, dt_ms: 'int') -> 'None'",
            "update_waiting_and_game_over": ("(self, dt_ms: 'int') -> 'None'"),
            "find_travel_plan_for_passengers": "(self) -> 'None'",
        }

        observed = {
            name: str(inspect.signature(getattr(Mediator, name))) for name in expected
        }

        self.assertEqual(observed, expected)

    def test_spawn_resolves_globals_after_due_hook_and_for_each_station(self) -> None:
        mediator = Mediator(seed=1)
        events: list[object] = []
        first = _SpawnStation("first", events)
        second = _SpawnStation("second", events)
        mediator.stations = [first, second]
        mediator.station_steps_since_last_spawn = {first: 7, second: 8}
        mediator.get_station_shape_types = lambda: ["origin", "destination"]
        first_color, second_color = object(), object()
        first_size, second_size = object(), object()

        def passenger_one(shape: object) -> object:
            passenger = SimpleNamespace(name="passenger-one", shape=shape)
            events.append(("passenger-one", shape))
            return passenger

        def passenger_two(shape: object) -> object:
            passenger = SimpleNamespace(name="passenger-two", shape=shape)
            events.append(("passenger-two", shape))
            return passenger

        def shape_two(shape_type: object, color: object, size: object) -> object:
            events.append(("shape-two", shape_type, color, size))
            mediator_module.Passenger = passenger_two
            return SimpleNamespace(name="shape-two")

        def shape_one(shape_type: object, color: object, size: object) -> object:
            events.append(("shape-one", shape_type, color, size))
            mediator_module.get_shape_from_type = shape_two
            mediator_module.passenger_color = second_color
            mediator_module.passenger_size = second_size
            mediator_module.Passenger = passenger_one
            return SimpleNamespace(name="shape-one")

        def due(station: _SpawnStation) -> bool:
            events.append(("due", station.name))
            if station is first:
                mediator_module.get_shape_from_type = shape_one
                mediator_module.passenger_color = first_color
                mediator_module.passenger_size = first_size
            return True

        def unresolved(*_args: object) -> object:
            raise AssertionError("spawn dependency resolved before the due hook")

        def choose(options: list[object]) -> object:
            events.append(("choice", tuple(options)))
            return options[0]

        mediator.should_spawn_passenger_at_station = due
        with (
            patch.object(mediator_module, "get_shape_from_type", unresolved),
            patch.object(mediator_module, "Passenger", unresolved),
            patch.object(mediator_module, "passenger_color", object()),
            patch.object(mediator_module, "passenger_size", object()),
            patch.object(mediator.context.python_random, "choice", side_effect=choose),
        ):
            mediator.spawn_passengers()

        self.assertEqual(
            events,
            [
                ("due", "first"),
                ("choice", ("destination",)),
                ("shape-one", "destination", first_color, first_size),
                ("passenger-one", first.passengers[0].shape),
                ("room", "first"),
                ("station-add", "first", first.passengers[0]),
                ("due", "second"),
                ("choice", ("destination",)),
                ("shape-two", "destination", second_color, second_size),
                ("passenger-two", second.passengers[0].shape),
                ("room", "second"),
                ("station-add", "second", second.passengers[0]),
            ],
        )
        self.assertEqual(
            mediator.passengers, [first.passengers[0], second.passengers[0]]
        )
        self.assertEqual(mediator.station_steps_since_last_spawn, {first: 0, second: 0})

    def test_spawn_exception_preserves_prior_success_and_failing_partial_state(
        self,
    ) -> None:
        mediator = Mediator(seed=1)
        events: list[object] = []
        first = _SpawnStation("first", events)
        second = _SpawnStation("second", events)
        mediator.stations = [first, second]
        mediator.station_steps_since_last_spawn = {first: 11, second: 12}
        mediator.get_station_shape_types = lambda: ["origin", "destination"]
        mediator.should_spawn_passenger_at_station = lambda _station: True
        created: list[object] = []

        class FailingGlobalPassengers(list[object]):
            def append(self, passenger: object) -> None:
                events.append(("global-append", passenger))
                if len(self) == 1:
                    raise RuntimeError("second global append failed")
                super().append(passenger)

        def make_passenger(shape: object) -> object:
            passenger = SimpleNamespace(index=len(created), shape=shape)
            created.append(passenger)
            events.append(("construct", passenger))
            return passenger

        mediator.passengers = FailingGlobalPassengers()
        with (
            patch.object(
                mediator_module,
                "get_shape_from_type",
                side_effect=lambda *_args: object(),
            ),
            patch.object(mediator_module, "Passenger", side_effect=make_passenger),
            patch.object(
                mediator.context.python_random,
                "choice",
                return_value="destination",
            ),
            self.assertRaisesRegex(RuntimeError, "second global append failed"),
        ):
            mediator.spawn_passengers()

        self.assertEqual(first.passengers, [created[0]])
        self.assertEqual(second.passengers, [created[1]])
        self.assertEqual(mediator.passengers, [created[0]])
        self.assertEqual(mediator.station_steps_since_last_spawn[first], 0)
        self.assertEqual(mediator.station_steps_since_last_spawn[second], 12)

    def test_spawn_probe_uses_live_stations_dynamic_hook_and_short_circuit(
        self,
    ) -> None:
        mediator = Mediator()
        first, second, never = object(), object(), object()
        mediator.stations = [first]
        calls: list[object] = []

        def rebound(station: object) -> bool:
            calls.append(station)
            mediator.stations.append(never)
            return True

        def initial(station: object) -> bool:
            calls.append(station)
            mediator.stations.append(second)
            mediator.should_spawn_passenger_at_station = rebound
            return False

        mediator.should_spawn_passenger_at_station = initial

        self.assertTrue(mediator.is_passenger_spawn_time())
        self.assertEqual(calls, [first, second])
        self.assertEqual(mediator.stations, [first, second, never])

    def test_spawn_state_initialization_uses_live_input_and_rebound_hook(self) -> None:
        mediator = Mediator()
        first, second, appended = object(), object(), object()
        stations = [first, second]
        mediator.station_spawn_interval_steps = {}
        mediator.station_steps_since_last_spawn = {}
        calls: list[str] = []

        def rebound() -> int:
            calls.append("rebound")
            return 22

        def initial() -> int:
            calls.append("initial")
            stations.append(appended)
            mediator.get_station_spawn_interval_step = rebound
            return 11

        mediator.get_station_spawn_interval_step = initial
        mediator.initialize_station_spawning_state(stations)

        self.assertEqual(calls, ["initial", "rebound", "rebound"])
        self.assertEqual(
            mediator.station_spawn_interval_steps,
            {first: 11, second: 22, appended: 22},
        )
        self.assertEqual(
            mediator.station_steps_since_last_spawn,
            {first: 11, second: 22, appended: 22},
        )

    def test_boarding_resolves_one_router_iterator_and_applies_before_resume(
        self,
    ) -> None:
        mediator = Mediator()
        events: list[object] = []
        first, second = object(), object()
        first_plan, second_plan = object(), object()
        station = SimpleNamespace(passengers=[first, second])
        metro = SimpleNamespace(path_id="path")
        path = object()
        mediator.get_path_by_id = lambda _path_id: path

        class ExplodingRouter:
            @property
            def iter_boarding_candidates(self):
                raise AssertionError("router iterator was resolved more than once")

        class Router:
            @property
            def iter_boarding_candidates(self):
                events.append("resolve")

                def build(*_args: object, **_kwargs: object):
                    events.append("build")

                    def proposals():
                        yield first, first_plan
                        events.append(("after-first", mediator.travel_plans[first]))
                        mediator._router = ExplodingRouter()
                        yield second, second_plan
                        events.append(("after-second", mediator.travel_plans[second]))

                    return proposals()

                return build

        mediator._router = Router()
        candidates = mediator.get_boarding_candidates_for_metro(
            metro, station, {}, mutate_travel_plans=True
        )

        self.assertEqual(candidates, [first, second])
        self.assertEqual(
            events,
            [
                "resolve",
                "build",
                ("after-first", first_plan),
                ("after-second", second_plan),
            ],
        )

    def test_active_tick_builds_three_fresh_graphs_and_uses_live_collections(
        self,
    ) -> None:
        mediator = Mediator()
        events: list[object] = []
        graphs = [object(), object(), object()]

        class Station:
            def __init__(self, name: str) -> None:
                self.name = name
                self.passengers: list[object] = []

            def prune_visual_effects(self, now: int) -> None:
                events.append(("prune", self.name, now))
                if self.name == "first":
                    mediator.stations.append(second_station)

        class Metro:
            def __init__(self, name: str, station: object | None) -> None:
                self.name = name
                self.current_station = station
                self.stop_time_remaining_ms = 0
                self.just_arrived_and_stopped = False

        class Path:
            def __init__(self, name: str, metro: Metro) -> None:
                self.name = name
                self.metros = [metro]

            def move_metro(
                self,
                metro: Metro,
                dt_ms: int,
                *,
                should_stop_at_next_station: bool,
            ) -> None:
                events.append(
                    ("path-move", self.name, dt_ms, should_stop_at_next_station)
                )
                if self.name == "first":
                    mediator.paths.append(second_path)
                    metro.just_arrived_and_stopped = True

        first_station = Station("first")
        second_station = Station("second")
        first_metro = Metro("first", first_station)
        second_metro = Metro("second", None)
        first_path = Path("first", first_metro)
        second_path = Path("second", second_metro)
        mediator.stations = [first_station]
        mediator.paths = [first_path]
        mediator.metros = []
        mediator.station_steps_since_last_spawn = {
            first_station: 0,
            second_station: 4,
        }
        mediator.game_speed_multiplier = 2
        live_stations = mediator.stations
        live_paths = mediator.paths

        def initialize(stations: list[object]) -> None:
            events.append(("initialize", stations is live_stations))

        def build_graph(stations: list[object], paths: list[object]) -> object:
            index = sum(1 for event in events if event[0] == "build")
            events.append(
                (
                    "build",
                    index,
                    stations is live_stations,
                    paths is live_paths,
                    tuple(station.name for station in stations),
                    tuple(path.name for path in paths),
                )
            )
            return graphs[index]

        def start_stop(metro: Metro, _station: object, graph: object) -> None:
            events.append(("start-stop", metro.name, graphs.index(graph)))

        def should_stop(metro: Metro, graph: object) -> bool:
            events.append(("should-stop", metro.name, graphs.index(graph)))
            return True

        original_find = mediator.find_travel_plan_for_passengers
        original_move = mediator.move_passengers

        def find_plans() -> None:
            events.append("find-plans")
            original_find()

        def move_passengers(dt_ms: int) -> None:
            events.append(("exchange", dt_ms))
            original_move(dt_ms)

        mediator.initialize_station_spawning_state = initialize
        mediator.start_station_stop_if_needed = start_stop
        mediator.should_stop_at_next_station = should_stop
        mediator.is_passenger_spawn_time = lambda: events.append("spawn-probe") or True
        mediator.spawn_passengers = lambda: events.append("spawn")
        mediator.find_travel_plan_for_passengers = find_plans
        mediator.move_passengers = move_passengers
        mediator.update_waiting_and_game_over = lambda dt_ms: events.append(
            ("waiting", dt_ms)
        )

        with patch.object(
            mediator_module, "build_station_nodes_dict", side_effect=build_graph
        ):
            mediator.increment_time(7)

        self.assertEqual(mediator.time_ms, 14)
        self.assertEqual(mediator.steps, 2)
        self.assertEqual(mediator.station_steps_since_last_spawn[first_station], 2)
        self.assertEqual(mediator.station_steps_since_last_spawn[second_station], 6)
        self.assertEqual(
            events,
            [
                ("initialize", True),
                ("prune", "first", 14),
                ("prune", "second", 14),
                ("build", 0, True, True, ("first", "second"), ("first",)),
                ("start-stop", "first", 0),
                ("should-stop", "first", 0),
                ("path-move", "first", 14, True),
                ("start-stop", "first", 0),
                ("should-stop", "second", 0),
                ("path-move", "second", 14, True),
                "spawn-probe",
                "spawn",
                "find-plans",
                (
                    "build",
                    1,
                    True,
                    True,
                    ("first", "second"),
                    ("first", "second"),
                ),
                ("exchange", 14),
                (
                    "build",
                    2,
                    True,
                    True,
                    ("first", "second"),
                    ("first", "second"),
                ),
                ("waiting", 14),
            ],
        )


if __name__ == "__main__":
    support.unittest.main()
