"""GM-06c/07b twin: carriage attach/detach tolerate a stale service cache.

The mutation-path twin of the GM-07b:C checkpoint staleness fix. When two
Metros of one line stop at the same station, the live ``move_passengers``
loop can leave a Metro holding a structurally valid but stale
``_station_service_action`` (a later sibling boarded its cached target
inside the tick -- ordinary multi-Metro play GM-07b persists verbatim).

That stale cache made the strict, oracle-deriving ``carriage_state_is_canonical``
(directly, and inside ``_queue_state_is_canonical``) return False, so the
carriage attach/detach precondition and postconditions rejected it and the
public actions silently no-opped on *every* path during the one-tick
window -- even though a carriage op is entirely orthogonal to an unrelated
Metro's cache. The fix opts the carriage guards into the same
``allow_stale_bound`` tolerance the checkpoint verifier uses; the target
Metro's own post-reconcile cache stays strictly oracle-bound, an unrelated
stale cache is committed-around untouched, and every fleet-management and
path-lifecycle guard stays strict.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from env import MiniMetroEnv
from fleet_management import _queue_state_is_canonical
from fleet_validation import carriage_state_is_canonical, service_cache_is_canonical
from graph.graph_algo import build_station_nodes_dict
from passenger_capacity import pure_service_action, same_service_action

# Delta-debugged public sequence (seed 9) that parks two locomotives of one
# line at the same station where the board race leaves a stale bound cache.
_LAYOUT_SEED = 9
_SEQUENCE: tuple[tuple[dict[str, object], int], ...] = (
    ({"type": "create_path", "stations": [1, 2], "loop": False}, 1),
    (
        {"type": "replace_path", "path_index": 0, "stations": [2, 1, 0], "loop": False},
        1,
    ),
    ({"type": "assign_locomotive", "path_index": 0}, 0),
    ({"type": "noop"}, 1000),
    (
        {"type": "replace_path", "path_index": 0, "stations": [1, 2, 0], "loop": False},
        1,
    ),
    ({"type": "noop"}, 1000),
    ({"type": "assign_locomotive", "path_index": 0}, 0),
    ({"type": "noop"}, 50),
    ({"type": "attach_carriage", "path_index": 0}, 1),
    ({"type": "noop"}, 250),
    ({"type": "detach_carriage", "path_index": 0}, 1),
    ({"type": "noop"}, 1000),
    ({"type": "noop"}, 1000),
)


def _reach_stale_window() -> Any:
    env = MiniMetroEnv(reward_mode="deliveries")
    env.reset(seed=_LAYOUT_SEED)
    for action, dt_ms in _SEQUENCE:
        env.step(action, dt_ms=dt_ms)
    return env.mediator


def _stale_bound_metros(mediator: Any) -> list[Any]:
    nodes = build_station_nodes_dict(mediator.stations, mediator.paths)
    stale = []
    for metro in mediator.metros:
        cache = metro._station_service_action
        station = metro.current_station
        if cache is None or station is None:
            continue
        if not same_service_action(
            cache, pure_service_action(mediator, metro, station, nodes)
        ):
            stale.append(metro)
    return stale


def _sibling_stale_state() -> tuple[Any, Any, Any]:
    """Move the natural stale cache onto a non-target sibling.

    ``_attach_candidate``/``_detach_candidate`` pick the lowest-index Metro,
    which in the seed-9 state is the stale one, so a bare attach would merely
    reconcile it (Case A) and never exercise the postcondition tolerance.
    Reconcile that Metro (making it the canonical target) and transplant its
    stale bound cache onto the sibling, so a committed attach/detach must
    leave an *unrelated* Metro stale (Case B).
    """

    mediator = _reach_stale_window()
    path = mediator.paths[0]
    stale = _stale_bound_metros(mediator)
    assert len(stale) == 1, "seed-9 must have exactly one stale Metro"
    target = stale[0]
    sibling = next(metro for metro in path.metros if metro is not target)
    cache = target._station_service_action
    mediator._reconcile_station_service(target)
    interval = sibling.boarding_time_per_passenger_ms
    sibling._station_service_action = cache
    sibling.stop_time_remaining_ms = interval
    sibling.boarding_progress_ms = 0
    sibling.speed = 0
    return mediator, path, sibling


class TestCarriageOpsTolerateStaleCache(unittest.TestCase):
    def test_reachable_stale_window_now_permits_attach(self) -> None:
        mediator = _reach_stale_window()
        path = mediator.paths[0]
        # The reachable state is stale: the strict oracle-bound check rejects
        # it, only the stale-tolerant one accepts, and an attach is available.
        self.assertTrue(_stale_bound_metros(mediator))
        self.assertFalse(carriage_state_is_canonical(mediator))
        self.assertTrue(carriage_state_is_canonical(mediator, allow_stale_bound=True))
        carriages_before = sum(len(m.carriages) for m in path.metros)
        self.assertGreater(mediator.num_carriages - carriages_before, 0)

        self.assertTrue(mediator.can_attach_carriage(path))
        self.assertTrue(mediator.attach_carriage(path))
        self.assertEqual(
            sum(len(m.carriages) for m in path.metros), carriages_before + 1
        )

    def test_attach_commits_while_an_unrelated_metro_stays_stale(self) -> None:
        mediator, path, sibling = _sibling_stale_state()
        stale_cache = sibling._station_service_action
        self.assertIn(sibling, _stale_bound_metros(mediator))
        carriages_before = sum(len(m.carriages) for m in path.metros)

        self.assertTrue(mediator.can_attach_carriage(path))
        self.assertTrue(mediator.attach_carriage(path))

        # The op committed (a carriage was added) while the unrelated sibling's
        # stale cache was preserved verbatim, never reconciled or rolled back.
        self.assertEqual(
            sum(len(m.carriages) for m in path.metros), carriages_before + 1
        )
        self.assertIs(sibling._station_service_action, stale_cache)
        self.assertIn(sibling, _stale_bound_metros(mediator))
        # The Metro the transaction actually touched is strictly canonical: its
        # target postcondition was NOT relaxed.
        target = next(m for m in path.metros if m.carriages)
        self.assertTrue(
            service_cache_is_canonical(mediator, target, allow_unbound=False)
        )

    def test_detach_commits_while_an_unrelated_metro_stays_stale(self) -> None:
        mediator, path, sibling = _sibling_stale_state()
        # Give the canonical target a carriage to remove (still Case B: the
        # attach targets the reconciled Metro, leaving the sibling stale).
        self.assertTrue(mediator.attach_carriage(path))
        stale_cache = sibling._station_service_action
        self.assertIn(sibling, _stale_bound_metros(mediator))
        carriages_before = sum(len(m.carriages) for m in path.metros)

        self.assertTrue(mediator.can_detach_carriage(path))
        self.assertTrue(mediator.detach_carriage(path))

        self.assertEqual(
            sum(len(m.carriages) for m in path.metros), carriages_before - 1
        )
        self.assertIs(sibling._station_service_action, stale_cache)
        self.assertIn(sibling, _stale_bound_metros(mediator))

    def test_fleet_and_queue_guards_stay_strict(self) -> None:
        # The opt-in is scoped: the shared invariants keep their strict default,
        # so fleet-management/path-lifecycle guards are unaffected.
        mediator = _reach_stale_window()
        self.assertFalse(carriage_state_is_canonical(mediator))
        self.assertFalse(_queue_state_is_canonical(mediator))
        self.assertTrue(carriage_state_is_canonical(mediator, allow_stale_bound=True))
        self.assertTrue(_queue_state_is_canonical(mediator, allow_stale_bound=True))


if __name__ == "__main__":
    unittest.main()
