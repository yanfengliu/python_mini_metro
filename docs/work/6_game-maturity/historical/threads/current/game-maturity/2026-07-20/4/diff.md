# GM-05c diff ledger

Status: remotely finalized through exact-green implementation Commit A and evidence-only Commit B

## Production surface

- Added `path_handle_geometry.py`, `path_handles.py`, and `path_handle_input.py` for immutable primitive descriptors, deterministic collision-resolved geometry, weak idle selection, exact-source edit derivation, and thin input transitions.
- Added cache-free `rendering/path_handle_renderer.py`; extended the existing selected-line preview with arbitrary insertion slots, selected/invalid handle feedback, visual-lane-projected removal overlays, and package-safe lazy renderer wiring.
- Extended the stateless input coordinator, facade state, false-to-true game-over cleanup, and desktop letterbox mouse-up routing while reusing the existing public atomic `replace_path` transaction exactly once after transient cleanup.
- Added config-owned handle geometry and rendering constants. Checkpoint, replay, action protocol, reward/history, and path-replacement modules remain unchanged.

## Evidence surface

- Added five focused GM-05c modules with 43 methods plus two live desktop-adapter regressions in `test_main.py`, for 45 GM-05c tests total. They cover pure derivation, real converted events, rendering/cache behavior including active empty-pointer preview integration, actual fast/fidelity CHW observations, canonical state/array/RNG equivalence, game-over cleanup, and letterbox cancellation.
- The full py313 suite passes 719 tests with 12 expected optional-stack skips. The named checkpoint-v1/v2 and recursive/agent-input-v1/v2/v3 compatibility run passes 34 tests.
- The frozen GM-03f differential remains byte-identical at four cases, 90 events, 16 records, 7,123 bytes, and SHA-256 `147f90d827a9b4c3fb17f0aae212e2603c5c6bdc99915a87bbfde29f8d699f05`.
- Protocol, default-task, and fidelity-task fingerprints remain `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and `cd713a6891d8e74dab1aac2ded2edc88a727cb2b5b420948c65731d3a0eb3418`; the intentional source/render change advances content identity to `7a5401c1c901ba7bdfb0283c5e8c482535c9b04d339c4ed0a5d9528944f2bfbc`.
- All 20 changed Python files remain below 500 lines except the explicit 660-line Mediator facade, which remains below the 1,000 hard ceiling. `InputCoordinator` is 476 lines and `GameRenderer` is 477.
- Updated public controls/rules, architecture, progress, parent maturity state/decision/evidence, GM-05b downstream reconciliation, and this iteration's reviewed evidence while preserving unrelated `.agents/`, ignored output/pin state, and the external review boundary.

The exact 38-path stage excludes `.agents/`, ignored output/pin state, dependency/environment/workflow surfaces, and credentials; cached whitespace and unstaged-tracked-drift audits are clean. Implementation Commit A `242f400` passed run `29792200360`; evidence-only Commit B `b5295c0` passed run `29792542962` and was reconciled by GM-06a.
