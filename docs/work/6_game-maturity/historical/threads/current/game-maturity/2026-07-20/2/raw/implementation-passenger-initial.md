# Passenger, RNG, and rollback implementation review - initial and corrective outputs

The reviewer reported that context compaction removed the exact wording of the earliest messages, so those seven points cannot honestly be labeled verbatim. Their recovered chronological content was:

1. Shared `TravelPlan.node_path` storage let one marker rewrite corrupt another plan.
2. Shared path topology-list storage let replacing the target mutate another path’s stations while leaving its geometry stale.
3. Aliasing a target write list with a host/holder list let replacement insert geometry objects into global passengers.
4. A candidate list aliased to host passengers was mutated before the rollback snapshot, causing an exception and unrecoverable live-state corruption.
5. Malformed candidate geometry—including wrong loop state and geometry lists rebound to live target storage—could commit.
6. Direct `PassengerFlow.replan_passenger_at_station` coverage and the four-field empty-marker assertion were missing.
7. The first geometry validator rejected a valid nonzero-order, zero-length exact no-op.

The following retained messages are verbatim and chronological.

## Retained output 1

Fresh post-fix reread: one remaining test-coverage gap already visible. `test_marker_alight_dispatches_one_scoped_fresh_route` wraps the marker resolver at test/test_gm05a_passenger_transitions.py:311-313 but does not assert the exhausted marker’s four fields are empty at that effect point. The only four-field assertions are in the replacement-time stable-waiting test (148-153, where plans were initialized empty) and the direct helper test (348-352); neither proves PLAN.md:55’s reset-before-marker-resolver ordering. Production `PassengerFlow.move_passengers` currently does reset fields at 384-387 before calling at 388, but the exact contract lacks a regression assertion.

## Retained output 2

Rollback probe for the PLAN.md:74 multi-waiter boundary passed: first waiter completed a fresh route/plan replacement, second waiter faulted, then canonical checkpoint, both original TravelPlan identities, and both RNG streams restored exactly. However no committed GM05a test covers this distinct required fault point: rollback.py has candidate-init, graph, arrival-removal, and partial-search faults; transaction_edges has topology and first-metro faults. PLAN lists “first scoped waiting plan” separately from partial route and arrival removal. Recommend adding the proven two-waiter first-success/second-fault regression.

## Retained output 3

Fresh focused rerun against the live post-refactor tree now fails 2/4: `test_valid_noop_preflights_but_resolves_no_effect_collaborators` line 98 returns False for the new angled exact no-op, and `test_factory_cannot_return_or_alias_a_live_path` line 210 expected invalid candidate but no ValueError was raised. Marker ordering and alias suite pass. This appears to be a live validator/test update after my prior 72-test green run; I’m inspecting the exact new cases now.

## Retained output 4

The live tree is currently mid-edit: `src/path_replacement_geometry.py` disappeared between my reads (status now no longer lists it) while `src/path_replacement.py` still imports it, so further test/audit results would be transient. Ping me when your geometry refactor is stable and I’ll do the final fresh pass.

## Retained output 5

Post-fix live verification: all 73 GM05a + adjacent passenger/facade/effect tests pass. Scoped `ruff check` passes. Scoped `ruff format --check` still reports 5 files needing format: `src/mediator.py`, `src/path_replacement.py`, `src/path_replacement_geometry.py`, `test/test_gm05a_passenger_transitions.py`, `test/test_gm05a_rollback.py` (consistent with your note that formatting was pending).
