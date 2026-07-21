import gc
import os
import subprocess
import sys
import weakref
from pathlib import Path


def assert_import_isolated(test_case):
    repo_root = Path(__file__).resolve().parents[1]
    source_root = repo_root / "src"
    blocked = (
        "pygame",
        "mediator",
        "entity",
        "graph",
        "progression",
        "route_planner",
        "simulation_context",
        "travel_plan",
        "rendering",
        "ui",
    )
    script = f"""
import sys
import passenger_flow

blocked = {blocked!r}
loaded = sorted(
    name for name in sys.modules
    if any(name == root or name.startswith(f"{{root}}.") for root in blocked)
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
    test_case.assertEqual(result.returncode, 0, result.stderr)


class FakeShape:
    def __init__(self, shape_type):
        self.type = shape_type


class FakeNode:
    def __init__(self, station):
        self.station = station


class FakePassenger:
    def __init__(self, name, destination_type, events):
        self.name = name
        self.destination_shape = FakeShape(destination_type)
        self.events = events
        self.is_at_destination = False
        self.wait_ms = 0


class FakeStation:
    def __init__(self, name, shape_type, events, *, capacity=12):
        self.name = name
        self.shape = FakeShape(shape_type)
        self.events = events
        self.capacity = capacity
        self.passengers = []

    def has_room(self):
        self.events.append(("room", self.name))
        return len(self.passengers) < self.capacity

    def add_passenger(self, passenger):
        self.events.append(("station:add", self.name, passenger.name))
        self.passengers.append(passenger)

    def remove_passenger(self, passenger):
        self.events.append(("station:remove", self.name, passenger.name))
        self.passengers.remove(passenger)

    def move_passenger(self, passenger, metro):
        self.events.append(("station:move", self.name, passenger.name))
        self.passengers.remove(passenger)
        metro.add_passenger(passenger)

    def prune_visual_effects(self, time_ms):
        self.events.append(("prune", self.name, time_ms))


class FakePlan:
    def __init__(self, route=(), events=None, *, next_path=None):
        self.node_path = list(route)
        self.events = events if events is not None else []
        self.next_path = next_path
        self.next_station = self._station_at(0)

    def _station_at(self, index):
        if index >= len(self.node_path):
            return None
        value = self.node_path[index]
        return value.station if hasattr(value, "station") else value

    def get_next_station(self):
        return self.next_station

    def increment_next_station(self):
        self.events.append(("plan:increment",))
        if self.node_path:
            self.node_path.pop(0)
        self.next_station = self._station_at(0)


class FakeSegment:
    def __init__(self, start_station, end_station):
        self.start_station = start_station
        self.end_station = end_station


class FakeMetro:
    def __init__(self, name, events, *, capacity=6):
        self.name = name
        self.events = events
        self.capacity = capacity
        self.passengers = []
        self.path_id = "path"
        self.current_station = None
        self.current_segment = None
        self.is_forward = True
        self.just_arrived_and_stopped = False
        self.stop_time_remaining_ms = 0
        self.boarding_progress_ms = 0
        self.boarding_time_per_passenger_ms = 500
        self._station_service_action = None
        self.speed = 10

    def has_room(self):
        return len(self.passengers) < self.capacity

    def add_passenger(self, passenger):
        self.events.append(("metro:add", self.name, passenger.name))
        self.passengers.append(passenger)

    def remove_passenger(self, passenger):
        self.events.append(("metro:remove", self.name, passenger.name))
        self.passengers.remove(passenger)

    def move_passenger(self, passenger, station):
        self.events.append(("metro:move", self.name, passenger.name))
        self.passengers.remove(passenger)
        station.add_passenger(passenger)


class FakePath:
    def __init__(self, path_id, events, metros=()):
        self.id = path_id
        self.events = events
        self.metros = list(metros)
        self.stations = []
        self.on_move = None

    def move_metro(self, metro, dt_ms, *, should_stop_at_next_station):
        self.events.append(
            ("path:move", self.id, metro.name, dt_ms, should_stop_at_next_station)
        )
        if self.on_move is not None:
            self.on_move()


class FakeRandom:
    def __init__(self, events):
        self.events = events
        self.randint_values = []
        self.choice_values = []

    def randint(self, low, high):
        self.events.append(("randint", low, high))
        return self.randint_values.pop(0) if self.randint_values else low

    def choice(self, values):
        self.events.append(("choice", tuple(values)))
        return self.choice_values.pop(0) if self.choice_values else values[0]


class FakeContext:
    def __init__(self, events):
        self.python_random = FakeRandom(events)


class RaisingAppendList(list):
    def append(self, value):
        raise RuntimeError("append failed")


class RaisingCounterMap(dict):
    def __setitem__(self, key, value):
        if value == 0:
            raise RuntimeError("counter reset failed")
        super().__setitem__(key, value)


def iter_boarding_candidates(
    passengers,
    *,
    get_required_path_id,
    get_current_plan,
    get_constrained_plan,
):
    for passenger in passengers:
        current = get_current_plan(passenger)
        if (
            current is not None
            and current.next_path is not None
            and current.next_path.id == get_required_path_id()
        ):
            yield passenger, None
            continue
        proposed = get_constrained_plan(passenger)
        if proposed is not None:
            yield passenger, proposed


class FakeHost:
    def __init__(self, flow):
        self.flow = flow
        self.events = []
        self.context = FakeContext(self.events)
        self.stations = []
        self.paths = []
        self.metros = []
        self.passengers = []
        self.travel_plans = {}
        self.station_spawn_interval_steps = {}
        self.station_steps_since_last_spawn = {}
        self.passenger_spawning_interval_step = 100
        self.passenger_spawning_step = 1
        self.steps = 0
        self.time_ms = 0
        self.is_paused = False
        self.is_game_over = False
        self.game_speed_multiplier = 1
        self.passenger_max_wait_time_ms = 100
        self.overdue_passenger_threshold = 2
        self.graph_builder = lambda stations, paths: object()
        self.boarding_iterator = iter_boarding_candidates
        self.bulk_iterator = lambda *args, **kwargs: iter(())
        self.search = lambda start, end: []
        self.plan_factory = lambda route: FakePlan(route, self.events)
        self.passenger_factory = lambda shape: FakePassenger(
            "spawned", shape.type, self.events
        )
        self.shape_factory = lambda shape_type, color, size: FakeShape(shape_type)
        self.passenger_color = "color"
        self.passenger_size = 7
        self.record_delivery = lambda: self.events.append(("delivery",))

    def get_station_shape_types(self):
        return self.flow.get_station_shape_types(self)

    def get_station_spawn_interval_step(self):
        return self.flow.get_station_spawn_interval_step(self)

    def initialize_station_spawning_state(self, stations):
        return self.flow.initialize_station_spawning_state(self, stations)

    def should_spawn_passenger_at_station(self, station):
        return self.flow.should_spawn_passenger_at_station(self, station)

    def is_passenger_spawn_time(self):
        return self.flow.is_passenger_spawn_time(self)

    def spawn_passengers(self):
        return self.flow.spawn_passengers(
            self,
            get_passenger_factory=lambda: self.passenger_factory,
            get_shape_factory=lambda: self.shape_factory,
            get_passenger_color=lambda: self.passenger_color,
            get_passenger_size=lambda: self.passenger_size,
        )

    def get_path_by_id(self, path_id):
        return next((path for path in self.paths if path.id == path_id), None)

    def get_travel_plan_starting_with_path(
        self, passenger, station, required_path, node_map
    ):
        return None

    def get_boarding_candidates_for_metro(
        self, metro, station, node_map, mutate_travel_plans
    ):
        return self.flow.get_boarding_candidates_for_metro(
            self,
            metro,
            station,
            node_map,
            mutate_travel_plans,
            get_boarding_iterator=lambda: self.boarding_iterator,
        )

    def get_unloading_candidates_for_metro(self, metro, station):
        return self.flow.get_unloading_candidates_for_metro(self, metro, station)

    def get_next_station_for_metro(self, metro):
        return self.flow.get_next_station_for_metro(self, metro)

    def should_stop_at_next_station(self, metro, node_map):
        return self.flow.should_stop_at_next_station(self, metro, node_map)

    def start_station_stop_if_needed(self, metro, station, node_map):
        return self.flow.start_station_stop_if_needed(self, metro, station, node_map)

    def can_board_at_station(self, metro, station):
        return self.flow.can_board_at_station(self, metro, station)

    def find_next_path_for_passenger_at_station(self, passenger, station):
        self.events.append(("next-path", passenger.name, station.name))
        self.travel_plans[passenger].next_path = None

    def update_unlocked_num_paths(self):
        self.events.append(("unlock-paths",))

    def update_unlocked_num_stations(self):
        self.events.append(("unlock-stations",))

    def find_travel_plan_for_passengers(self):
        return self.flow.find_travel_plan_for_passengers(
            self,
            get_graph_builder=lambda: self.graph_builder,
            get_bulk_iterator=lambda: self.bulk_iterator,
            get_search=lambda: self.search,
            get_plan_factory=lambda: self.plan_factory,
        )

    def move_passengers(self, dt_ms):
        return self.flow.move_passengers(
            self,
            dt_ms,
            get_graph_builder=lambda: self.graph_builder,
            get_record_delivery=lambda: self.record_delivery,
        )

    def update_waiting_and_game_over(self, dt_ms):
        return self.flow.update_waiting_and_game_over(self, dt_ms)


def assert_component_boundary(test_case, flow, component_type):
    test_case.assertEqual(component_type.__slots__, ())
    test_case.assertFalse(hasattr(flow, "__dict__"))
    with test_case.assertRaises(AttributeError):
        flow.host = object()

    host = FakeHost(flow)
    station = FakeStation("station", "circle", host.events)
    metro = FakeMetro("metro", host.events)
    host.paths = [FakePath("path", host.events)]

    def iterator(*args, **kwargs):
        return iter(())

    def iterator_getter(value=iterator):
        return value

    iterator_ref = weakref.ref(iterator)
    flow.get_boarding_candidates_for_metro(
        host,
        metro,
        station,
        {},
        False,
        get_boarding_iterator=iterator_getter,
    )
    del iterator_getter
    del iterator
    host_ref = weakref.ref(host)
    del host
    gc.collect()
    test_case.assertIsNone(iterator_ref())
    test_case.assertIsNone(host_ref())
    assert_import_isolated(test_case)


def assert_station_service_action(test_case, metro, expected_kind, expected_passenger):
    action = metro._station_service_action
    test_case.assertIsInstance(action, tuple)
    test_case.assertEqual(len(action), 2)
    action_kind, action_passenger = action
    normalized_kind = str(getattr(action_kind, "value", action_kind)).lower()
    test_case.assertIn(expected_kind, normalized_kind)
    test_case.assertIs(action_passenger, expected_passenger)
