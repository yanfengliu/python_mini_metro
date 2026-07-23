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
from fleet_queue_transition import reconcile_queue_transition, set_queue_flag
from fleet_validation import carriage_state_is_canonical
from path_replacement_geometry import validate_path_geometry

MetroFactoryGetter = Callable[[], Callable[[], Any]]
ReconcileStationService = Callable[[Any], None]
_MISSING = object()


def _identity_unique(values: Any) -> bool:
    items = tuple(values)
    return len({id(value) for value in items}) == len(items)


def _same_identity_contents(collection: list[Any], contents: tuple[Any, ...]) -> bool:
    return len(collection) == len(contents) and all(
        current is expected for current, expected in zip(collection, contents)
    )


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


def _queue_state_is_canonical(host: Any, *, allow_stale_bound: bool = False) -> bool:
    if not _ownership_is_canonical(host) or not carriage_state_is_canonical(
        host, allow_stale_bound=allow_stale_bound
    ):
        return False
    return all(
        type(getattr(metro, "is_unassignment_queued", _MISSING)) is bool
        and isinstance(getattr(metro, "passengers", None), list)
        and _metro_binding_is_canonical(path, metro)
        for path in host.paths
        for metro in path.metros
    )


def _fleet_state_is_canonical(host: Any) -> bool:
    """Queue-state predicate for user locomotive ops, tolerant of a sibling.

    assign/queue/cancel are orthogonal to another Metro's transient
    stale-but-structural ``_station_service_action`` (the reachable same-tick
    sibling-board window GM-07b persists verbatim), so they opt into the same
    ``allow_stale_bound`` tolerance the checkpoint verifier and carriage guards
    use. The touched Metro's own postcondition stays strict at its own site,
    while the automatic ``settle`` reconciler and path-lifecycle removal keep
    the strict ``_queue_state_is_canonical`` default.
    """

    return _queue_state_is_canonical(host, allow_stale_bound=True)


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
            ) or not _fleet_state_is_canonical(host):
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
        # Full snapshot/rollback, mirroring carriage attach: the only committed
        # transition is one fresh off-station Metro appended to the owning path
        # and the global fleet. Every other Metro -- including an unrelated
        # stale-bound sibling -- is pinned unchanged by identity, so an effectful
        # factory that touched one is caught and the whole state is restored
        # verbatim on any failure.
        state = snapshot_transaction_state(host)
        existing_ids = {id(metro) for metro in host.metros}
        try:
            factory = get_metro_factory()
            if not callable(factory):
                raise TypeError("metro factory is not callable")
            metro = factory()
            if not transaction_state_matches(host, state):
                raise ValueError("fleet state changed during metro factory resolution")
            if id(metro) in existing_ids:
                raise ValueError("metro factory returned an assigned identity")

            path.add_metro(metro)
            host.metros.append(metro)
            if not transaction_state_matches(host, state, added_owner=(path, metro)):
                raise ValueError("assignment changed unrelated fleet state")
            if not _assignment_initialized(path, metro) or not (
                _fleet_state_is_canonical(host)
            ):
                raise ValueError("assigned Metro failed its ownership postcondition")
        except BaseException as error:
            traceback = error.__traceback__
            restore_transaction_state(host, state)
            if not isinstance(error, Exception):
                raise error.with_traceback(traceback)
            return False
        return True

    def unassignment_candidate(self, host: Any, path: Any) -> Any | None:
        try:
            if bool(getattr(host, "is_game_over", False)):
                return None
            if not _command_target_is_complete(
                host, path
            ) or not _fleet_state_is_canonical(host):
                return None
            for metro in reversed(path.metros):
                if not metro.passengers and metro.is_unassignment_queued is False:
                    return metro
            # Only when no empty candidate exists: the occupied nonqueued
            # Metro with the fewest riders, tie-broken to the latest owner.
            occupied = None
            for metro in reversed(path.metros):
                if metro.is_unassignment_queued is not False:
                    continue
                if occupied is None or len(metro.passengers) < len(occupied.passengers):
                    occupied = metro
            return occupied
        except Exception:
            return None

    def can_queue(self, host: Any, path: Any) -> bool:
        return self.unassignment_candidate(host, path) is not None

    def queue(
        self,
        host: Any,
        path: Any,
        *,
        reconcile_station_service: ReconcileStationService | None = None,
    ) -> bool:
        metro = self.unassignment_candidate(host, path)
        if metro is None:
            return False
        original_flag = metro.is_unassignment_queued
        if not set_queue_flag(metro, True):
            return False
        # The immediate-detach fast path stays gated on empty-at-station; an
        # at-station occupied selection reconciles to the queue-gated oracle.
        if not metro.passengers and _real_station(path, metro):
            metro._station_service_action = None
            metro.stop_time_remaining_ms = 0
            metro.boarding_progress_ms = 0
            self._detach(host, path, metro, allow_stale_bound=True)
            return True
        if reconcile_station_service is not None and _real_station(path, metro):
            return reconcile_queue_transition(
                host,
                metro,
                reconcile_station_service,
                queue_state_is_canonical=_queue_state_is_canonical,
                restore_flag=original_flag,
                label="queue",
                allow_stale_bound=True,
            )
        return True

    def cancel_candidate(self, host: Any, path: Any) -> Any | None:
        try:
            if bool(getattr(host, "is_game_over", False)):
                return None
            if not _command_target_is_complete(
                host, path
            ) or not _fleet_state_is_canonical(host):
                return None
            for metro in path.metros:
                if metro.is_unassignment_queued is True:
                    return metro
        except Exception:
            return None
        return None

    def can_cancel(self, host: Any, path: Any) -> bool:
        return self.cancel_candidate(host, path) is not None

    def cancel(
        self,
        host: Any,
        path: Any,
        *,
        reconcile_station_service: ReconcileStationService | None = None,
    ) -> bool:
        metro = self.cancel_candidate(host, path)
        if metro is None:
            return False
        original_flag = metro.is_unassignment_queued
        if not set_queue_flag(metro, False):
            return False
        # A restored at-station Metro rebinds any newly-legal action at once.
        if reconcile_station_service is not None and _real_station(path, metro):
            return reconcile_queue_transition(
                host,
                metro,
                reconcile_station_service,
                queue_state_is_canonical=_queue_state_is_canonical,
                restore_flag=original_flag,
                label="cancel",
                allow_stale_bound=True,
            )
        return True

    def reconcile(self, host: Any) -> None:
        """Repair only provably-safe residual fleet shapes; refuse the rest."""

        try:
            global_metros = getattr(host, "metros", None)
            paths = getattr(host, "paths", None)
            if not isinstance(global_metros, list) or not isinstance(paths, list):
                return
            for path in tuple(paths):
                collection = getattr(path, "metros", None)
                if not isinstance(collection, list):
                    continue
                for metro in tuple(collection):
                    if any(metro is known for known in global_metros):
                        continue
                    if getattr(metro, "is_unassignment_queued", False) is not False:
                        metro.is_unassignment_queued = False
                    riders = getattr(metro, "passengers", None)
                    if isinstance(riders, list) and not riders:
                        collection.remove(metro)
        except Exception:
            return

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
            # The public per-path queued count stays consistent with
            # can_queue/can_cancel (not spuriously 0) during an unrelated Metro's
            # one-tick stale-bound window. (The rendered fleet-button badge does
            # not read this; it counts the raw is_unassignment_queued flags.)
            if not _path_is_exact_active(host, path) or not _fleet_state_is_canonical(
                host
            ):
                return 0
            metros = path.metros
        return sum(
            getattr(metro, "is_unassignment_queued", _MISSING) is True
            for metro in metros
        )

    @staticmethod
    def _detach(
        host: Any, path: Any, metro: Any, *, allow_stale_bound: bool = False
    ) -> bool:
        # ``allow_stale_bound`` lets the user-initiated queue fast path remove an
        # empty at-station Metro while an unrelated sibling holds a transient
        # stale-bound cache; the removed Metro's own cache is cleared first, and
        # the snapshot-equality ``transaction_state_matches`` still pins the
        # sibling verbatim. The automatic ``settle`` reconciler leaves it False.
        if (
            not _path_is_complete(host, path)
            or not _queue_state_is_canonical(host, allow_stale_bound=allow_stale_bound)
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
                host, allow_stale_bound=allow_stale_bound
            ):
                raise ValueError("detachment failed its ownership postcondition")
        except BaseException as error:
            traceback = error.__traceback__
            restore_transaction_state(host, state)
            if not isinstance(error, Exception):
                raise error.with_traceback(traceback)
            return False
        return True
