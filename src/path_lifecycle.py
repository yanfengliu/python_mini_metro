from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from path_replacement import replace_path as replace_path_transaction

PathFactoryGetter = Callable[[], Callable[[Any], Any]]
Resolver = Callable[[], Any]


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

    def remove_path(self, host: PathLifecycleHost, path: Any) -> None:
        host.path_to_button[path].remove_path()
        for metro in list(path.metros):
            for passenger in list(metro.passengers):
                if passenger in host.passengers:
                    host.passengers.remove(passenger)
                host.travel_plans.pop(passenger, None)
            if metro in host.metros:
                host.metros.remove(metro)
        host.invalidate_travel_plans_for_path(path)
        host.release_color_for_path(path)
        host.paths.remove(path)
        host.assign_paths_to_buttons()
        host.find_travel_plan_for_passengers()

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
        host.is_creating_path = False
        host.path_being_created.is_being_created = False
        host.path_being_created.remove_temporary_point()
        host.path_being_created = None
        host.assign_paths_to_buttons()

    def end_path_on_station(self, host: PathLifecycleHost, station: Any) -> None:
        assert host.path_being_created is not None
        if (
            len(host.path_being_created.stations) > 1
            and host.path_being_created.stations[-1] == station
        ):
            host.finish_path_creation()
        elif (
            len(host.path_being_created.stations) > 1
            and host.path_being_created.stations[0] == station
        ):
            host.path_being_created.set_loop()
            host.finish_path_creation()
        elif host.path_being_created.stations[0] != station:
            host.path_being_created.add_station(station)
            station.start_snap_blip(host.time_ms, host.path_being_created.color)
            host.finish_path_creation()
        else:
            host.abort_path_creation()
