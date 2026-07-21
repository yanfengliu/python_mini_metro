"""Deterministic, rollback-safe carriage attachment transactions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from carriage_transaction_snapshot import (
    restore_transaction_state,
    snapshot_transaction_state,
    transaction_state_matches,
)
from fleet_management import (
    _command_target_is_complete,
    _queue_state_is_canonical,
    _real_station,
)
from fleet_validation import (
    assigned_carriage_count,
    carriage_state_is_canonical,
    identity_union,
    service_cache_is_canonical,
    valid_new_carriage,
)

CarriageFactoryGetter = Callable[[], Callable[[], Any]]
ReconcileStationService = Callable[[Any], None]


def _valid_host_and_path(host: Any, path: Any) -> bool:
    total = getattr(host, "num_carriages", None)
    return (
        type(total) is int
        and total >= 0
        and not bool(getattr(host, "is_game_over", False))
        and _command_target_is_complete(host, path)
        and _queue_state_is_canonical(host)
        and carriage_state_is_canonical(host)
    )


def _attach_candidate(host: Any, path: Any) -> Any | None:
    if not _valid_host_and_path(host, path):
        return None
    if max(0, host.num_carriages - assigned_carriage_count(host)) <= 0:
        return None
    eligible = tuple(
        (index, metro)
        for index, metro in enumerate(path.metros)
        if metro.is_unassignment_queued is False
    )
    if not eligible:
        return None
    return min(eligible, key=lambda item: (len(item[1].carriages), item[0]))[1]


def _detach_candidate(host: Any, path: Any) -> Any | None:
    if not _valid_host_and_path(host, path):
        return None
    eligible = []
    for index, metro in enumerate(path.metros):
        if metro.is_unassignment_queued is not False or not metro.carriages:
            continue
        remaining_capacity = metro._base_capacity + sum(
            carriage.capacity for carriage in metro.carriages[:-1]
        )
        if len(metro.passengers) <= remaining_capacity:
            eligible.append((index, metro))
    if not eligible:
        return None
    return max(eligible, key=lambda item: (len(item[1].carriages), item[0]))[1]


class CarriageManagement:
    """Stateless attachment/detachment over the facade-owned canonical graph."""

    __slots__ = ()

    def can_attach(self, host: Any, path: Any) -> bool:
        try:
            return _attach_candidate(host, path) is not None
        except Exception:
            return False

    def can_detach(self, host: Any, path: Any) -> bool:
        try:
            return _detach_candidate(host, path) is not None
        except Exception:
            return False

    def attach(
        self,
        host: Any,
        path: Any,
        *,
        get_carriage_factory: CarriageFactoryGetter,
        reconcile_station_service: ReconcileStationService,
    ) -> bool:
        target = _attach_candidate(host, path)
        if target is None:
            return False
        state = snapshot_transaction_state(host)
        original = tuple(target.carriages)
        existing = identity_union(
            *(metro.carriages for metro in host.metros),
            *(metro.carriages for active in host.paths for metro in active.metros),
        )
        try:
            factory = get_carriage_factory()
            if not callable(factory):
                raise TypeError("carriage factory is not callable")
            candidate = factory()
            if not transaction_state_matches(host, state):
                raise ValueError("graph changed during carriage factory resolution")
            if not valid_new_carriage(candidate, existing):
                raise ValueError("carriage factory returned an invalid identity")
            candidate_state = (candidate.id, candidate.capacity, candidate.shape)

            target.carriages.append(candidate)
            expected = (*original, candidate)
            if not transaction_state_matches(
                host,
                state,
                carriage_override=(target, expected),
            ):
                raise ValueError("carriage append changed unrelated state")
            at_station = _real_station(path, target)
            if at_station:
                reconcile_station_service(target)
            if not transaction_state_matches(
                host,
                state,
                carriage_override=(target, expected),
                allow_service_change=target,
            ):
                raise ValueError("carriage reconciliation changed unrelated state")
            if (
                (candidate.id, candidate.capacity, candidate.shape) != candidate_state
                or not carriage_state_is_canonical(host)
                or (
                    at_station
                    and not service_cache_is_canonical(
                        host, target, allow_unbound=False
                    )
                )
                or not _queue_state_is_canonical(host)
            ):
                raise ValueError("carriage attachment failed its postcondition")
        except BaseException as error:
            traceback = error.__traceback__
            restore_transaction_state(host, state)
            if not isinstance(error, Exception):
                raise error.with_traceback(traceback)
            return False
        return True

    def detach(
        self,
        host: Any,
        path: Any,
        *,
        reconcile_station_service: ReconcileStationService,
    ) -> bool:
        target = _detach_candidate(host, path)
        if target is None:
            return False
        state = snapshot_transaction_state(host)
        original = tuple(target.carriages)
        expected = original[:-1]
        removed = original[-1]
        try:
            actual = target.carriages.pop()
            if actual is not removed:
                raise ValueError("carriage detach removed the wrong identity")
            if not transaction_state_matches(
                host,
                state,
                carriage_override=(target, expected),
            ):
                raise ValueError("carriage removal changed unrelated state")
            at_station = _real_station(path, target)
            if at_station:
                reconcile_station_service(target)
            if not transaction_state_matches(
                host,
                state,
                carriage_override=(target, expected),
                allow_service_change=target,
            ):
                raise ValueError("carriage reconciliation changed unrelated state")
            if (
                not carriage_state_is_canonical(host)
                or (
                    at_station
                    and not service_cache_is_canonical(
                        host, target, allow_unbound=False
                    )
                )
                or not _queue_state_is_canonical(host)
            ):
                raise ValueError("carriage detachment failed its postcondition")
        except BaseException as error:
            traceback = error.__traceback__
            restore_transaction_state(host, state)
            if not isinstance(error, Exception):
                raise error.with_traceback(traceback)
            return False
        return True
