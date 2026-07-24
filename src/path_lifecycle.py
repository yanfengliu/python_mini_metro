from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from crossings import within_tunnel_budget
from path_removal_snapshot import restore_removal_state, snapshot_removal_state
from path_replacement import replace_path as replace_path_transaction

PathFactoryGetter = Callable[[], Callable[[Any], Any]]
Resolver = Callable[[], Any]


def _squared_distance(first: Any, second: Any) -> float:
    dx = first.left - second.left
    dy = first.top - second.top
    return dx * dx + dy * dy


def _nearest_endpoint_station(metro: Any, segment: Any) -> Any:
    position = getattr(metro, "position", None)
    start = getattr(segment, "segment_start", None)
    end = getattr(segment, "segment_end", None)
    if position is None or start is None or end is None:
        return segment.start_station
    if _squared_distance(position, start) <= _squared_distance(position, end):
        return segment.start_station
    return segment.end_station


def _padding_adjacent_station(
    path: Any, segments: list[Any], index: int, metro: Any
) -> Any | None:
    forward = getattr(metro, "is_forward", True) is not False
    looped = bool(getattr(path, "is_looped", False))
    count = len(segments)
    step = 1 if forward else -1
    cursor = index
    for _ in range(count):
        cursor += step
        if looped:
            cursor %= count
        elif not 0 <= cursor < count:
            break
        candidate = segments[cursor]
        start_station = getattr(candidate, "start_station", None)
        end_station = getattr(candidate, "end_station", None)
        if start_station is None or end_station is None:
            continue
        return start_station if forward else end_station
    return None


def _alight_station_for_metro(path: Any, metro: Any) -> Any | None:
    station = getattr(metro, "current_station", None)
    if station is not None:
        return station
    segment = getattr(metro, "current_segment", None)
    segments = getattr(path, "segments", None)
    if segment is None or not isinstance(segments, list) or not segments:
        return None
    index = getattr(metro, "current_segment_idx", None)
    if type(index) is not int or not (
        0 <= index < len(segments) and segments[index] is segment
    ):
        index = next(
            (idx for idx, candidate in enumerate(segments) if candidate is segment),
            None,
        )
        if index is None:
            return None
    if (
        getattr(segment, "start_station", None) is not None
        and getattr(segment, "end_station", None) is not None
    ):
        return _nearest_endpoint_station(metro, segment)
    return _padding_adjacent_station(path, segments, index, metro)


def _destination_matches(station: Any, rider: Any) -> bool:
    station_shape = getattr(getattr(station, "shape", None), "type", None)
    rider_shape = getattr(getattr(rider, "destination_shape", None), "type", None)
    return station_shape is not None and station_shape == rider_shape


def _credit_delivery(host: Any) -> None:
    record = getattr(getattr(host, "_progression", None), "record_delivery", None)
    if callable(record):
        record()
    for name in ("update_unlocked_num_paths", "update_unlocked_num_stations"):
        hook = getattr(host, name, None)
        if callable(hook):
            hook()


class PathLifecycleHost(Protocol):
    """Mutable facade surface used only for the duration of one transition."""

    path_buttons: list[Any]
    path_to_button: dict[Any, Any]
    paths: list[Any]
    metros: list[Any]
    passengers: list[Any]
    travel_plans: dict[Any, Any]
    path_colors: dict[Any, bool]
    path_to_color: dict[Any, Any]
    stations: list[Any]
    unlocked_num_paths: int
    time_ms: int
    is_creating_path: bool
    path_being_created: Any | None

    def update_path_button_lock_states(self) -> None: ...

    def find_travel_plan_for_passengers(self) -> None: ...

    def assign_paths_to_buttons(self) -> None: ...

    def remove_path(self, path: Any) -> None: ...

    def replace_path(
        self, path: Any, station_indices: list[int], loop: bool = False
    ) -> bool: ...

    def invalidate_travel_plans_for_path(self, path: Any) -> None: ...

    def release_color_for_path(self, path: Any) -> None: ...

    def start_path_on_station(self, station: Any) -> None: ...

    def add_station_to_path(self, station: Any) -> None: ...

    def abort_path_creation(self) -> None: ...

    def finish_path_creation(self) -> None: ...

    def end_path_on_station(self, station: Any) -> None: ...


class PathLifecycle:
    """Stateless path transition algorithms over canonical facade state."""

    __slots__ = ()

    def assign_paths_to_buttons(self, host: PathLifecycleHost) -> None:
        for path_button in host.path_buttons:
            path_button.remove_path()

        host.path_to_button = {}
        for path, button in zip(host.paths, host.path_buttons):
            button.assign_path(path)
            host.path_to_button[path] = button
        host.update_path_button_lock_states()

    def remove_path(
        self,
        host: PathLifecycleHost,
        path: Any,
        *,
        get_reconcile_station_service: Resolver | None = None,
    ) -> None:
        if hasattr(host, "num_carriages"):
            from fleet_management import _path_is_complete, _queue_state_is_canonical

            if not _path_is_complete(host, path) or not _queue_state_is_canonical(host):
                return
        state = snapshot_removal_state(host)
        try:
            # Riders alight before any collection mutation; only after every
            # rider is safe does the Metro leave the canonical global fleet.
            for metro in list(path.metros):
                self._alight_metro_riders(host, path, metro)
                if metro in host.metros:
                    host.metros.remove(metro)
                    if hasattr(metro, "_station_service_action"):
                        metro._station_service_action = None
                        metro.stop_time_remaining_ms = 0
                        metro.boarding_progress_ms = 0
            host.path_to_button[path].remove_path()
            host.invalidate_travel_plans_for_path(path)
            host.release_color_for_path(path)
            host.paths.remove(path)
            host.assign_paths_to_buttons()
            host.find_travel_plan_for_passengers()
            if get_reconcile_station_service is not None:
                self._reconcile_surviving_service(host, get_reconcile_station_service())
        except BaseException as error:
            traceback = error.__traceback__
            restore_removal_state(host, state)
            if not isinstance(error, Exception):
                raise error.with_traceback(traceback)

    @staticmethod
    def _reconcile_surviving_service(host: PathLifecycleHost, reconcile: Any) -> None:
        """Rebind surviving stopped Metros' caches after the conserving dump.

        The alights and replan sweep can change another line's stopped
        Metro's executable actions, so the removal transaction reconciles
        every surviving at-station Metro inside the snapshot scope.
        """

        from fleet_management import _real_station

        for surviving in host.paths:
            for metro in surviving.metros:
                if _real_station(surviving, metro):
                    reconcile(metro)

    @staticmethod
    def _alight_metro_riders(host: PathLifecycleHost, path: Any, metro: Any) -> None:
        """Conserve every onboard rider at a deterministic real station (D-024)."""

        station = _alight_station_for_metro(path, metro)
        riders = getattr(metro, "passengers", None)
        if not isinstance(riders, list):
            return
        if riders and station is None:
            # Refuse rather than silently drop: the removal transaction
            # restores the exact prior state when no station can host the
            # rider (unreachable through the canonically-gated facade).
            raise ValueError(
                "line removal could not resolve an alight station for a rider"
            )
        for rider in list(riders):
            riders.remove(rider)
            host.travel_plans.pop(rider, None)
            if _destination_matches(station, rider):
                rider.is_at_destination = True
                if rider in host.passengers:
                    host.passengers.remove(rider)
                _credit_delivery(host)
            else:
                # D-024 overflow-permitted placement bypasses the capacity
                # assert; ordinary spawn/boarding/transfer gates stay exact.
                station.passengers.append(rider)
                rider.wait_ms = 0

    def invalidate_travel_plans_for_path(
        self, host: PathLifecycleHost, path: Any
    ) -> None:
        onboard_passengers = {
            passenger for metro in host.metros for passenger in metro.passengers
        }
        for passenger, travel_plan in list(host.travel_plans.items()):
            if passenger in onboard_passengers and travel_plan.next_path != path:
                continue
            if travel_plan.next_path == path or any(
                path in node.paths for node in travel_plan.node_path
            ):
                del host.travel_plans[passenger]

    def remove_path_by_id(self, host: PathLifecycleHost, path_id: str) -> bool:
        for path in host.paths:
            if path.id == path_id:
                host.remove_path(path)
                return True
        return False

    def remove_path_by_index(self, host: PathLifecycleHost, path_index: int) -> bool:
        if type(path_index) is not int:
            return False
        if 0 <= path_index < len(host.paths):
            host.remove_path(host.paths[path_index])
            return True
        return False

    def start_path_on_station(
        self,
        host: PathLifecycleHost,
        station: Any,
        *,
        get_path_factory: PathFactoryGetter,
    ) -> None:
        if len(host.paths) < host.unlocked_num_paths:
            host.is_creating_path = True
            assigned_color = (0, 0, 0)
            available_colors = list(host.path_colors.keys())[: host.unlocked_num_paths]
            for path_color in available_colors:
                taken = host.path_colors[path_color]
                if not taken:
                    assigned_color = path_color
                    host.path_colors[path_color] = True
                    break
            path = get_path_factory()(assigned_color)
            host.path_to_color[path] = assigned_color
            path.add_station(station)
            path.is_being_created = True
            host.path_being_created = path
            host.paths.append(path)

    def create_path_from_station_indices(
        self,
        host: PathLifecycleHost,
        station_indices: list[int],
        loop: bool = False,
    ) -> Any | None:
        if not isinstance(station_indices, list):
            return None
        if len(station_indices) < 2 or len(host.paths) >= host.unlocked_num_paths:
            return None
        if any(
            type(idx) is not int or idx < 0 or idx >= len(host.stations)
            for idx in station_indices
        ):
            return None

        host.start_path_on_station(host.stations[station_indices[0]])
        created_path = host.path_being_created
        if not created_path:
            return None

        stations_to_add = station_indices[1:-1]
        if loop:
            stations_to_add = station_indices[1:]
            if station_indices[-1] == station_indices[0]:
                stations_to_add = station_indices[1:-1]

        for idx in stations_to_add:
            host.add_station_to_path(host.stations[idx])

        if loop:
            host.end_path_on_station(host.stations[station_indices[0]])
        else:
            host.end_path_on_station(host.stations[station_indices[-1]])

        if created_path in host.paths and not created_path.is_being_created:
            return created_path
        return None

    def replace_path(
        self,
        host: PathLifecycleHost,
        path: Any,
        station_indices: list[int],
        loop: bool = False,
        *,
        get_path_factory: Resolver,
        get_geometry_style: Resolver,
        get_graph_builder: Resolver,
        get_scoped_replanner: Resolver,
    ) -> bool:
        return replace_path_transaction(
            host,
            path,
            station_indices,
            loop,
            get_path_factory=get_path_factory,
            get_geometry_style=get_geometry_style,
            get_graph_builder=get_graph_builder,
            get_scoped_replanner=get_scoped_replanner,
        )

    def replace_path_by_id(
        self,
        host: PathLifecycleHost,
        path_id: str,
        station_indices: list[int],
        loop: bool = False,
    ) -> bool:
        if type(path_id) is not str or not path_id:
            return False
        matches = [path for path in host.paths if getattr(path, "id", None) == path_id]
        if len(matches) != 1:
            return False
        return host.replace_path(matches[0], station_indices, loop)

    def replace_path_by_index(
        self,
        host: PathLifecycleHost,
        path_index: int,
        station_indices: list[int],
        loop: bool = False,
    ) -> bool:
        if type(path_index) is not int or not 0 <= path_index < len(host.paths):
            return False
        path = host.paths[path_index]
        if sum(candidate is path for candidate in host.paths) != 1:
            return False
        return host.replace_path(path, station_indices, loop)

    def add_station_to_path(self, host: PathLifecycleHost, station: Any) -> None:
        assert host.path_being_created is not None
        if host.path_being_created.stations[-1] == station:
            return
        if (
            len(host.path_being_created.stations) > 1
            and host.path_being_created.stations[0] == station
        ):
            host.path_being_created.set_loop()
            station.start_snap_blip(host.time_ms, host.path_being_created.color)
        elif host.path_being_created.stations[0] != station:
            if host.path_being_created.is_looped:
                host.path_being_created.remove_loop()
            host.path_being_created.add_station(station)
            station.start_snap_blip(host.time_ms, host.path_being_created.color)

    def abort_path_creation(self, host: PathLifecycleHost) -> None:
        assert host.path_being_created is not None
        host.is_creating_path = False
        host.release_color_for_path(host.path_being_created)
        host.paths.remove(host.path_being_created)
        host.path_being_created = None

    def release_color_for_path(self, host: PathLifecycleHost, path: Any) -> None:
        host.path_colors[path.color] = False
        del host.path_to_color[path]

    def finish_path_creation(self, host: PathLifecycleHost) -> None:
        assert host.path_being_created is not None
        draft = host.path_being_created
        # GM-09c commit-boundary guard: clearing is_being_created is the moment a
        # draft becomes a COUNTED crossing, so the authoritative budget check lives
        # here and counts the REAL draft (`draft.stations`/`is_looped`), never a
        # route predicted from raw indices -- this also catches a direct
        # start/add/finish that bypasses end_path_on_station (review Codex). Over
        # budget -> the ordinary abort (unchanged from pre-GM-09c: it removes the
        # draft and frees its color; a transient snap-blip from the drag fades as it
        # always has, so CLASSIC stays byte-identical). No crossing commits.
        if not within_tunnel_budget(
            host, draft.stations, draft.is_looped, exclude=draft
        ):
            host.abort_path_creation()
            return
        host.is_creating_path = False
        draft.is_being_created = False
        draft.remove_temporary_point()
        host.path_being_created = None
        host.assign_paths_to_buttons()

    def end_path_on_station(self, host: PathLifecycleHost, station: Any) -> None:
        assert host.path_being_created is not None
        creating = host.path_being_created
        stations = creating.stations
        if len(stations) > 1 and stations[-1] == station:
            action = "finish"
        elif len(stations) > 1 and stations[0] == station:
            action = "loop"
        elif stations[0] != station:
            action = "extend"
        else:
            host.abort_path_creation()
            return
        # GM-09c tunnel-budget gate on the RESOLVED route (the real draft plus the
        # ending station), so it counts exactly what commits -- an explicit-closure
        # loop [X,Y,X] resolves to the 2-station loop [X,Y] (one crossing), never
        # the raw round trip (review re-review). Gated BEFORE the extend/loop
        # mutation, so an over-budget release adds no station and commits no
        # crossing; the ordinary abort (unchanged) removes the draft.
        final_stations = list(stations) + ([station] if action == "extend" else [])
        final_loop = bool(creating.is_looped) or action == "loop"
        if not within_tunnel_budget(host, final_stations, final_loop, exclude=creating):
            host.abort_path_creation()
            return
        if action == "loop":
            creating.set_loop()
        elif action == "extend":
            creating.add_station(station)
            station.start_snap_blip(host.time_ms, creating.color)
        host.finish_path_creation()
