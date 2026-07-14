from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, MutableSequence
from typing import Any, Literal

RouteProposalKind = Literal["arrival", "route", "fallback"]


class RoutePlanner:
    """Stateless route queries and lazy planning proposal iterators."""

    __slots__ = ()

    def get_stations_for_shape_type(
        self, stations: Iterable[Any], shape_type: object
    ) -> list[Any]:
        return [station for station in stations if station.shape.type == shape_type]

    def find_shared_path(
        self, paths: Iterable[Any], station_a: Any, station_b: Any
    ) -> Any | None:
        for path in paths:
            stations = path.stations
            if station_a in stations and station_b in stations:
                return path
        return None

    def passenger_has_travel_plan(
        self,
        *,
        contains_travel_plan: Callable[[], bool],
        get_travel_plan: Callable[[], Any],
    ) -> bool:
        return contains_travel_plan() and get_travel_plan().next_path is not None

    def get_path_by_id(self, paths: Iterable[Any], path_id: str) -> Any | None:
        for path in paths:
            if path.id == path_id:
                return path
        return None

    def skip_stations_on_same_path(
        self, node_path: MutableSequence[Any]
    ) -> MutableSequence[Any]:
        assert len(node_path) >= 2
        if len(node_path) == 2:
            return node_path

        nodes_to_remove: list[Any] = []
        path_set_list = [node.paths for node in node_path]
        path_set_list.append(set())
        i = 0
        j = 1
        while j <= len(path_set_list) - 1:
            set_a = path_set_list[i]
            set_b = path_set_list[j]
            if set_a & set_b:
                j += 1
            else:
                for k in range(i + 1, j - 1):
                    nodes_to_remove.append(node_path[k])
                i = j - 1
                j += 1
        for node in nodes_to_remove:
            node_path.remove(node)
        return node_path

    def find_best_node_path(
        self,
        start_station: Any,
        destination_stations: Iterable[Any],
        node_map: Mapping[Any, Any],
        *,
        find_node_path: Callable[[Any, Any], list[Any]],
        get_reduce_node_path: Callable[[], Callable[[list[Any]], list[Any]]],
    ) -> list[Any] | None:
        selections = self._iter_best_node_path_selections(
            start_station,
            destination_stations,
            node_map,
            find_node_path=find_node_path,
            get_reduce_node_path=get_reduce_node_path,
        )
        try:
            node_path, _arrived = next(selections)
            return node_path
        finally:
            selections.close()

    def _iter_best_node_path_selections(
        self,
        start_station: Any,
        destination_stations: Iterable[Any],
        node_map: Mapping[Any, Any],
        *,
        find_node_path: Callable[[Any, Any], list[Any]],
        get_reduce_node_path: Callable[[], Callable[[list[Any]], list[Any]]],
    ) -> Iterator[tuple[list[Any] | None, bool]]:
        best_node_path: list[Any] | None = None
        best_path_cost: tuple[int, int] | None = None
        for destination_station in destination_stations:
            start = node_map[start_station]
            end = node_map[destination_station]
            node_path = find_node_path(start, end)
            if len(node_path) == 1:
                yield node_path, True
                return
            if len(node_path) > 1:
                reduced_node_path = get_reduce_node_path()(list(node_path))
                candidate_cost = (len(node_path), len(reduced_node_path))
                if best_path_cost is None or candidate_cost < best_path_cost:
                    best_path_cost = candidate_cost
                    best_node_path = reduced_node_path
        yield best_node_path, False

    def get_travel_plan_starting_with_path(
        self,
        start_station: Any,
        destination_stations: Iterable[Any],
        node_map: Mapping[Any, Any],
        *,
        get_required_first_path_id: Callable[[], str],
        find_node_path: Callable[[Any, Any], list[Any]],
        get_reduce_node_path: Callable[[], Callable[[list[Any]], list[Any]]],
        get_find_shared_path: Callable[[], Callable[[Any, Any], Any | None]],
        get_plan_factory: Callable[[], Callable[[list[Any]], Any]],
    ) -> Any | None:
        best_node_path: list[Any] | None = None
        best_path_cost: tuple[int, int] | None = None
        start = node_map[start_station]
        for destination_station in destination_stations:
            end = node_map[destination_station]
            node_path = find_node_path(start, end)
            if len(node_path) <= 1:
                continue
            reduced_node_path = get_reduce_node_path()(list(node_path))
            if len(reduced_node_path) <= 1:
                continue
            first_hop_path = get_find_shared_path()(
                start_station, reduced_node_path[1].station
            )
            if (
                first_hop_path is None
                or first_hop_path.id != get_required_first_path_id()
            ):
                continue
            candidate_cost = (len(node_path), len(reduced_node_path))
            if best_path_cost is None or candidate_cost < best_path_cost:
                best_path_cost = candidate_cost
                best_node_path = reduced_node_path

        if best_node_path is None:
            return None
        travel_plan = get_plan_factory()(best_node_path[1:])
        next_station = travel_plan.get_next_station()
        if next_station is None:
            return None
        travel_plan.next_path = get_find_shared_path()(start_station, next_station)
        return travel_plan

    def update_next_path_for_plan(
        self,
        station: Any,
        *,
        get_plan: Callable[[], Any],
        find_shared_path: Callable[[Any, Any], Any | None],
    ) -> None:
        next_station = get_plan().get_next_station()
        assert next_station is not None
        next_path = find_shared_path(station, next_station)
        get_plan().next_path = next_path
        if next_path is None:
            get_plan().next_station = None

    def iter_boarding_candidates(
        self,
        passengers: Iterable[Any],
        *,
        get_required_path_id: Callable[[], str],
        get_current_plan: Callable[[Any], Any | None],
        get_constrained_plan: Callable[[Any], Any | None],
    ) -> Iterator[tuple[Any, Any | None]]:
        for passenger in passengers:
            current_plan = get_current_plan(passenger)
            if (
                current_plan
                and current_plan.next_path
                and current_plan.next_path.id == get_required_path_id()
            ):
                yield passenger, None
                continue
            proposed_plan = get_constrained_plan(passenger)
            if proposed_plan is not None:
                yield passenger, proposed_plan

    def iter_bulk_route_proposals(
        self,
        stations: Iterable[Any],
        *,
        has_travel_plan: Callable[[Any], bool],
        get_destination_stations: Callable[[Any], Iterable[Any]],
        node_map: Mapping[Any, Any],
        find_node_path: Callable[[Any, Any], list[Any]],
        get_reduce_node_path: Callable[[], Callable[[list[Any]], list[Any]]],
    ) -> Iterator[tuple[Any, Any, list[Any] | None, RouteProposalKind]]:
        for station in stations:
            for passenger in station.passengers:
                if has_travel_plan(passenger):
                    continue
                destination_stations = get_destination_stations(passenger)
                best_node_path: list[Any] | None = None
                best_path_cost: tuple[int, int] | None = None
                for destination_station in destination_stations:
                    start = node_map[station]
                    end = node_map[destination_station]
                    node_path = find_node_path(start, end)
                    if len(node_path) == 1:
                        yield station, passenger, node_path, "arrival"
                        best_node_path = None
                        break
                    elif len(node_path) > 1:
                        reduced_node_path = get_reduce_node_path()(list(node_path))
                        candidate_cost = (len(node_path), len(reduced_node_path))
                        if best_path_cost is None or candidate_cost < best_path_cost:
                            best_path_cost = candidate_cost
                            best_node_path = reduced_node_path

                if best_node_path is not None:
                    yield station, passenger, best_node_path, "route"
                else:
                    yield station, passenger, None, "fallback"
