# GM-07a plan narrow recheck — verdict: CLEAN (verbatim)

All eight findings are genuinely closed by the revision, and the end-to-end read found no fresh contradiction with the live code.

- F1 closed: per-instance lazy store, class-default prohibition with leak rationale, named bare-instance red. Feasibility confirmed against `test_mediator_input_contract.py:16-21,393` and `scripts/input_coordinator_differential_support.py:86-93`; properties are class-level so bare `__new__` hosts work; the Space path reads-then-writes through the lazy store.
- F2 closed: main-owned construction closure, controller invokes-only, per-frame triple read, menu-restart red named. Seams verified: the four direct-call tests patch `main.*` (resolved at call time by a main-level closure); the runpy test patches source modules, which the closure picks up because `runpy.run_module` re-executes main's imports under the patches.
- F3 closed: cancel dispatched first, hold after, mid-drag red named. Cancel semantics verified: `(-1,-1)` conversion pinned (test_main.py:83-118); handle drag → `PathHandleEdit.result` None via the identity check (`path_handles.py:260`) → clear, no `replace_path`; redraw → outside-viewport clear (`input_coordinator.py:268-269`); creation → `abort_path_creation`; `_apply_release_target` unreachable at `(-1,-1)`. Ordering wording explicit, so no conflict with the no-dispatch-while-menu rule.
- F4 closed and exhaustively verified: exactly five `run_game` call sites; all four direct tests pass `max_frames=1` and the `__main__` hook passes `max_frames` from the env var; auto-PLAYING on `max_frames is not None` covers all five with zero edits; explicit `start_state` override stated.
- F5 closed: eager triple on TITLE pinned.
- F6 closed: plan commits to an explicit parent `DECISIONS.md` line within the transaction.
- F7 closed: exact-`bool` pinned in the model bullet and the red-test step; the missing-store getter returns a genuine `False`, so F1 and F7 compose.
- F8 closed and authoritatively verified: live git `main == origin/main == 325a055` (parent `62d26a2`); GitHub API confirms run 29893673381 = #147 head `325a055` success (build 88839134989, rl-smoke 88839134985) and run 29893340731 = #146 head `62d26a2` success. Every SHA, run number, and job ID matches.

Fresh-contradiction sweep clean: eager-TITLE coexists with the F2 seam; once-only construction assertions still hold; remaining anchors (`set_paused` at mediator.py:582, `transition_active` at 625, game-over transient clear at 715-719, Escape only in the game-over branch at main.py:54) all match live code. The review's unnumbered cosmetic item (pause speed-button lit behind the menu) was scoped out of the fold and is not a gap.
