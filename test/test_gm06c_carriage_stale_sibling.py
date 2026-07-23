"""GM-07b twin: carriage AND locomotive ops tolerate a stale service cache.

The mutation-path twin of the GM-07b:C checkpoint staleness fix. When two
Metros of one line stop at the same station, the live ``move_passengers``
loop can leave a Metro holding a structurally valid but stale
``_station_service_action`` (a later sibling boarded its cached target
inside the tick -- ordinary multi-Metro play GM-07b persists verbatim).

That stale cache made the strict, oracle-deriving ``carriage_state_is_canonical``
(directly, and inside ``_queue_state_is_canonical``) return False, so every
canonically-gated fleet action silently no-opped on *every* path during the
one-tick self-healing window -- even though the action is entirely orthogonal
to an unrelated Metro's cache.

``TestCarriageOpsTolerateStaleCache`` pins the carriage attach/detach fix
(GM-07b:D). ``TestFleetOpsTolerateStaleCache`` pins its locomotive twin
(GM-07b:E): ``assign``/``queue``/``cancel`` opt into the same
``allow_stale_bound`` tolerance the checkpoint verifier uses, so the touched
Metro's own post-reconcile cache stays strictly oracle-bound, an unrelated
stale sibling is committed-around untouched (and rolled back verbatim), while
the automatic ``settle`` reconciler and path-lifecycle removal keep the strict
default.
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.metro import Metro
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


class TestFleetOpsTolerateStaleCache(unittest.TestCase):
    def test_reachable_stale_window_now_permits_assign(self) -> None:
        # The headline repro: two locomotives are free but the strict gate on
        # an unrelated Metro's stale cache rejected assignment on every path.
        mediator = _reach_stale_window()
        path = mediator.paths[0]
        stale = _stale_bound_metros(mediator)
        self.assertEqual(len(stale), 1, "seed-9 must have exactly one stale Metro")
        stale_metro = stale[0]
        stale_cache = stale_metro._station_service_action
        self.assertFalse(_queue_state_is_canonical(mediator))
        self.assertTrue(_queue_state_is_canonical(mediator, allow_stale_bound=True))
        self.assertEqual(mediator.num_metros - len(mediator.metros), 2)

        before = len(mediator.metros)
        self.assertTrue(mediator.can_assign_locomotive(path))
        self.assertTrue(mediator.assign_locomotive(path))
        self.assertEqual(len(mediator.metros), before + 1)
        # Assign appends a fresh off-station Metro and never touches the
        # unrelated stale sibling, whose cache is preserved verbatim.
        self.assertIs(stale_metro._station_service_action, stale_cache)
        self.assertIn(stale_metro, _stale_bound_metros(mediator))

    def test_reachable_stale_window_now_permits_queue(self) -> None:
        # Case A: the queue candidate IS the stale Metro (empty at a station);
        # queueing clears its cache and immediately detaches it, self-healing
        # the window. The strict gate used to reject candidate selection.
        mediator = _reach_stale_window()
        path = mediator.paths[0]
        self.assertEqual(len(_stale_bound_metros(mediator)), 1)
        before = len(path.metros)

        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertEqual(len(path.metros), before - 1)
        self.assertFalse(_stale_bound_metros(mediator))

    def test_cancel_commits_while_an_unrelated_metro_stays_stale(self) -> None:
        # Case B: an occupied non-stale Metro was queued earlier (the canonical
        # waiting-to-empty state a prior queue produces); the unrelated empty
        # sibling holds the reachable stale cache. Cancelling must commit --
        # rebinding the touched Metro's own cache strictly -- while the
        # sibling's stale cache is preserved verbatim.
        mediator = _reach_stale_window()
        path = mediator.paths[0]
        stale = _stale_bound_metros(mediator)
        self.assertEqual(len(stale), 1)
        stale_metro = stale[0]
        stale_cache = stale_metro._station_service_action
        queued = next(metro for metro in path.metros if metro is not stale_metro)
        self.assertTrue(queued.passengers, "the Case-B queued Metro is occupied")
        queued.is_unassignment_queued = True

        self.assertFalse(_queue_state_is_canonical(mediator))
        # The public per-path count reflects the queued Metro despite the stale
        # sibling (it used to read a spurious 0 through the strict gate).
        self.assertEqual(mediator.queued_locomotives_for_path(path), 1)
        self.assertTrue(mediator.can_cancel_unassignment(path))
        self.assertTrue(mediator.cancel_unassignment(path))

        self.assertIs(queued.is_unassignment_queued, False)
        # The Metro the transaction touched is strictly oracle-bound: its own
        # postcondition was NOT relaxed.
        self.assertTrue(
            service_cache_is_canonical(mediator, queued, allow_unbound=False)
        )
        # The unrelated sibling's stale cache survived untouched.
        self.assertIs(stale_metro._station_service_action, stale_cache)
        self.assertIn(stale_metro, _stale_bound_metros(mediator))

    def test_queue_fast_path_detaches_while_unrelated_metro_stays_stale(self) -> None:
        # Case B for the immediate-detach fast path: the queue candidate is an
        # empty at-station non-stale Metro while an unrelated sibling holds the
        # stale cache. The fast-path detach must remove the candidate and
        # commit-around the sibling untouched.
        mediator, path, sibling = _sibling_stale_state()
        stale_cache = sibling._station_service_action
        self.assertIn(sibling, _stale_bound_metros(mediator))
        before = len(path.metros)

        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
        self.assertTrue(mediator.queue_locomotive_unassignment(path))
        self.assertEqual(len(path.metros), before - 1)
        self.assertIs(sibling._station_service_action, stale_cache)
        self.assertIn(sibling, _stale_bound_metros(mediator))

    def test_assign_rejects_and_rolls_back_an_effectful_factory(self) -> None:
        # Defense in depth (mirrors carriage attach): assign snapshots the full
        # state, so a factory that mutates an unrelated sibling's cache to
        # another structurally-valid, still-live action -- which allow_stale_bound
        # would accept in isolation -- is caught by the identity snapshot and the
        # whole state is restored verbatim. assign never commits a modified
        # sibling, and the reachable public factory (a pure Metro constructor)
        # can never trigger this.
        mediator = _reach_stale_window()
        path = mediator.paths[0]
        stale = _stale_bound_metros(mediator)
        self.assertEqual(len(stale), 1)
        sibling = stale[0]
        original_cache = sibling._station_service_action
        live_passenger = original_cache[1]
        metros_before = len(mediator.metros)
        path_metros_before = tuple(path.metros)

        def effectful_factory() -> Metro:
            sibling._station_service_action = ("transfer", live_passenger)
            return Metro()

        self.assertFalse(
            mediator._fleet.assign(
                mediator, path, get_metro_factory=lambda: effectful_factory
            )
        )
        # No Metro was added and the sibling's cache is restored verbatim.
        self.assertEqual(len(mediator.metros), metros_before)
        self.assertEqual(tuple(path.metros), path_metros_before)
        self.assertIs(sibling._station_service_action, original_cache)

    def test_assign_rolls_back_verbatim_when_factory_raises(self) -> None:
        # A raising factory leaves the fleet and the unrelated sibling exactly
        # as they were: full snapshot restore, not just the owner collections.
        mediator = _reach_stale_window()
        path = mediator.paths[0]
        sibling = _stale_bound_metros(mediator)[0]
        original_cache = sibling._station_service_action
        metros_before = tuple(mediator.metros)
        path_metros_before = tuple(path.metros)

        def raising_factory() -> Metro:
            raise RuntimeError("factory boom")

        self.assertFalse(
            mediator._fleet.assign(
                mediator, path, get_metro_factory=lambda: raising_factory
            )
        )
        self.assertEqual(tuple(mediator.metros), metros_before)
        self.assertEqual(tuple(path.metros), path_metros_before)
        self.assertIs(sibling._station_service_action, original_cache)

    def test_shared_validators_keep_strict_default(self) -> None:
        # The opt-in is scoped: the shared validators keep their strict default,
        # so callers that do not opt in still reject the stale window. Only the
        # fleet assign/queue/cancel and carriage guards pass allow_stale_bound.
        mediator = _reach_stale_window()
        self.assertFalse(carriage_state_is_canonical(mediator))
        self.assertFalse(_queue_state_is_canonical(mediator))
        self.assertTrue(carriage_state_is_canonical(mediator, allow_stale_bound=True))
        self.assertTrue(_queue_state_is_canonical(mediator, allow_stale_bound=True))

    def test_settle_stays_strict_under_unrelated_stale_sibling(self) -> None:
        # The automatic per-tick reconciler is deliberately NOT relaxed: a
        # queued empty at-station Metro that settle would normally detach is
        # left in place while an unrelated sibling is stale, so settle never
        # mutates the fleet around another Metro's transient cache.
        mediator, path, sibling = _sibling_stale_state()
        candidate = next(metro for metro in path.metros if metro is not sibling)
        self.assertFalse(candidate.passengers)
        candidate.is_unassignment_queued = True
        self.assertIn(sibling, _stale_bound_metros(mediator))

        self.assertEqual(mediator._fleet.settle(mediator), 0)
        self.assertIn(candidate, path.metros)
        self.assertIn(sibling, _stale_bound_metros(mediator))


if __name__ == "__main__":
    unittest.main()
