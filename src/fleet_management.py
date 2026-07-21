"""Stateless locomotive assignment and queued-return transactions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from carriage_transaction_snapshot import (
    restore_transaction_state,
    snapshot_transaction_state,
    transaction_state_matches,
)
from config import path_order_shift, path_width
from fleet_validation import carriage_state_is_canonical
from path_replacement_geometry import validate_path_geometry

MetroFactoryGetter = Callable[[], Callable[[], Any]]
_MISSING = object()


def _identity_unique(values: Any) -> bool:
    items = tuple(values)
    return len({id(value) for value in items}) == len(items)


def _same_identity_contents(collection: list[Any], contents: tuple[Any, ...]) -> bool:
    return len(collection) == len(contents) and all(
        current is expected for current, expected in zip(collection, contents)
    )


def _is_exact_append(
    collection: list[Any], contents: tuple[Any, ...], appended: Any
) -> bool:
    return (
        len(collection) == len(contents) + 1
        and all(current is expected for current, expected in zip(collection, contents))
        and collection[-1] is appended
    )


def _restore_collection(owner: Any, name: str, collection: list[Any], contents) -> None:
    setattr(owner, name, collection)
    list.clear(collection)
    list.extend(collection, contents)


def _restore_owner_lists(
    host: Any,
    path: Any,
    path_collection: list[Any],
    path_contents: tuple[Any, ...],
    global_collection: list[Any],
    global_contents: tuple[Any, ...],
) -> None:
    _restore_collection(path, "metros", path_collection, path_contents)
    _restore_collection(host, "metros", global_collection, global_contents)


def _active_paths(host: Any) -> tuple[Any, ...] | None:
    paths = getattr(host, "paths", None)
    if not isinstance(paths, list) or not _identity_unique(paths):
        return None
    return tuple(paths)


def _path_is_exact_active(host: Any, path: Any) -> bool:
    paths = _active_paths(host)
    if paths is None or sum(candidate is path for candidate in paths) != 1:
        return False
    path_ids = [getattr(candidate, "id", _MISSING) for candidate in paths]
    return all(type(path_id) is str and path_id for path_id in path_ids) and len(
        set(path_ids)
    ) == len(path_ids)


def _path_is_complete(host: Any, path: Any) -> bool:
    if not _path_is_exact_active(host, path):
        return False
    if (
        bool(getattr(path, "is_being_created", False))
        or getattr(path, "temp_point", None) is not None
    ):
        return False
    stations = getattr(path, "stations", None)
    active_stations = getattr(host, "stations", None)
    segments = getattr(path, "segments", None)
    if not (
        isinstance(stations, list)
        and len(stations) >= 2
        and _identity_unique(stations)
        and isinstance(active_stations, list)
        and _identity_unique(active_stations)
        and all(
            any(station is active for active in active_stations) for station in stations
        )
        and isinstance(segments, list)
        and bool(segments)
        and callable(getattr(path, "add_metro", None))
    ):
        return False
    is_looped = getattr(path, "is_looped", None)
    return type(is_looped) is bool and validate_path_geometry(
        path,
        stations,
        is_looped,
        lane_spacing=path_order_shift,
        stroke_width=path_width,
    )


def _command_target_is_complete(host: Any, path: Any) -> bool:
    return (
        not bool(getattr(host, "is_creating_path", False))
        and getattr(host, "path_being_created", None) is None
        and _path_is_complete(host, path)
    )


def _ownership_is_canonical(host: Any) -> bool:
    paths = _active_paths(host)
    global_metros = getattr(host, "metros", None)
    if paths is None or not isinstance(global_metros, list):
        return False
    path_collections = [getattr(path, "metros", None) for path in paths]
    if any(not isinstance(collection, list) for collection in path_collections):
        return False
    collections = [global_metros, *path_collections]
    if not _identity_unique(collections) or not _identity_unique(global_metros):
        return False

    owners: dict[int, Any] = {}
    for path, collection in zip(paths, path_collections):
        path_id = getattr(path, "id", _MISSING)
        if type(path_id) is not str or not path_id:
            return False
        for metro in collection:
            if id(metro) in owners or getattr(metro, "path_id", _MISSING) != path_id:
                return False
            owners[id(metro)] = path
    return {id(metro) for metro in global_metros} == set(owners)


def _queue_state_is_canonical(host: Any) -> bool:
    if not _ownership_is_canonical(host) or not carriage_state_is_canonical(host):
        return False
    return all(
        type(getattr(metro, "is_unassignment_queued", _MISSING)) is bool
        and isinstance(getattr(metro, "passengers", None), list)
        and _metro_binding_is_canonical(path, metro)
        for path in host.paths
        for metro in path.metros
    )


def _real_station(path: Any, metro: Any) -> bool:
    current = getattr(metro, "current_station", None)
    stations = getattr(path, "stations", ())
    return current is not None and any(current is station for station in stations)


def _metro_binding_is_canonical(path: Any, metro: Any) -> bool:
    segments = getattr(path, "segments", ())
    index = getattr(metro, "current_segment_idx", None)
    station = getattr(metro, "current_station", _MISSING)
    return (
        type(index) is int
        and 0 <= index < len(segments)
        and getattr(metro, "current_segment", None) is segments[index]
        and getattr(metro, "position", None) is not None
        and (station is None or _real_station(path, metro))
    )


def _assignment_initialized(path: Any, metro: Any) -> bool:
    segments = getattr(path, "segments", ())
    index = getattr(metro, "current_segment_idx", None)
    return (
        getattr(metro, "is_unassignment_queued", _MISSING) is False
        and getattr(metro, "path_id", _MISSING) == path.id
        and type(index) is int
        and index == 0
        and bool(segments)
        and getattr(metro, "current_segment", None) is segments[index]
        and getattr(metro, "current_station", _MISSING) is None
        and getattr(metro, "position", None) is segments[index].segment_start
    )


class FleetManagement:
    """Dependency-light algorithms over facade-owned fleet collections."""

    __slots__ = ()

    def can_assign(self, host: Any, path: Any) -> bool:
        try:
            if bool(getattr(host, "is_game_over", False)):
                return False
            if not _command_target_is_complete(
                host, path
            ) or not _queue_state_is_canonical(host):
                return False
            total = getattr(host, "num_metros", None)
            return type(total) is int and max(0, total - len(host.metros)) > 0
        except Exception:
            return False

    def assign(
        self,
        host: Any,
        path: Any,
        *,
        get_metro_factory: MetroFactoryGetter,
    ) -> bool:
        if not self.can_assign(host, path):
            return False
        path_collection = path.metros
        path_contents = tuple(path_collection)
        global_collection = host.metros
        global_contents = tuple(global_collection)
        existing_ids = {id(metro) for metro in global_contents}
        try:
            factory = get_metro_factory()
            if not callable(factory):
                raise TypeError("metro factory is not callable")
            metro = factory()
            if id(metro) in existing_ids:
                raise ValueError("metro factory returned an assigned identity")
            if (
                path.metros is not path_collection
                or host.metros is not global_collection
            ):
                raise ValueError("fleet collection rebound during factory resolution")
            if not _same_identity_contents(path_collection, path_contents) or not (
                _same_identity_contents(global_collection, global_contents)
            ):
                raise ValueError("fleet collection changed during factory resolution")

            path.add_metro(metro)
            if (
                path.metros is not path_collection
                or host.metros is not global_collection
            ):
                raise ValueError("fleet collection rebound during route assignment")
            if not _is_exact_append(path_collection, path_contents, metro) or not (
                _same_identity_contents(global_collection, global_contents)
            ):
                raise ValueError("route assignment did not append the exact identity")

            host.metros.append(metro)
            if (
                path.metros is not path_collection
                or host.metros is not global_collection
            ):
                raise ValueError("fleet collection rebound during global assignment")
            if not _is_exact_append(path_collection, path_contents, metro) or not (
                _is_exact_append(global_collection, global_contents, metro)
            ):
                raise ValueError("global assignment did not append the exact identity")
            if not _assignment_initialized(path, metro) or not (
                _queue_state_is_canonical(host)
            ):
                raise ValueError("assigned Metro failed its ownership postcondition")
        except BaseException as error:
            _restore_owner_lists(
                host,
                path,
                path_collection,
                path_contents,
                global_collection,
                global_contents,
            )
            if not isinstance(error, Exception):
                raise
            return False
        return True

    def unassignment_candidate(self, host: Any, path: Any) -> Any | None:
        try:
            if bool(getattr(host, "is_game_over", False)):
                return None
            if not _command_target_is_complete(
                host, path
            ) or not _queue_state_is_canonical(host):
                return None
            for metro in reversed(path.metros):
                if not metro.passengers and metro.is_unassignment_queued is False:
                    return metro
        except Exception:
            return None
        return None

    def can_queue(self, host: Any, path: Any) -> bool:
        return self.unassignment_candidate(host, path) is not None

    def queue(self, host: Any, path: Any) -> bool:
        metro = self.unassignment_candidate(host, path)
        if metro is None:
            return False
        original_flag = metro.is_unassignment_queued
        try:
            metro.is_unassignment_queued = True
        except Exception:
            try:
                metro.is_unassignment_queued = original_flag
            except Exception:
                pass
            return False
        if metro.is_unassignment_queued is not True:
            try:
                metro.is_unassignment_queued = original_flag
            except Exception:
                pass
            return False
        if _real_station(path, metro):
            metro._station_service_action = None
            metro.stop_time_remaining_ms = 0
            metro.boarding_progress_ms = 0
            self._detach(host, path, metro)
        return True

    def settle(self, host: Any) -> int:
        if bool(getattr(host, "is_paused", False)):
            return 0
        try:
            if not _queue_state_is_canonical(host):
                return 0
            paths = tuple(host.paths)
            candidates = tuple(
                (path, metro)
                for path in paths
                for metro in tuple(path.metros)
                if metro.is_unassignment_queued is True
                and not metro.passengers
                and _real_station(path, metro)
            )
        except Exception:
            return 0

        removed = 0
        for path, metro in candidates:
            if self._detach(host, path, metro):
                removed += 1
        return removed

    def queued_count(self, host: Any, path: Any | None = None) -> int:
        if path is None:
            metros = getattr(host, "metros", None)
            if not isinstance(metros, list):
                return 0
        else:
            if not _path_is_exact_active(host, path) or not _queue_state_is_canonical(
                host
            ):
                return 0
            metros = path.metros
        return sum(
            getattr(metro, "is_unassignment_queued", _MISSING) is True
            for metro in metros
        )

    @staticmethod
    def _detach(host: Any, path: Any, metro: Any) -> bool:
        if (
            not _path_is_complete(host, path)
            or not _queue_state_is_canonical(host)
            or getattr(metro, "is_unassignment_queued", None) is not True
            or bool(getattr(metro, "passengers", ()))
            or not _real_station(path, metro)
            or sum(candidate is metro for candidate in path.metros) != 1
            or sum(candidate is metro for candidate in host.metros) != 1
        ):
            return False
        state = snapshot_transaction_state(host)
        path_collection = path.metros
        path_contents = tuple(path_collection)
        global_collection = host.metros
        global_contents = tuple(global_collection)
        expected_path = tuple(
            candidate for candidate in path_contents if candidate is not metro
        )
        expected_global = tuple(
            candidate for candidate in global_contents if candidate is not metro
        )
        try:
            path.metros.remove(metro)
            host.metros.remove(metro)
            if (
                path.metros is not path_collection
                or host.metros is not global_collection
            ):
                raise ValueError("fleet collection rebound during detachment")
            if not _same_identity_contents(path_collection, expected_path) or not (
                _same_identity_contents(global_collection, expected_global)
            ):
                raise ValueError("detachment removed the wrong identity")
            metro._station_service_action = None
            metro.stop_time_remaining_ms = 0
            metro.boarding_progress_ms = 0
            if not transaction_state_matches(
                host,
                state,
                allow_service_change=metro,
                removed_owner=(path, metro),
            ):
                raise ValueError("detachment changed unrelated fleet state")
            if not _ownership_is_canonical(host) or not carriage_state_is_canonical(
                host
            ):
                raise ValueError("detachment failed its ownership postcondition")
        except BaseException as error:
            traceback = error.__traceback__
            restore_transaction_state(host, state)
            if not isinstance(error, Exception):
                raise error.with_traceback(traceback)
            return False
        return True
