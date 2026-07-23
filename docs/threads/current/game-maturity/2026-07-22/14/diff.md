# GM-07b:E diff — locomotive assign/queue/cancel stale-sibling tolerance (final, incl. review hardening)

```diff
diff --git a/src/carriage_transaction_snapshot.py b/src/carriage_transaction_snapshot.py
index 641480d..8330bdd 100644
--- a/src/carriage_transaction_snapshot.py
+++ b/src/carriage_transaction_snapshot.py
@@ -289,8 +289,15 @@ def transaction_state_matches(
     carriage_override: tuple[Any, tuple[Any, ...]] | None = None,
     allow_service_change: Any | None = None,
     removed_owner: tuple[Any, Any] | None = None,
+    added_owner: tuple[Any, Any] | None = None,
 ) -> bool:
-    """Check the complete snapshot, allowing one exact composition transition."""
+    """Check the complete snapshot, allowing one exact composition transition.
+
+    ``removed_owner=(path, metro)`` expects that exact Metro gone from the
+    global and owning-path fleets; ``added_owner=(path, metro)`` expects it
+    appended to both (the snapshot must predate the append, so the new Metro
+    has no per-record entry to check). The two are mutually exclusive per call.
+    """

     try:
         host_state = state["host"]
@@ -313,6 +320,8 @@ def transaction_state_matches(
             if name == "metros" and removed_owner is not None:
                 _path, removed_metro = removed_owner
                 contents = tuple(item for item in contents if item is not removed_metro)
+            if name == "metros" and added_owner is not None:
+                contents = (*contents, added_owner[1])
             if getattr(host, name) is not collection or not _same_identity(
                 collection, contents
             ):
@@ -349,6 +358,12 @@ def transaction_state_matches(
                     contents = tuple(
                         item for item in contents if item is not removed_owner[1]
                     )
+                if (
+                    name == "metros"
+                    and added_owner is not None
+                    and path is added_owner[0]
+                ):
+                    contents = (*contents, added_owner[1])
                 if getattr(path, name) is not collection or not _same_identity(
                     collection, contents
                 ):
diff --git a/src/fleet_management.py b/src/fleet_management.py
index d01a580..23b98a5 100644
--- a/src/fleet_management.py
+++ b/src/fleet_management.py
@@ -31,34 +31,6 @@ def _same_identity_contents(collection: list[Any], contents: tuple[Any, ...]) ->
     )


-def _is_exact_append(
-    collection: list[Any], contents: tuple[Any, ...], appended: Any
-) -> bool:
-    return (
-        len(collection) == len(contents) + 1
-        and all(current is expected for current, expected in zip(collection, contents))
-        and collection[-1] is appended
-    )
-
-
-def _restore_collection(owner: Any, name: str, collection: list[Any], contents) -> None:
-    setattr(owner, name, collection)
-    list.clear(collection)
-    list.extend(collection, contents)
-
-
-def _restore_owner_lists(
-    host: Any,
-    path: Any,
-    path_collection: list[Any],
-    path_contents: tuple[Any, ...],
-    global_collection: list[Any],
-    global_contents: tuple[Any, ...],
-) -> None:
-    _restore_collection(path, "metros", path_collection, path_contents)
-    _restore_collection(host, "metros", global_collection, global_contents)
-
-
 def _active_paths(host: Any) -> tuple[Any, ...] | None:
     paths = getattr(host, "paths", None)
     if not isinstance(paths, list) or not _identity_unique(paths):
@@ -157,6 +129,21 @@ def _queue_state_is_canonical(host: Any, *, allow_stale_bound: bool = False) ->
     )


+def _fleet_state_is_canonical(host: Any) -> bool:
+    """Queue-state predicate for user locomotive ops, tolerant of a sibling.
+
+    assign/queue/cancel are orthogonal to another Metro's transient
+    stale-but-structural ``_station_service_action`` (the reachable same-tick
+    sibling-board window GM-07b persists verbatim), so they opt into the same
+    ``allow_stale_bound`` tolerance the checkpoint verifier and carriage guards
+    use. The touched Metro's own postcondition stays strict at its own site,
+    while the automatic ``settle`` reconciler and path-lifecycle removal keep
+    the strict ``_queue_state_is_canonical`` default.
+    """
+
+    return _queue_state_is_canonical(host, allow_stale_bound=True)
+
+
 def _real_station(path: Any, metro: Any) -> bool:
     current = getattr(metro, "current_station", None)
     stations = getattr(path, "stations", ())
@@ -202,7 +189,7 @@ class FleetManagement:
                 return False
             if not _command_target_is_complete(
                 host, path
-            ) or not _queue_state_is_canonical(host):
+            ) or not _fleet_state_is_canonical(host):
                 return False
             total = getattr(host, "num_metros", None)
             return type(total) is int and max(0, total - len(host.metros)) > 0
@@ -218,64 +205,37 @@ class FleetManagement:
     ) -> bool:
         if not self.can_assign(host, path):
             return False
-        path_collection = path.metros
-        path_contents = tuple(path_collection)
-        global_collection = host.metros
-        global_contents = tuple(global_collection)
-        existing_ids = {id(metro) for metro in global_contents}
+        # Full snapshot/rollback, mirroring carriage attach: the only committed
+        # transition is one fresh off-station Metro appended to the owning path
+        # and the global fleet. Every other Metro -- including an unrelated
+        # stale-bound sibling -- is pinned unchanged by identity, so an effectful
+        # factory that touched one is caught and the whole state is restored
+        # verbatim on any failure.
+        state = snapshot_transaction_state(host)
+        existing_ids = {id(metro) for metro in host.metros}
         try:
             factory = get_metro_factory()
             if not callable(factory):
                 raise TypeError("metro factory is not callable")
             metro = factory()
+            if not transaction_state_matches(host, state):
+                raise ValueError("fleet state changed during metro factory resolution")
             if id(metro) in existing_ids:
                 raise ValueError("metro factory returned an assigned identity")
-            if (
-                path.metros is not path_collection
-                or host.metros is not global_collection
-            ):
-                raise ValueError("fleet collection rebound during factory resolution")
-            if not _same_identity_contents(path_collection, path_contents) or not (
-                _same_identity_contents(global_collection, global_contents)
-            ):
-                raise ValueError("fleet collection changed during factory resolution")

             path.add_metro(metro)
-            if (
-                path.metros is not path_collection
-                or host.metros is not global_collection
-            ):
-                raise ValueError("fleet collection rebound during route assignment")
-            if not _is_exact_append(path_collection, path_contents, metro) or not (
-                _same_identity_contents(global_collection, global_contents)
-            ):
-                raise ValueError("route assignment did not append the exact identity")
-
             host.metros.append(metro)
-            if (
-                path.metros is not path_collection
-                or host.metros is not global_collection
-            ):
-                raise ValueError("fleet collection rebound during global assignment")
-            if not _is_exact_append(path_collection, path_contents, metro) or not (
-                _is_exact_append(global_collection, global_contents, metro)
-            ):
-                raise ValueError("global assignment did not append the exact identity")
+            if not transaction_state_matches(host, state, added_owner=(path, metro)):
+                raise ValueError("assignment changed unrelated fleet state")
             if not _assignment_initialized(path, metro) or not (
-                _queue_state_is_canonical(host)
+                _fleet_state_is_canonical(host)
             ):
                 raise ValueError("assigned Metro failed its ownership postcondition")
         except BaseException as error:
-            _restore_owner_lists(
-                host,
-                path,
-                path_collection,
-                path_contents,
-                global_collection,
-                global_contents,
-            )
+            traceback = error.__traceback__
+            restore_transaction_state(host, state)
             if not isinstance(error, Exception):
-                raise
+                raise error.with_traceback(traceback)
             return False
         return True

@@ -285,7 +245,7 @@ class FleetManagement:
                 return None
             if not _command_target_is_complete(
                 host, path
-            ) or not _queue_state_is_canonical(host):
+            ) or not _fleet_state_is_canonical(host):
                 return None
             for metro in reversed(path.metros):
                 if not metro.passengers and metro.is_unassignment_queued is False:
@@ -324,7 +284,7 @@ class FleetManagement:
             metro._station_service_action = None
             metro.stop_time_remaining_ms = 0
             metro.boarding_progress_ms = 0
-            self._detach(host, path, metro)
+            self._detach(host, path, metro, allow_stale_bound=True)
             return True
         if reconcile_station_service is not None and _real_station(path, metro):
             return reconcile_queue_transition(
@@ -334,6 +294,7 @@ class FleetManagement:
                 queue_state_is_canonical=_queue_state_is_canonical,
                 restore_flag=original_flag,
                 label="queue",
+                allow_stale_bound=True,
             )
         return True

@@ -343,7 +304,7 @@ class FleetManagement:
                 return None
             if not _command_target_is_complete(
                 host, path
-            ) or not _queue_state_is_canonical(host):
+            ) or not _fleet_state_is_canonical(host):
                 return None
             for metro in path.metros:
                 if metro.is_unassignment_queued is True:
@@ -377,6 +338,7 @@ class FleetManagement:
                 queue_state_is_canonical=_queue_state_is_canonical,
                 restore_flag=original_flag,
                 label="cancel",
+                allow_stale_bound=True,
             )
         return True

@@ -433,7 +395,11 @@ class FleetManagement:
             if not isinstance(metros, list):
                 return 0
         else:
-            if not _path_is_exact_active(host, path) or not _queue_state_is_canonical(
+            # The public per-path queued count stays consistent with
+            # can_queue/can_cancel (not spuriously 0) during an unrelated Metro's
+            # one-tick stale-bound window. (The rendered fleet-button badge does
+            # not read this; it counts the raw is_unassignment_queued flags.)
+            if not _path_is_exact_active(host, path) or not _fleet_state_is_canonical(
                 host
             ):
                 return 0
@@ -444,10 +410,17 @@ class FleetManagement:
         )

     @staticmethod
-    def _detach(host: Any, path: Any, metro: Any) -> bool:
+    def _detach(
+        host: Any, path: Any, metro: Any, *, allow_stale_bound: bool = False
+    ) -> bool:
+        # ``allow_stale_bound`` lets the user-initiated queue fast path remove an
+        # empty at-station Metro while an unrelated sibling holds a transient
+        # stale-bound cache; the removed Metro's own cache is cleared first, and
+        # the snapshot-equality ``transaction_state_matches`` still pins the
+        # sibling verbatim. The automatic ``settle`` reconciler leaves it False.
         if (
             not _path_is_complete(host, path)
-            or not _queue_state_is_canonical(host)
+            or not _queue_state_is_canonical(host, allow_stale_bound=allow_stale_bound)
             or getattr(metro, "is_unassignment_queued", None) is not True
             or bool(getattr(metro, "passengers", ()))
             or not _real_station(path, metro)
@@ -489,7 +462,7 @@ class FleetManagement:
             ):
                 raise ValueError("detachment changed unrelated fleet state")
             if not _ownership_is_canonical(host) or not carriage_state_is_canonical(
-                host
+                host, allow_stale_bound=allow_stale_bound
             ):
                 raise ValueError("detachment failed its ownership postcondition")
         except BaseException as error:
diff --git a/src/fleet_queue_transition.py b/src/fleet_queue_transition.py
index c9f4fa8..26debda 100644
--- a/src/fleet_queue_transition.py
+++ b/src/fleet_queue_transition.py
@@ -12,7 +12,7 @@ from carriage_transaction_snapshot import (
 )
 from fleet_validation import service_cache_is_canonical

-QueueStateCheck = Callable[[Any], bool]
+QueueStateCheck = Callable[..., bool]
 ReconcileStationService = Callable[[Any], None]


@@ -46,6 +46,7 @@ def reconcile_queue_transition(
     queue_state_is_canonical: QueueStateCheck,
     restore_flag: Any,
     label: str,
+    allow_stale_bound: bool = False,
 ) -> bool:
     """Rebind the flipped Metro's at-station service cache transactionally.

@@ -54,6 +55,11 @@ def reconcile_queue_transition(
     identity-matching fraction, dropping a no-longer-legal boarding
     binding, and binding a newly legal action. Any failure restores the
     complete pre-reconcile state including the queue flag and refuses.
+
+    ``allow_stale_bound`` relaxes only the whole-fleet postcondition so a
+    user queue/cancel tolerates an unrelated Metro's transient stale-bound
+    cache (committed-around verbatim by the identity ``transaction_state_matches``);
+    the touched Metro's own cache stays strictly oracle-bound.
     """

     state = snapshot_transaction_state(host)
@@ -63,7 +69,7 @@ def reconcile_queue_transition(
             raise ValueError(f"{label} reconciliation changed unrelated state")
         if not service_cache_is_canonical(
             host, metro, allow_unbound=False
-        ) or not queue_state_is_canonical(host):
+        ) or not queue_state_is_canonical(host, allow_stale_bound=allow_stale_bound):
             raise ValueError(f"{label} reconciliation failed its postcondition")
     except BaseException as error:
         traceback = error.__traceback__
diff --git a/test/test_gm06c_carriage_stale_sibling.py b/test/test_gm06c_carriage_stale_sibling.py
index d53f228..5138747 100644
--- a/test/test_gm06c_carriage_stale_sibling.py
+++ b/test/test_gm06c_carriage_stale_sibling.py
@@ -1,4 +1,4 @@
-"""GM-06c/07b twin: carriage attach/detach tolerate a stale service cache.
+"""GM-07b twin: carriage AND locomotive ops tolerate a stale service cache.

 The mutation-path twin of the GM-07b:C checkpoint staleness fix. When two
 Metros of one line stop at the same station, the live ``move_passengers``
@@ -7,15 +7,19 @@ loop can leave a Metro holding a structurally valid but stale
 inside the tick -- ordinary multi-Metro play GM-07b persists verbatim).

 That stale cache made the strict, oracle-deriving ``carriage_state_is_canonical``
-(directly, and inside ``_queue_state_is_canonical``) return False, so the
-carriage attach/detach precondition and postconditions rejected it and the
-public actions silently no-opped on *every* path during the one-tick
-window -- even though a carriage op is entirely orthogonal to an unrelated
-Metro's cache. The fix opts the carriage guards into the same
-``allow_stale_bound`` tolerance the checkpoint verifier uses; the target
+(directly, and inside ``_queue_state_is_canonical``) return False, so every
+canonically-gated fleet action silently no-opped on *every* path during the
+one-tick self-healing window -- even though the action is entirely orthogonal
+to an unrelated Metro's cache.
+
+``TestCarriageOpsTolerateStaleCache`` pins the carriage attach/detach fix
+(GM-07b:D). ``TestFleetOpsTolerateStaleCache`` pins its locomotive twin
+(GM-07b:E): ``assign``/``queue``/``cancel`` opt into the same
+``allow_stale_bound`` tolerance the checkpoint verifier uses, so the touched
 Metro's own post-reconcile cache stays strictly oracle-bound, an unrelated
-stale cache is committed-around untouched, and every fleet-management and
-path-lifecycle guard stays strict.
+stale sibling is committed-around untouched (and rolled back verbatim), while
+the automatic ``settle`` reconciler and path-lifecycle removal keep the strict
+default.
 """

 from __future__ import annotations
@@ -27,6 +31,7 @@ from typing import Any

 sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

+from entity.metro import Metro
 from env import MiniMetroEnv
 from fleet_management import _queue_state_is_canonical
 from fleet_validation import carriage_state_is_canonical, service_cache_is_canonical
@@ -168,15 +173,172 @@ class TestCarriageOpsTolerateStaleCache(unittest.TestCase):
         self.assertIs(sibling._station_service_action, stale_cache)
         self.assertIn(sibling, _stale_bound_metros(mediator))

-    def test_fleet_and_queue_guards_stay_strict(self) -> None:
-        # The opt-in is scoped: the shared invariants keep their strict default,
-        # so fleet-management/path-lifecycle guards are unaffected.
+
+class TestFleetOpsTolerateStaleCache(unittest.TestCase):
+    def test_reachable_stale_window_now_permits_assign(self) -> None:
+        # The headline repro: two locomotives are free but the strict gate on
+        # an unrelated Metro's stale cache rejected assignment on every path.
+        mediator = _reach_stale_window()
+        path = mediator.paths[0]
+        stale = _stale_bound_metros(mediator)
+        self.assertEqual(len(stale), 1, "seed-9 must have exactly one stale Metro")
+        stale_metro = stale[0]
+        stale_cache = stale_metro._station_service_action
+        self.assertFalse(_queue_state_is_canonical(mediator))
+        self.assertTrue(_queue_state_is_canonical(mediator, allow_stale_bound=True))
+        self.assertEqual(mediator.num_metros - len(mediator.metros), 2)
+
+        before = len(mediator.metros)
+        self.assertTrue(mediator.can_assign_locomotive(path))
+        self.assertTrue(mediator.assign_locomotive(path))
+        self.assertEqual(len(mediator.metros), before + 1)
+        # Assign appends a fresh off-station Metro and never touches the
+        # unrelated stale sibling, whose cache is preserved verbatim.
+        self.assertIs(stale_metro._station_service_action, stale_cache)
+        self.assertIn(stale_metro, _stale_bound_metros(mediator))
+
+    def test_reachable_stale_window_now_permits_queue(self) -> None:
+        # Case A: the queue candidate IS the stale Metro (empty at a station);
+        # queueing clears its cache and immediately detaches it, self-healing
+        # the window. The strict gate used to reject candidate selection.
+        mediator = _reach_stale_window()
+        path = mediator.paths[0]
+        self.assertEqual(len(_stale_bound_metros(mediator)), 1)
+        before = len(path.metros)
+
+        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
+        self.assertTrue(mediator.queue_locomotive_unassignment(path))
+        self.assertEqual(len(path.metros), before - 1)
+        self.assertFalse(_stale_bound_metros(mediator))
+
+    def test_cancel_commits_while_an_unrelated_metro_stays_stale(self) -> None:
+        # Case B: an occupied non-stale Metro was queued earlier (the canonical
+        # waiting-to-empty state a prior queue produces); the unrelated empty
+        # sibling holds the reachable stale cache. Cancelling must commit --
+        # rebinding the touched Metro's own cache strictly -- while the
+        # sibling's stale cache is preserved verbatim.
+        mediator = _reach_stale_window()
+        path = mediator.paths[0]
+        stale = _stale_bound_metros(mediator)
+        self.assertEqual(len(stale), 1)
+        stale_metro = stale[0]
+        stale_cache = stale_metro._station_service_action
+        queued = next(metro for metro in path.metros if metro is not stale_metro)
+        self.assertTrue(queued.passengers, "the Case-B queued Metro is occupied")
+        queued.is_unassignment_queued = True
+
+        self.assertFalse(_queue_state_is_canonical(mediator))
+        # The public per-path count reflects the queued Metro despite the stale
+        # sibling (it used to read a spurious 0 through the strict gate).
+        self.assertEqual(mediator.queued_locomotives_for_path(path), 1)
+        self.assertTrue(mediator.can_cancel_unassignment(path))
+        self.assertTrue(mediator.cancel_unassignment(path))
+
+        self.assertIs(queued.is_unassignment_queued, False)
+        # The Metro the transaction touched is strictly oracle-bound: its own
+        # postcondition was NOT relaxed.
+        self.assertTrue(
+            service_cache_is_canonical(mediator, queued, allow_unbound=False)
+        )
+        # The unrelated sibling's stale cache survived untouched.
+        self.assertIs(stale_metro._station_service_action, stale_cache)
+        self.assertIn(stale_metro, _stale_bound_metros(mediator))
+
+    def test_queue_fast_path_detaches_while_unrelated_metro_stays_stale(self) -> None:
+        # Case B for the immediate-detach fast path: the queue candidate is an
+        # empty at-station non-stale Metro while an unrelated sibling holds the
+        # stale cache. The fast-path detach must remove the candidate and
+        # commit-around the sibling untouched.
+        mediator, path, sibling = _sibling_stale_state()
+        stale_cache = sibling._station_service_action
+        self.assertIn(sibling, _stale_bound_metros(mediator))
+        before = len(path.metros)
+
+        self.assertTrue(mediator.can_queue_locomotive_unassignment(path))
+        self.assertTrue(mediator.queue_locomotive_unassignment(path))
+        self.assertEqual(len(path.metros), before - 1)
+        self.assertIs(sibling._station_service_action, stale_cache)
+        self.assertIn(sibling, _stale_bound_metros(mediator))
+
+    def test_assign_rejects_and_rolls_back_an_effectful_factory(self) -> None:
+        # Defense in depth (mirrors carriage attach): assign snapshots the full
+        # state, so a factory that mutates an unrelated sibling's cache to
+        # another structurally-valid, still-live action -- which allow_stale_bound
+        # would accept in isolation -- is caught by the identity snapshot and the
+        # whole state is restored verbatim. assign never commits a modified
+        # sibling, and the reachable public factory (a pure Metro constructor)
+        # can never trigger this.
+        mediator = _reach_stale_window()
+        path = mediator.paths[0]
+        stale = _stale_bound_metros(mediator)
+        self.assertEqual(len(stale), 1)
+        sibling = stale[0]
+        original_cache = sibling._station_service_action
+        live_passenger = original_cache[1]
+        metros_before = len(mediator.metros)
+        path_metros_before = tuple(path.metros)
+
+        def effectful_factory() -> Metro:
+            sibling._station_service_action = ("transfer", live_passenger)
+            return Metro()
+
+        self.assertFalse(
+            mediator._fleet.assign(
+                mediator, path, get_metro_factory=lambda: effectful_factory
+            )
+        )
+        # No Metro was added and the sibling's cache is restored verbatim.
+        self.assertEqual(len(mediator.metros), metros_before)
+        self.assertEqual(tuple(path.metros), path_metros_before)
+        self.assertIs(sibling._station_service_action, original_cache)
+
+    def test_assign_rolls_back_verbatim_when_factory_raises(self) -> None:
+        # A raising factory leaves the fleet and the unrelated sibling exactly
+        # as they were: full snapshot restore, not just the owner collections.
+        mediator = _reach_stale_window()
+        path = mediator.paths[0]
+        sibling = _stale_bound_metros(mediator)[0]
+        original_cache = sibling._station_service_action
+        metros_before = tuple(mediator.metros)
+        path_metros_before = tuple(path.metros)
+
+        def raising_factory() -> Metro:
+            raise RuntimeError("factory boom")
+
+        self.assertFalse(
+            mediator._fleet.assign(
+                mediator, path, get_metro_factory=lambda: raising_factory
+            )
+        )
+        self.assertEqual(tuple(mediator.metros), metros_before)
+        self.assertEqual(tuple(path.metros), path_metros_before)
+        self.assertIs(sibling._station_service_action, original_cache)
+
+    def test_shared_validators_keep_strict_default(self) -> None:
+        # The opt-in is scoped: the shared validators keep their strict default,
+        # so callers that do not opt in still reject the stale window. Only the
+        # fleet assign/queue/cancel and carriage guards pass allow_stale_bound.
         mediator = _reach_stale_window()
         self.assertFalse(carriage_state_is_canonical(mediator))
         self.assertFalse(_queue_state_is_canonical(mediator))
         self.assertTrue(carriage_state_is_canonical(mediator, allow_stale_bound=True))
         self.assertTrue(_queue_state_is_canonical(mediator, allow_stale_bound=True))

+    def test_settle_stays_strict_under_unrelated_stale_sibling(self) -> None:
+        # The automatic per-tick reconciler is deliberately NOT relaxed: a
+        # queued empty at-station Metro that settle would normally detach is
+        # left in place while an unrelated sibling is stale, so settle never
+        # mutates the fleet around another Metro's transient cache.
+        mediator, path, sibling = _sibling_stale_state()
+        candidate = next(metro for metro in path.metros if metro is not sibling)
+        self.assertFalse(candidate.passengers)
+        candidate.is_unassignment_queued = True
+        self.assertIn(sibling, _stale_bound_metros(mediator))
+
+        self.assertEqual(mediator._fleet.settle(mediator), 0)
+        self.assertIn(candidate, path.metros)
+        self.assertIn(sibling, _stale_bound_metros(mediator))
+

 if __name__ == "__main__":
     unittest.main()
```
