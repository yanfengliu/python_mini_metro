"""Queue-flag transitions with snapshot-guarded service reconciliation."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from carriage_transaction_snapshot import (
    restore_transaction_state,
    snapshot_transaction_state,
    transaction_state_matches,
)
from fleet_validation import service_cache_is_canonical

QueueStateCheck = Callable[..., bool]
ReconcileStationService = Callable[[Any], None]


def _restore_flag(metro: Any, value: Any) -> None:
    try:
        metro.is_unassignment_queued = value
    except Exception:
        pass


def set_queue_flag(metro: Any, value: bool) -> bool:
    """Write and read back the queue flag, restoring the original on failure."""

    original = metro.is_unassignment_queued
    try:
        metro.is_unassignment_queued = value
    except Exception:
        _restore_flag(metro, original)
        return False
    if metro.is_unassignment_queued is not value:
        _restore_flag(metro, original)
        return False
    return True


def reconcile_queue_transition(
    host: Any,
    metro: Any,
    reconcile_station_service: ReconcileStationService,
    *,
    queue_state_is_canonical: QueueStateCheck,
    restore_flag: Any,
    label: str,
    allow_stale_bound: bool = False,
) -> bool:
    """Rebind the flipped Metro's at-station service cache transactionally.

    Mirrors the carriage attach/detach reconciliation (D-023): the pure
    oracle rebinds under the flipped queue flag, preserving an
    identity-matching fraction, dropping a no-longer-legal boarding
    binding, and binding a newly legal action. Any failure restores the
    complete pre-reconcile state including the queue flag and refuses.

    ``allow_stale_bound`` relaxes only the whole-fleet postcondition so a
    user queue/cancel tolerates an unrelated Metro's transient stale-bound
    cache (committed-around verbatim by the identity ``transaction_state_matches``);
    the touched Metro's own cache stays strictly oracle-bound.
    """

    state = snapshot_transaction_state(host)
    try:
        reconcile_station_service(metro)
        if not transaction_state_matches(host, state, allow_service_change=metro):
            raise ValueError(f"{label} reconciliation changed unrelated state")
        if not service_cache_is_canonical(
            host, metro, allow_unbound=False
        ) or not queue_state_is_canonical(host, allow_stale_bound=allow_stale_bound):
            raise ValueError(f"{label} reconciliation failed its postcondition")
    except BaseException as error:
        traceback = error.__traceback__
        restore_transaction_state(host, state)
        _restore_flag(metro, restore_flag)
        if not isinstance(error, Exception):
            raise error.with_traceback(traceback)
        return False
    return True
