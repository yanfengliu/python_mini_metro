Findings first:

- High — A stateful aggregate with mirrored `Mediator` fields is not credible here. Writable/rebindable fields such as `paths`, `metros`, `path_being_created`, and the path maps are used directly throughout tests and runtime. Forwarding even five fields costs about 40 mediator lines before wrappers, making the below-1,000 gate unlikely without scope creep or magic delegation.
  - Correction: use a stateless, non-retaining `PathLifecycle` and pass an explicit ephemeral `PathLifecycleHost` protocol per call. `Mediator` remains the sole canonical state/public facade; the component owns lifecycle behavior but stores no host, collection, entity, callback, or cache between calls.

- High — The exact size budget must be frozen. The 12 lifecycle methods occupy 168 physical lines at `5e6186d`: `assign_paths_to_buttons` (9), `remove_path` through `finish_path_creation` (137), and `end_path_on_station` (22). GM-03d needs a net reduction of at least 111 lines.
  - Correction: cap all replacement wrappers plus the lifecycle import/installation at 57 lines; target 45 or fewer, which projects `mediator.py` near 986 lines. Do not pull `apply_action`, mouse/layout handling, or passenger movement into scope merely to satisfy the gate.

- High — Naive delegation will break observable lookup and mutation order. Current methods repeatedly re-read mutable `paths`, `metros`, `passengers`, `travel_plans`, path maps, and creation state; they dynamically dispatch public methods after prior effects.
  - Correction: the component must operate on the ephemeral host and retain the original expressions/order. Do not cache `host.paths`, mappings, current path, or bound public methods across effect points. Calls such as `host.finish_path_creation()` and `host.invalidate_travel_plans_for_path(path)` must remain public-to-public dispatch.

- High — Importing `Path` and `Metro` into the new module changes monkeypatch/global-resolution timing.
  - Correction: pass factory getter thunks from the facade and invoke them only at the original construction points, e.g. direct getter-call composition. Characterize `mediator.Path` and `mediator.Metro` replacement before production moves.

- High — Removal is an atomic lifecycle cascade, not merely `paths.remove`.
  - Correction: preserve, in order, button clearing; `list(path.metros)` and `list(metro.passengers)` snapshots; passenger/global-plan cleanup; metro cleanup; public invalidation; color release; path removal; button reassignment; and public replanning. Preserve partial state if any hook/factory raises.

- Medium — Existing path tests are insufficient for this extraction.
  - Add baseline-green facade tests for:
    - public callback overrides and call order;
    - `paths` rebinding between `len` and index access;
    - map/list rebinding during button assignment, invalidation, and removal;
    - Path/Metro factory lookup timing and partial failures;
    - exact created `Path`/`Metro` identity and one-time insertion;
    - existing empty/surviving travel-plan identity;
    - loop/abort/finish state and snap-blip timing;
    - snapshot versus live-iteration behavior;
    - direct writable creation-state compatibility.
  - Then add expected-red direct `PathLifecycle` tests before creating the module.

- Medium — Avoid nested/materialized proposal helpers unless their lifetime behavior is proven. GM-03c already showed that extra generator frames and retained callables can change destructor-driven state.
  - Correction: move each method body nearly verbatim into the stateless helper, using the host at each original read. Add weakref/destructor probes around factory/callback and replaced-collection lifetimes, plus actual baseline/current differentials for any refactoring that introduces a generator.

Recommended scope:

- Extract exactly these 12 methods into `src/path_lifecycle.py`: `assign_paths_to_buttons`, `remove_path`, `invalidate_travel_plans_for_path`, both remove selectors, start/create/add/abort/release/finish/end creation.
- Keep `generate_distinct_path_colors`, `react_mouse_event`, `apply_action`, layout, general passenger flow, route planning, and progression in their existing owners.
- Keep every public `Mediator` name/signature as a real explicit wrapper.
- Keep the new module and every new test file below 500 lines.

Verification should include exact AST signature comparison for all 12 methods; focused lifecycle/interaction/env/routing/passenger/checkpoint/render tests; a topology-specific baseline/current action differential covering non-loop, loop, abort, removal by ID/index, onboard cleanup, waiting-plan invalidation, RNG state, structured observations, and canonical checkpoints; full py313 and exact-RL suites; Ruff/format/pre-commit; dependency-light import proof; fingerprints; and the hard line counts.

Durability:

- New iteration path is `docs/threads/current/game-maturity/2026-07-14/1/`; numbering restarts for the new date, and no matching current/done directory exists.
- Update parent `STATE.md`, `EVIDENCE.md`, `DECISIONS.md` with the lifecycle boundary, plus `ARCHITECTURE.md`, `PROGRESS.md`, iteration `PLAN.md`, `REVIEW.md`, `diff.md`, prompts, and raw reviews. README/GAME_RULES should remain unchanged if behavior/API do.
- Commit A: implementation, tests, architecture/progress, state/evidence, and review artifacts; push and wait for exact `build` and `rl-smoke`.
- Commit B: evidence-only A SHA/run/durations and cursor advance; push and wait for exact B CI. GM-03e’s opening evidence records B’s result.

No technical blocker remains if the stateless ephemeral-host boundary and 57-line hard envelope are adopted. External multi-CLI review remains unlaunched under the existing repository-context-transfer restriction; use the required in-process adversarial lanes and record that limitation.
