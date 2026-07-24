# GM-09c plan — dual adversarial review synthesis

Both lanes (harness + external Codex ultra) went NOT CLEAN and both VERIFIED the two load-bearing decisions CORRECT: the derived-count rollback/refund (free with no snapshot field — the intricate route-edit transaction is untouched) and the centerline determinism (`PathSegment` geometry is `path_order`-offset + round-quantized, unusable). The crossing test is empirically anchored (`raw/crossing-feasibility.md`).

- Harness (`raw/plan-harness.md`, NOT CLEAN): full file:line trace; 1 MAJOR (checkpoint-v4 break via the fleet dict) + M1-M3/N1-N3.
- Codex ultra (`raw/plan-codex.md`, NOT CLEAN): corroborated the checkpoint break + draft-counting; ADDED the two-station-loop double-charge and the snap-blip leak on rejected creation. (Codex's `-o` write failed — second flaky Codex output this session — so its detailed evidence was captured from the run summary; the harness lane's independent trace covers the same surface with file:line evidence. Flagged.)

## Findings + dispositions (all folded into PLAN.md v2)
- MAJOR (both) — tunnels in the `fleet` dict break v4 checkpoint for all maps. FOLD: sibling `structured["tunnels"]` block + RIVER-env checkpoint coverage.
- MAJOR (Codex) — two-station loop double-charges (retrace). FOLD: add the loop-closure segment only when `len(stations) >= 3`.
- MAJOR (Codex) — rejected creation leaks snap-blip state. FOLD: route the gate rejection through the clean `abort_path_creation`; test `canonical_checkpoint` valid after a rejected creation.
- Both — drafts counted as live. FOLD: exclude `is_being_created` from `consumed_tunnels`; finish gate adds the finishing path's crossings.
- Harness M1 — gate in `replace_path` after `_normalize` (needs `loop`), guarded by `if num_tunnels is not None`.
- Harness M3 — validate `tunnel_budget`.
- NITs — tangency tie-break, per-crossing semantics, empirical budget solvability.

## Result
NOT CLEAN → all folded into a v2 plan; the two highest-risk decisions are dual-verified correct. Ready for red tests.

---

# GM-09c implementation — dual adversarial review synthesis

The two lanes SPLIT hard, and the external lane again earned its keep (5th time this session — see the review-coverage memory lesson). The harness lane rated it SHIP; the Codex lane REJECTed with 3 MAJORs, 2 of which the harness missed entirely (a clean-object API-only pass never called the internal commit primitive directly or swapped the map post-construction).

- Harness (`raw/impl-harness.md`, **SHIP**): read all live files, ran the full suite, wrote 3 determinism/rejection/checkpoint probes. Verified the load-bearing derived-count determinism (round() is post-count, centerline-based, lane-offset-independent) and CLASSIC byte-identity (RNG + checkpoint + frame). Found 1 MINOR (M1: multi-station rejected-creation snap-blip leak) + 2 NITs.
- Codex ultra (`raw/impl-codex.md`, **REJECT**): read all live files + ran probes through the `env.step` action API. 3 MAJORs + 2 MINORs.

## Findings + dispositions (all folded)
- MAJOR (Codex; harness MISSED) — **commit-boundary bypass**: `finish_path_creation` (the public primitive that clears `is_being_created`) had no budget check, so a direct `start/add/finish` committed a 4th crossing over a budget of 3. Reproduced (`consumed==4`). **FIXED**: gate `within_tunnel_budget` at `finish_path_creation` before the commit, aborting over-budget; kept the entry-point preflights for clean early rejection. Regression: `test_direct_finish_cannot_bypass_the_budget`.
- MAJOR (Codex; harness MISSED) — **cached-budget fail-open**: `num_tunnels` was cached from `map_definition.tunnel_budget` in `__init__` while `consumed_tunnels` read `map_definition.rivers` live; a CLASSIC→RIVER map swap left `num_tunnels=None` and accepted 4 crossings. Reproduced. **FIXED**: `num_tunnels` is now a derived @property, and `within_tunnel_budget` reads the budget from `map_definition` (single source, same as `rivers`). Regression: `test_num_tunnels_is_derived_from_the_map_not_cached`.
- MAJOR (Codex) / MINOR (harness M1) — **rejected multi-station creation not atomic**: `create_path_from_station_indices([2,0,1])` at budget 0 leaked an intermediate snap-blip (checkpoint `snap_blips 3→4`) before the `end_path_on_station` gate. **FIXED**: upfront pre-check in `create_path_from_station_indices` before `start_path_on_station`. Regression: `test_rejected_multistation_creation_is_fully_inert` (whole-checkpoint equality before/after).
- MINOR (Codex) — **boundary-grazing counted**: a positive-length segment collinear with a band EDGE, or a zero-length interior segment, counts. **DOCUMENTED as unreachable** for the current eroded-bank maps (centerlines are inset from the river edge by `station_size`; consecutive stations are distinct) in `segment_crosses_band`; strict-interior semantics deferred (with a test) to the first map that can place a line along a river edge. No geometry change near delivery (regression risk, zero reachable benefit).
- MINOR (Codex) — **bare `action_ok=False`**: tunnel-exhaustion rejection is indistinguishable from malformed input. **DOCUMENTED**: README create/replace failure conditions now name the tunnel-budget rejection and point to the `tunnels` observation block (`available==0`) for diagnosis. A structured-reason channel for ALL create/replace rejections (not just tunnels) is a broader follow-up beyond GM-09c's scope — noted, not silently dropped.
- Harness N1 (test gaps) — **FIXED** by the three regression tests above. N2 (tunnels in CLASSIC `structured`) — by-design sibling block, suite-green.

## Round 2 — re-review of the three fixes (both lanes NOT clean)
Both lanes independently caught that the round-1 create-path PRE-CHECK mis-predicts the route: harness (1 MAJOR + 1 MINOR), Codex `raw/impl-codex-rereview.md` (3 MAJORs). The other two round-1 fixes (`num_tunnels` property, commit-boundary gate) were re-verified CLEAN by both.

- MAJOR (both) — the raw-index pre-check counts an explicit-closure loop `[X,Y,X]` as a two-crossing round trip, but it builds the 2-station loop `[X,Y]` (one crossing) → a within-budget loop is FALSE-REJECTED. Codex also showed the mirror: `[0,1,0,2]` builds `[0,1,2]` looped (2 crossings) but the pre-check counts 1 → false-accept, then the end gate rejects with a leaked snap-blip.
- MAJOR (Codex) — `abort_path_creation` after an intervening `remove_path` (which reassigns buttons and binds the in-progress draft) leaves a colored ghost-line button.
- MINOR (harness) — an over-budget abort (interactive drag or direct bypass) leaks the intermediate `add_station` snap-blip; the rejection is not fully inert.

### Disposition (root-cause rework, not a patch): probe proved building-then-aborting a draft draws NO RNG — the only non-inert side effect is the snap-blip, and `end_path_on_station`/`finish_path_creation` already count the REAL draft correctly. So the fix REMOVES the fragile pre-check entirely and makes abort inert:
- **Removed** the create-path pre-check → both route-prediction MAJORs gone; the gates count the resolved draft. Regression: `test_explicit_closure_loop_is_not_false_rejected` (a `[2,0,2]` loop at consumed 2 now commits, total 3).
- **Clean abort** — `abort_path_creation` drops the draft's own snap-blips by its unique color → every rejection (create, interactive, direct) is checkpoint-inert. Regression: `test_rejected_multistation_creation_is_fully_inert`.
- **Ghost button fixed at the SOURCE** — `assign_paths_to_buttons` skips a still-drafting path, so a draft never holds a button (rather than making abort reconcile buttons, which broke the abort contract test). Regression: `test_abort_after_intervening_removal_leaves_no_ghost_button`.
- The abort rework initially broke two pre-existing contract tests (the live-rebinding re-read + "abort emits no button-reassign"); both were honored by re-reading `path_being_created` AFTER the release hook and keeping the button fix out of abort — a signal (per the review-coverage lesson) that the first fix attempt was in the wrong layer.

Empirically re-verified: all three round-2 counterexamples fixed, CLASSIC byte-identical (loop + abort inert), interactive over-budget inert, full suite 1403 OK.

## Round 3 — re-review of the abort/pre-check-removal rework (both lanes FIX-FIRST, converged)
Both lanes independently CONFIRMED the round-2 core is correct — the count invariant cannot be bypassed, the gate counts the real resolved draft (explicit-closure `[X,Y,X]`, mid-repeat `[0,1,0,2]` all correct), `num_tunnels` derived, no over-budget commit — and both flagged the SAME single defect: the round-2 clean-abort broke CLASSIC byte-identity.

- Harness (`raw/impl-harness-rereview` task, FIX-FIRST): 1 MAJOR — `abort_path_creation`'s color-matched blip clearing over-matches a removed line's reclaimed-color blip and, more fundamentally, HEAD's abort never touched `snap_blips`, so a CLASSIC drag-then-cancel now yields a different checkpoint/frame. Everything else verified correct.
- Codex (`raw/impl-codex-rereview3.md`, FIX-FIRST): 3 MAJORs, all the same root cause — (a) color-reclaim blip over-match on RIVER, (b) CLASSIC abort blip-clear breaks byte-identity, (c) the draft-skipping button pass changes CLASSIC's button mapping bytes. + 1 MINOR (release-hook rebind + pre-hook blip ownership).

### Disposition — REVERT the cleanup (re-disposition per the review-coverage lesson: folding a "leak" fix into shared methods broke a load-bearing invariant, so the fix was in the wrong place). `abort_path_creation` and `assign_paths_to_buttons` are restored BYTE-FOR-BYTE to pre-GM-09c (verified: absent from `git diff origin/main`). GM-09c now changes ONLY the two gates (which short-circuit on CLASSIC's `None` budget), so CLASSIC is byte-identical. A rejected creation is count-, path-, and RNG-inert; the transient snap-blip it may leave (and the ghost-button after a mid-draft removal) are PRE-EXISTING abort behaviors present in HEAD, not introduced here — spun off to a focused follow-up (`task_384488d0`) that must fix them with owned-blip tracking / byte-preserving button handling. Tests updated: `test_rejected_multistation_creation_commits_and_draws_nothing` asserts the real guarantees (no crossing, no ghost path, no RNG draw) rather than full checkpoint equality; the ghost-button test was removed with its fix.

Empirically re-verified after the revert: cross consumes 1; over-budget 4th rejected; explicit-closure loop accepted; direct-finish bypass blocked; rejection count/path/RNG-inert; CLASSIC unchanged. Full suite 1403 OK.

### Round 4 judged unnecessary
The round-3 finding is definitively resolved by a VERIFIABLE revert (abort/assign byte-identical to HEAD — provable by diff, not by re-review), and it did not touch the core both lanes verified correct across all three rounds (the gates + derived count + crossings geometry). A fourth dual-review would re-confirm the same core and the revert, converging on no new information; the residual pre-existing issues are tracked in `task_384488d0`.
