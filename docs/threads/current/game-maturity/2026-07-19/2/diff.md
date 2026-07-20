# GM-03f reviewed diff

## Production boundary

- Add dependency-light, stateless `InputCoordinator` with a call-scoped structural host and original-expression resolver thunks for facade-owned pygame values, numeric layout configuration, helpers, factories, renderer, event classes, and entity classes.
- Replace the 19 frozen `Mediator` algorithm bodies with exact-signature real wrappers while keeping canonical UI collections, layout rectangles, compatibility renderer, progression, topology, clocks, input flags, pause/speed/game-over state, and all public effects on the facade.
- Reduce `src/mediator.py` from 735 to 605 physical lines; keep `src/input_coordinator.py` at 391 lines without retained state or game-domain runtime imports.

## Verification boundary

- Preserve the isolated import-only missing-module red, make the final 10-test facade characterization replayable and green against both archived baseline and candidate, and add 12 direct/edge component tests. The combined direct, edge, and facade surface passes 22/22 and line tracing exercises every executable coordinator body statement.
- Add a non-mutating archived-baseline differential runner split across five sub-500-line files plus one canonical artifact and digest summary. Exact baseline, candidate, and `--expected` replay are equal at 7,123 bytes with SHA-256 `147f90d827a9b4c3fb17f0aae212e2603c5c6bdc99915a87bbfde29f8d699f05` across four cases, 16 records, and 90 mutation-sensitive events; exact-path `.gitattributes` rules preserve those LF bytes through a clean Windows `core.autocrlf=true` checkout and external-output replay.
- Core validation passes 582 tests with 12 expected optional-RL skips; the exact RL environment passes 585/585 without skips. Protocol, task, history, and training fingerprints remain unchanged; the content fingerprint changes intentionally with the new runtime source boundary.

## Review and documentation

- Resolve every in-process plan and implementation finding, including late numeric/type lookup, Python bound-method evaluation order, subclass and dual-class precedence, index identity/`bool` behavior, speed truth tables, uncovered short circuits, live collection replacement, and baseline replay. Both final implementation lanes returned `CLEAN`.
- Record decision D-015 and update architecture, progress, cursor, evidence, plan, review, and raw reviewer surfaces. The fleet-pinned external launch remained unavailable at the repository-export authorization boundary, so no external approval is claimed.
- Change no dependency declaration, workflow, gameplay rule, public signature, protocol/task/history/training contract, reward, observation, checkpoint, recursive schema, or renderer behavior. Preserve and exclude the pre-existing untracked `.agents/` tree and unrelated ignored `output/` evidence.
