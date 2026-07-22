from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from passenger_capacity import (
    BOARD,
    DESTINATION,
    TRANSFER,
    drain_queued_returns,
    next_service_action,
    pure_service_action,
    reconcile_service_action,
    same_service_action,
)

Resolver = Callable[[], Any]


class PassengerFlowHost(Protocol):
    """Mutable facade surface used only for one passenger-flow transition."""

    context: Any
    stations: list[Any]
    paths: list[Any]
    metros: list[Any]
    passengers: list[Any]
    travel_plans: dict[Any, Any]
    station_spawn_interval_steps: dict[Any, int]
    station_steps_since_last_spawn: dict[Any, int]
    passenger_spawning_interval_step: int
    passenger_spawning_step: int
    passenger_max_wait_time_ms: int
    overdue_passenger_threshold: int
    steps: int
    time_ms: int
    is_paused: bool
    is_game_over: bool
    game_speed_multiplier: int

    get_station_shape_types: Callable[[], list[Any]]
    is_passenger_spawn_time: Callable[[], bool]
    initialize_station_spawning_state: Callable[[list[Any]], None]
    get_station_spawn_interval_step: Callable[[], int]
    should_spawn_passenger_at_station: Callable[[Any], bool]
    spawn_passengers: Callable[[], None]
    get_next_station_for_metro: Callable[[Any], Any | None]
    get_boarding_candidates_for_metro: Callable[..., list[Any]]
    get_unloading_candidates_for_metro: Callable[..., tuple[list[Any], list[Any]]]
    should_stop_at_next_station: Callable[..., bool]
    start_station_stop_if_needed: Callable[..., None]
    can_board_at_station: Callable[[Any, Any], bool]
    find_travel_plan_for_passengers: Callable[[], None]
    move_passengers: Callable[[int], None]
    update_waiting_and_game_over: Callable[[int], None]
    get_path_by_id: Callable[[str], Any | None]
    get_travel_plan_starting_with_path: Callable[..., Any | None]
    passenger_has_travel_plan: Callable[[Any], bool]
    get_stations_for_shape_type: Callable[[Any], list[Any]]
    skip_stations_on_same_path: Callable[[list[Any]], list[Any]]
    find_next_path_for_passenger_at_station: Callable[[Any, Any], None]
    update_unlocked_num_paths: Callable[[], None]
    update_unlocked_num_stations: Callable[[], None]


class PassengerFlow:
    """Stateless passenger and simulation algorithms over canonical facade state."""

    __slots__ = ()

    def get_station_shape_types(self, host: PassengerFlowHost) -> list[Any]:
        return list(dict.fromkeys(station.shape.type for station in host.stations))

    def is_passenger_spawn_time(self, host: PassengerFlowHost) -> bool:
        return any(
            host.should_spawn_passenger_at_station(station) for station in host.stations
        )

    def initialize_station_spawning_state(
        self, host: PassengerFlowHost, stations: list[Any]
    ) -> None:
        for station in stations:
            if station not in host.station_spawn_interval_steps:
                host.station_spawn_interval_steps[station] = (
                    host.get_station_spawn_interval_step()
                )
            if station not in host.station_steps_since_last_spawn:
                host.station_steps_since_last_spawn[station] = (
                    host.station_spawn_interval_steps[station]
                )

    def get_station_spawn_interval_step(self, host: PassengerFlowHost) -> int:
        min_interval = max(1, int(host.passenger_spawning_interval_step * 0.7))
        max_interval = max(
            min_interval, int(host.passenger_spawning_interval_step * 1.3)
        )
        return host.context.python_random.randint(min_interval, max_interval)

    def should_spawn_passenger_at_station(
        self, host: PassengerFlowHost, station: Any
    ) -> bool:
        host.initialize_station_spawning_state([station])
        return (
            host.steps == host.passenger_spawning_step
            or host.station_steps_since_last_spawn[station]
            >= host.station_spawn_interval_steps[station]
        )

    def spawn_passengers(
        self,
        host: PassengerFlowHost,
        *,
        get_passenger_factory: Resolver,
        get_shape_factory: Resolver,
        get_passenger_color: Resolver,
        get_passenger_size: Resolver,
    ) -> None:
        station_types = host.get_station_shape_types()
        for station in host.stations:
            if not host.should_spawn_passenger_at_station(station):
                continue
            other_station_shape_types = [
                shape_type
                for shape_type in station_types
                if shape_type != station.shape.type
            ]
            destination_shape_type = host.context.python_random.choice(
                other_station_shape_types
            )
            destination_shape = get_shape_factory()(
                destination_shape_type,
                get_passenger_color(),
                get_passenger_size(),
            )
            passenger = get_passenger_factory()(destination_shape)
            if station.has_room():
                station.add_passenger(passenger)
                host.passengers.append(passenger)
            host.station_steps_since_last_spawn[station] = 0

    def increment_time(
        self,
        host: PassengerFlowHost,
        dt_ms: int,
        *,
        get_graph_builder: Resolver,
    ) -> None:
        if host.is_paused or host.is_game_over:
            return

        speed_multiplier = host.game_speed_multiplier
        scaled_dt_ms = dt_ms * speed_multiplier

        host.time_ms += scaled_dt_ms
        host.steps += speed_multiplier
        host.initialize_station_spawning_state(host.stations)
        for station in host.stations:
            host.station_steps_since_last_spawn[station] += speed_multiplier
            station.prune_visual_effects(host.time_ms)

        station_nodes_dict = get_graph_builder()(host.stations, host.paths)
        for path in host.paths:
            for metro in path.metros:
                if (
                    metro.current_station is not None
                    and metro.stop_time_remaining_ms <= 0
                ):
                    host.start_station_stop_if_needed(
                        metro,
                        metro.current_station,
                        station_nodes_dict,
                    )
                should_stop_at_next_station = host.should_stop_at_next_station(
                    metro, station_nodes_dict
                )
                path.move_metro(
                    metro,
                    scaled_dt_ms,
                    should_stop_at_next_station=should_stop_at_next_station,
                )
                if metro.just_arrived_and_stopped and metro.current_station is not None:
                    host.start_station_stop_if_needed(
                        metro,
                        metro.current_station,
                        station_nodes_dict,
                    )

        if host.is_passenger_spawn_time():
            host.spawn_passengers()

        host.find_travel_plan_for_passengers()
        host.move_passengers(scaled_dt_ms)
        host.update_waiting_and_game_over(scaled_dt_ms)

    def get_next_station_for_metro(
        self, host: PassengerFlowHost, metro: Any
    ) -> Any | None:
        assert metro.current_segment is not None
        if metro.is_forward:
            return metro.current_segment.end_station
        return metro.current_segment.start_station

    def get_boarding_candidates_for_metro(
        self,
        host: PassengerFlowHost,
        metro: Any,
        station: Any,
        station_nodes_dict: dict[Any, Any],
        mutate_travel_plans: bool,
        *,
        get_boarding_iterator: Resolver,
    ) -> list[Any]:
        metro_path = host.get_path_by_id(metro.path_id)
        if metro_path is None:
            return []

        candidates: list[Any] = []
        for passenger, travel_plan in get_boarding_iterator()(
            station.passengers,
            get_required_path_id=lambda: metro.path_id,
            get_current_plan=lambda item: host.travel_plans.get(item),
            get_constrained_plan=lambda item: host.get_travel_plan_starting_with_path(
                item, station, metro_path, station_nodes_dict
            ),
        ):
            if travel_plan is not None and mutate_travel_plans:
                host.travel_plans[passenger] = travel_plan
            candidates.append(passenger)
        return candidates

    def get_unloading_candidates_for_metro(
        self, host: PassengerFlowHost, metro: Any, station: Any
    ) -> tuple[list[Any], list[Any]]:
        passengers_to_destination: list[Any] = []
        passengers_to_transfer: list[Any] = []
        for passenger in metro.passengers:
            if station.shape.type == passenger.destination_shape.type:
                passengers_to_destination.append(passenger)
                continue
            travel_plan = host.travel_plans.get(passenger)
            if travel_plan is not None and travel_plan.get_next_station() == station:
                passengers_to_transfer.append(passenger)
        return passengers_to_destination, passengers_to_transfer

    def should_stop_at_next_station(
        self,
        host: PassengerFlowHost,
        metro: Any,
        station_nodes_dict: dict[Any, Any],
    ) -> bool:
        if metro.current_segment is None:
            return False
        destination_station = host.get_next_station_for_metro(metro)
        if destination_station is None:
            return False
        return (
            pure_service_action(
                host,
                metro,
                destination_station,
                station_nodes_dict,
            )
            is not None
        )

    def start_station_stop_if_needed(
        self,
        host: PassengerFlowHost,
        metro: Any,
        station: Any,
        station_nodes_dict: dict[Any, Any],
    ) -> None:
        reconcile_service_action(host, metro, station, station_nodes_dict)

    def drain_queued_returns(
        self,
        host: PassengerFlowHost,
        *,
        get_graph_builder: Resolver,
    ) -> None:
        drain_queued_returns(
            host,
            build_graph=lambda: get_graph_builder()(host.stations, host.paths),
        )

    def reconcile_station_service(
        self,
        host: PassengerFlowHost,
        metro: Any,
        *,
        get_graph_builder: Resolver,
    ) -> None:
        station = getattr(metro, "current_station", None)
        if station is None:
            return
        station_nodes_dict = get_graph_builder()(host.stations, host.paths)
        reconcile_service_action(host, metro, station, station_nodes_dict)

    def can_board_at_station(
        self, host: PassengerFlowHost, metro: Any, station: Any
    ) -> bool:
        if metro.has_room():
            return True
        for passenger in metro.passengers:
            if station.shape.type == passenger.destination_shape.type:
                return True
            travel_plan = host.travel_plans.get(passenger)
            if travel_plan is not None and travel_plan.get_next_station() == station:
                return True
        return False

    def move_passengers(
        self,
        host: PassengerFlowHost,
        dt_ms: int,
        *,
        get_graph_builder: Resolver,
        get_record_delivery: Resolver,
        get_scoped_replanner: Resolver | None = None,
    ) -> None:
        station_nodes_dict = get_graph_builder()(host.stations, host.paths)
        for metro in host.metros:
            station = metro.current_station
            if station is None:
                continue
            remaining = max(0, dt_ms)
            while True:
                action = reconcile_service_action(
                    host, metro, station, station_nodes_dict
                )
                if action is None:
                    break
                interval = metro.boarding_time_per_passenger_ms
                needed = interval - metro.boarding_progress_ms
                consumed = min(remaining, needed)
                metro.boarding_progress_ms += consumed
                metro.stop_time_remaining_ms = interval - metro.boarding_progress_ms
                remaining -= consumed
                if metro.boarding_progress_ms < interval:
                    break
                try:
                    executed = self._execute_station_service_action(
                        host,
                        metro,
                        station,
                        station_nodes_dict,
                        action,
                        get_record_delivery=get_record_delivery,
                        get_scoped_replanner=get_scoped_replanner,
                    )
                except BaseException:
                    metro._station_service_action = None
                    metro.stop_time_remaining_ms = 0
                    metro.boarding_progress_ms = 0
                    raise
                metro._station_service_action = None
                metro.stop_time_remaining_ms = 0
                metro.boarding_progress_ms = 0
                if not executed or remaining <= 0:
                    reconcile_service_action(host, metro, station, station_nodes_dict)
                    break

    def _execute_station_service_action(
        self,
        host: PassengerFlowHost,
        metro: Any,
        station: Any,
        station_nodes_dict: dict[Any, Any],
        expected: tuple[str, Any],
        *,
        get_record_delivery: Resolver,
        get_scoped_replanner: Resolver | None,
    ) -> bool:
        action = next_service_action(
            host,
            metro,
            station,
            station_nodes_dict,
            mutate_travel_plans=True,
        )
        if not same_service_action(action, expected):
            return False
        kind, passenger = expected
        if kind == DESTINATION:
            passenger.is_at_destination = True
            metro.remove_passenger(passenger)
            host.passengers.remove(passenger)
            if passenger in host.travel_plans:
                del host.travel_plans[passenger]
            get_record_delivery()()
            host.update_unlocked_num_paths()
            host.update_unlocked_num_stations()
            return True
        if kind == TRANSFER:
            if not station.has_room():
                return False
            metro.move_passenger(passenger, station)
            passenger.wait_ms = 0
            travel_plan = host.travel_plans.get(passenger)
            if travel_plan is not None:
                travel_plan.increment_next_station()
                next_station_idx = getattr(travel_plan, "next_station_idx", None)
                if (
                    get_scoped_replanner is not None
                    and type(next_station_idx) is int
                    and next_station_idx >= len(travel_plan.node_path)
                ):
                    travel_plan.next_path = None
                    travel_plan.next_station = None
                    travel_plan.node_path.clear()
                    travel_plan.next_station_idx = 0
                    get_scoped_replanner()(passenger, station, station_nodes_dict)
                else:
                    host.find_next_path_for_passenger_at_station(passenger, station)
            return True
        if kind == BOARD and metro.has_room():
            station.move_passenger(passenger, metro)
            passenger.wait_ms = 0
            return True
        return False

    def replan_passenger_at_station(
        self,
        host: PassengerFlowHost,
        passenger: Any,
        station: Any,
        station_nodes_dict: dict[Any, Any],
        *,
        get_best_path_finder: Resolver,
        get_search: Resolver,
        get_plan_factory: Resolver,
    ) -> None:
        node_path = get_best_path_finder()(
            station,
            host.get_stations_for_shape_type(passenger.destination_shape.type),
            station_nodes_dict,
            find_node_path=lambda start, end: get_search()(start, end),
            get_reduce_node_path=lambda: host.skip_stations_on_same_path,
        )
        if node_path is not None and len(node_path) == 1:
            station.remove_passenger(passenger)
            host.passengers.remove(passenger)
            passenger.is_at_destination = True
            host.travel_plans.pop(passenger, None)
        elif node_path:
            host.travel_plans[passenger] = get_plan_factory()(node_path[1:])
            host.find_next_path_for_passenger_at_station(passenger, station)
        else:
            host.travel_plans[passenger] = get_plan_factory()([])

    def update_waiting_and_game_over(self, host: PassengerFlowHost, dt_ms: int) -> None:
        if host.is_game_over:
            return

        waiting_over_limit = 0
        for station in host.stations:
            for passenger in station.passengers:
                passenger.wait_ms += dt_ms
                if passenger.wait_ms >= host.passenger_max_wait_time_ms:
                    waiting_over_limit += 1

        if waiting_over_limit >= host.overdue_passenger_threshold:
            host.is_game_over = True

    def find_travel_plan_for_passengers(
        self,
        host: PassengerFlowHost,
        *,
        get_graph_builder: Resolver,
        get_bulk_iterator: Resolver,
        get_search: Resolver,
        get_plan_factory: Resolver,
    ) -> None:
        station_nodes_dict = get_graph_builder()(host.stations, host.paths)
        for station, rider, route, kind in get_bulk_iterator()(
            host.stations,
            has_travel_plan=lambda item: host.passenger_has_travel_plan(item),
            get_destination_stations=lambda item: host.get_stations_for_shape_type(
                item.destination_shape.type
            ),
            node_map=station_nodes_dict,
            find_node_path=lambda start, end: get_search()(start, end),
            get_reduce_node_path=lambda: host.skip_stations_on_same_path,
        ):
            if kind == "arrival":
                station.remove_passenger(rider)
                host.passengers.remove(rider)
                rider.is_at_destination = True
                del host.travel_plans[rider]
            elif kind == "route":
                host.travel_plans[rider] = get_plan_factory()(route[1:])
                host.find_next_path_for_passenger_at_station(rider, station)
            elif not rider.is_at_destination and rider not in host.travel_plans:
                host.travel_plans[rider] = get_plan_factory()([])
