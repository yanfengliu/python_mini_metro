# GM-05a diff ledger

Baseline: `8c4ba85bfec20916cefa418e8b180a6c16a1f2f6`

Current phase: locally green, independently re-reviewed, and hook-clean on all 35 paths; exact Commit A staging, push, and remote CI pending

The red-first surface began with 27 methods in `test_gm05a_api_replay.py`, `test_gm05a_metro_continuity.py`, and `test_gm05a_passenger_transitions.py`. API/replay recorded 11 expected feature-causal failures with zero errors, metro continuity recorded 13 expected missing-method errors, and passenger transitions recorded 15 expected missing-method/private-replanner errors before any production edit. Reviewer-driven edge and rollback coverage added `test_gm05a_transaction_edges.py`, `test_gm05a_rollback.py`, and direct subcases within the original modules, yielding 40 focused green methods.

Production payload: new dependency-light `src/path_replacement.py`, `src/path_replacement_geometry.py`, and `src/path_replacement_snapshot.py`; updated `src/path_lifecycle.py`, `src/passenger_flow.py`, `src/input_coordinator.py`, and `src/mediator.py`. This supplies the atomic transaction, exact off-live rounded geometry validation, identity-preserving snapshot/rollback, three public selector/facade methods, the structured action branch, and one private late-bound scoped passenger replanner.

Test payload: `test/test_gm05a_api_replay.py`, `test/test_gm05a_metro_continuity.py`, `test/test_gm05a_passenger_transitions.py`, `test/test_gm05a_rollback.py`, and `test/test_gm05a_transaction_edges.py`. Final validation is 40/40 focused and 622/622 full-suite methods with 12 expected optional-stack skips.

Documentation/evidence payload: `README.md`, `GAME_RULES.md`, `ARCHITECTURE.md`, `PROGRESS.md`; parent `DECISIONS.md`, `EVIDENCE.md`, and `STATE.md`; this iteration's `PLAN.md`, `REVIEW.md`, `diff.md`, and available verbatim reviewer outputs plus explicitly labeled recovered summaries under `raw/`.

Final physical line counts are 494 for `path_replacement.py`, 254 for `path_replacement_geometry.py`, 114 for `path_replacement_snapshot.py`, 293 for `path_lifecycle.py`, 494 for `passenger_flow.py`, 432 for `input_coordinator.py`, 652 for `mediator.py`, and 455/411/499/197/406 for the five new test modules. Every changed handwritten file remains below the 1,000-line ceiling, and every new/extracted focused file remains below 500 lines; the explicit facade remains 652 lines because its real public methods and canonical state stay visible.

The final Commit A transaction contains 35 exact paths after six implementation-review records are added. `.agents/`, ignored `output/`, the retained civ-engine pin, the unrelated sibling, the pre-existing setup lease, and the four ACL-blocked ignored cache roots remain outside the transaction.
