from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime_tree_sha256(source_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def label(labels: dict[int, str], value: object) -> str | None:
    if value is None:
        return None
    key = id(value)
    if key not in labels:
        labels[key] = f"{type(value).__name__.lower()}-{len(labels)}"
    return labels[key]


def record(
    env: Any,
    name: str,
    outcome: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    from recursive_checkpoint import canonical_checkpoint

    observation = env.observe()
    checkpoint = canonical_checkpoint(env, observation)
    return {
        "checkpoint": checkpoint,
        "eventCursor": len(events),
        "label": name,
        "observation": checkpoint["structured"],
        "outcome": outcome,
        "rng": checkpoint["rng"],
    }


def rider_state(host: Any, rider: Any, labels: dict[int, str]) -> dict[str, Any]:
    plan = host.travel_plans.get(rider)
    plan_state = None
    if plan is not None:
        plan_state = {
            "nextPath": label(labels, plan.next_path),
            "nextStation": label(labels, plan.next_station),
            "nodePath": [label(labels, node.station) for node in plan.node_path],
        }
    return {
        "arrived": rider.is_at_destination,
        "global": rider in host.passengers,
        "metros": [
            label(labels, item) for item in host.metros if rider in item.passengers
        ],
        "plan": plan_state,
        "stations": [
            label(labels, item) for item in host.stations if rider in item.passengers
        ],
        "waitMs": rider.wait_ms,
    }


class RebindingCallable:
    def __init__(
        self,
        name: str,
        events: list[dict],
        owner: object,
        attribute: str,
        replacement: object,
        delegate: Any,
    ):
        self.name = name
        self.events = events
        self.owner = owner
        self.attribute = attribute
        self.replacement = replacement
        self.delegate = delegate

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.events.append({"event": "callable.call", "name": self.name})
        setattr(self.owner, self.attribute, self.replacement)
        return self.delegate(*args, **kwargs)

    def __del__(self) -> None:
        self.events.append({"event": "callable.release", "name": self.name})


class TaggedGraph(dict):
    def __init__(self, values: dict, phase: str):
        super().__init__(values)
        self.phase = phase


def graph_phase(graph: object) -> str:
    return str(getattr(graph, "phase", "untagged"))


def builder_chain(module: Any, original: Any, events: list[dict]) -> Any:
    phases = ("pre-move", "planning", "exchange")

    def unexpected(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("a tick built more than three station graphs")

    def make(index: int) -> Any:
        replacement = unexpected if index == len(phases) - 1 else make(index + 1)

        def build(stations: Any, paths: Any) -> TaggedGraph:
            phase = phases[index]
            events.append({"event": "graph.build", "phase": phase})
            setattr(module, "build_station_nodes_dict", replacement)
            return TaggedGraph(original(stations, paths), phase)

        return build

    return make(0)


class Destinations:
    def __init__(self, name: str, values: list[Any], events: list[dict]):
        self.name = name
        self.values = values
        self.events = events

    def __iter__(self) -> Any:
        return iter(self.values)

    def __del__(self) -> None:
        self.events.append({"event": "destinations.release", "rider": self.name})


class RouterTrace:
    def __init__(
        self, delegate: Any, host: Any, events: list[dict], labels: dict[int, str]
    ):
        self.delegate = delegate
        self.host = host
        self.events = events
        self.labels = labels

    def __getattr__(self, name: str) -> Any:
        return getattr(self.delegate, name)

    @property
    def iter_boarding_candidates(self) -> Any:
        self.events.append({"event": "router.resolve", "iterator": "boarding"})
        return self.delegate.iter_boarding_candidates

    @property
    def iter_bulk_route_proposals(self) -> Any:
        self.events.append({"event": "router.resolve", "iterator": "bulk"})
        return self._iter_bulk_route_proposals

    def _iter_bulk_route_proposals(self, *args: Any, **kwargs: Any) -> Any:
        self.events.append(
            {
                "event": "router.enter",
                "graph": graph_phase(kwargs["node_map"]),
                "iterator": "bulk",
            }
        )
        iterator = self.delegate.iter_bulk_route_proposals(*args, **kwargs)
        try:
            while True:
                self.events.append({"event": "router.resume", "iterator": "bulk"})
                try:
                    proposal = next(iterator)
                except StopIteration:
                    break
                _station, rider, route, kind = proposal
                rider_label = label(self.labels, rider)
                self.events.append(
                    {
                        "event": "proposal.yield",
                        "kind": kind,
                        "rider": rider_label,
                        "routeLength": None if route is None else len(route),
                    }
                )
                yield proposal
                self.events.append(
                    {
                        "event": "proposal.effect",
                        "kind": kind,
                        "rider": rider_label,
                        "state": rider_state(self.host, rider, self.labels),
                    }
                )
        finally:
            iterator.close()
            self.events.append({"event": "router.finalize", "iterator": "bulk"})


def station(shape_type: Any, x: int) -> Any:
    from config import station_color, station_size
    from entity.station import Station
    from geometry.point import Point
    from utils import get_shape_from_type

    return Station(
        get_shape_from_type(shape_type, station_color, station_size), Point(x, 0)
    )


def trace_graph_consumer(
    host: Any,
    name: str,
    graph_index: int,
    events: list[dict],
) -> None:
    original = getattr(host, name)

    def traced(*args: Any, **kwargs: Any) -> Any:
        event = {
            "event": "graph.consume",
            "method": name,
            "phase": graph_phase(args[graph_index]),
        }
        if name == "get_boarding_candidates_for_metro":
            event["mutate"] = kwargs.get(
                "mutate_travel_plans", args[3] if len(args) > 3 else None
            )
        events.append(event)
        return original(*args, **kwargs)

    setattr(host, name, traced)


def tick_case() -> dict[str, Any]:
    import mediator as mediator_module
    from entity.metro import Metro
    from entity.passenger import Passenger
    from entity.path import Path
    from env import MiniMetroEnv
    from geometry.type import ShapeType
    from graph.node import Node
    from travel_plan import TravelPlan

    env = MiniMetroEnv()
    env.reset(seed=311)
    host = env.mediator
    events: list[dict[str, Any]] = []
    labels: dict[int, str] = {}
    source = station(ShapeType.RECT, 0)
    reachable = station(ShapeType.CIRCLE, 1000)
    isolated = station(ShapeType.TRIANGLE, 2000)
    host.all_stations = host.stations = [source, reachable, isolated]
    for name, value in (
        ("station-source", source),
        ("station-reachable", reachable),
        ("station-isolated", isolated),
    ):
        labels[id(value)] = name

    path = Path((10, 20, 30))
    path.add_station(source)
    path.add_station(reachable)
    metro = Metro()
    path.add_metro(metro)
    metro.current_station = source
    host.paths = [path]
    host.metros = [metro]
    labels[id(path)] = "path-main"
    labels[id(metro)] = "metro-main"
    riders = {
        "deliver-1": Passenger(source.shape),
        "deliver-2": Passenger(source.shape),
        "transfer": Passenger(reachable.shape),
        "board": Passenger(reachable.shape),
        "overdue-1": Passenger(source.shape),
        "overdue-2": Passenger(source.shape),
    }
    for name, rider in riders.items():
        labels[id(rider)] = name
        host.passengers.append(rider)
    for name in ("deliver-1", "deliver-2", "transfer"):
        metro.add_passenger(riders[name])
    source.add_passenger(riders["board"])
    isolated.add_passenger(riders["overdue-1"])
    isolated.add_passenger(riders["overdue-2"])
    host.travel_plans[riders["deliver-1"]] = TravelPlan([Node(source)])
    host.travel_plans[riders["deliver-2"]] = TravelPlan([Node(source)])
    host.travel_plans[riders["transfer"]] = TravelPlan([Node(source), Node(reachable)])
    host.travel_plans[riders["board"]] = TravelPlan([Node(reachable)])
    host.travel_plans[riders["board"]].next_path = path
    for name in ("overdue-1", "overdue-2"):
        riders[name].wait_ms = 1000
    host.passenger_max_wait_time_ms = 3000
    host.overdue_passenger_threshold = 2
    host.station_spawn_interval_steps.clear()
    host.station_steps_since_last_spawn.clear()
    host._router = RouterTrace(host._router, host, events, labels)
    for name, graph_index in (
        ("start_station_stop_if_needed", 2),
        ("should_stop_at_next_station", 1),
        ("get_boarding_candidates_for_metro", 2),
    ):
        trace_graph_consumer(host, name, graph_index, events)

    original_transfer = metro.move_passenger

    def transfer(rider: Any, destination: Any) -> None:
        events.append({"event": "exchange.transfer", "rider": label(labels, rider)})
        original_transfer(rider, destination)

    metro.move_passenger = transfer
    original_board = source.move_passenger

    def board(rider: Any, destination: Any) -> None:
        events.append({"event": "exchange.board", "rider": label(labels, rider)})
        original_board(rider, destination)

    source.move_passenger = board
    original_delivery = host._progression.record_delivery
    host._progression.record_delivery = RebindingCallable(
        "delivery-1",
        events,
        host._progression,
        "record_delivery",
        RebindingCallable(
            "delivery-2",
            events,
            host._progression,
            "record_delivery",
            original_delivery,
            original_delivery,
        ),
        original_delivery,
    )
    original_builder = mediator_module.build_station_nodes_dict
    mediator_module.build_station_nodes_dict = builder_chain(
        mediator_module, original_builder, events
    )
    records = [record(env, "tick-prepared", {}, events)]
    try:
        host.set_paused(True)
        paused_observation, reward, done, info = env.step({"type": "noop"}, dt_ms=37)
        records.append(
            record(
                env,
                "tick-paused",
                {
                    "actionOk": info["action_ok"],
                    "done": done,
                    "reward": reward,
                    "structuredStable": paused_observation["structured"]
                    == env.observe()["structured"],
                },
                events,
            )
        )
        host.set_paused(False)
        host.set_game_speed(2)
        _observation, reward, done, info = env.step({"type": "noop"}, dt_ms=1000)
        records.append(
            record(
                env,
                "tick-active",
                {
                    "actionOk": info["action_ok"],
                    "deliveries": host.deliveries,
                    "done": done,
                    "knownRiders": {
                        name: rider_state(host, rider, labels)
                        for name, rider in riders.items()
                    },
                    "reward": reward,
                    "spawnedCount": len(host.passengers) - 4,
                },
                events,
            )
        )
    finally:
        mediator_module.build_station_nodes_dict = original_builder

    graph_builds = [
        event["phase"] for event in events if event["event"] == "graph.build"
    ]
    exchange_order = [
        event["event"]
        for event in events
        if event["event"] in {"callable.call", "exchange.transfer", "exchange.board"}
    ]
    if graph_builds != ["pre-move", "planning", "exchange"]:
        raise AssertionError("the active tick did not preserve three graph phases")
    if exchange_order != [
        "callable.call",
        "callable.call",
        "exchange.transfer",
        "exchange.board",
    ]:
        raise AssertionError("passenger exchange priority changed")
    if not done or reward != 2 or host.deliveries != 2:
        raise AssertionError("delivery reward or terminal waiting behavior changed")
    return {"events": events, "name": "seeded-tick", "records": records}
