# GM-03c review synthesis

## Plan review

Three independent in-process live-code lanes mapped the ownership boundary, hidden mutation/RNG/identity contracts, TDD coverage, documentation, and the hard below-baseline size recovery. The code lane showed that search-only extraction would miss the size gate; the refuter added the lazy constrained-boarding proposal boundary and then found direct callback capture would break per-iteration rebinding; the documentation lane found missing size allocation, absent-path short-circuit coverage, fingerprint/import/oracle proof, and convergence artifact accuracy.

The first corrected plan still had three substantive code-lane gaps: the boarding yield could lose or recompute the one newly built plan, search plus boarding alone did not credibly fit the hard line budget, and constrained/bulk graph lookup order differed in an unrecorded way. The next version still budgeted its seven wrappers impossibly and did not distinguish constrained-plan wiring from bulk hook visibility. The plan now defines exact lazy boarding/bulk contracts, wires only factory-created unowned constrained plans in the planner, installs bulk plans before the public next-hop hook, uses fresh plan-map resolvers for live field updates, allocates a credible 95-96 total replacement lines, and freezes mapping lookup order. The refuter's empty-sentinel identity guard is also explicit.

All three independent reviewers approved the corrected plan after the final retry prompts were synchronized. Plan finding status: no unresolved high- or medium-severity defect; characterization and expected-red direct contracts may begin.

## External reviewer boundary

Task-specific pinned Codex and Claude prompts are preserved. The platform previously prohibited exporting repository plan/code context without separate post-disclosure authorization; the user's later approval covers pre-commit, Git commit/push, and GitHub CI, not external repository-context transfer. Neither external reviewer is launched and the transfer is not rerouted. In-process live-code convergence is the plan authority.

## Implementation review

The first implementation introduced dependency-light `RoutePlanner` query/selection helpers and lazy boarding/bulk proposal iterators while retaining Mediator's public methods and mutation. Direct query, selection, and iterator modules each first failed only with the expected missing-module error. Baseline-green facade tests froze public dispatch, graph/map lookup order, RNG use, live-list mutation, plan ownership, and sentinel identity before production moved.

Four adversarial correction rounds followed. Every finding was checked against the live baseline before a fix:

| Severity | Finding | Reproduction and disposition |
| --- | --- | --- |
| High | Mutable `metro.path_id` and required-first `Path.id` were captured before their original comparison points | Six direct/facade rebinding tests reproduced the drift. ID resolver thunks now run only at the original short-circuited reads. |
| High | A `travel_plans` mapping object was retained across baseline membership/index accesses | Mapping-rebind tests failed before correction. Fresh contains/get/field resolver thunks now re-read the Mediator attribute at each original access. |
| High | The facade remeasured a selected route and used reduced length as arrival provenance | Bounded-`len` and compressed-to-one tests failed. Only raw one-node BFS output now emits `arrival`; `route` and `fallback` are explicit proposal kinds and the facade never calls `len(route)`. |
| High | Arrival mutation occurred after destination-iterator finalization and skipped the original post-arrival fallback guard | Generator-finalizer and delete-hook tests failed. The iterator yields arrival while selection is suspended, resumes to finalize destinations, then emits fallback for the same passenger before advancing the live passenger list. |
| High | Reducer/shared/factory lookup happened after `list(raw)`, `reduced[1]`, or `selected[1:]` argument effects | Three resolution-order tests failed. Getter-call composition resolves the temporary callable first, matching Python's original call evaluation. |
| Medium | Closing the nested selector released yielded destinations and prior raw/reduced route locals before facade route/fallback effects | Actual `HEAD` differentials and two destructor-side-effect tests proved map-state drift. Bulk selection now executes in the proposal generator frame, retaining the same function locals through facade effects while preserving iterator-finalization order. |
| Medium | Assigning resolved reducer/shared/factory callables to planner locals retained them beyond the original call | Four facade/direct destructor tests failed and actual `HEAD` differentials changed plan presence. Direct getter-call composition releases each temporary callable immediately after invocation. |

## Final convergence

Three independent post-fix live-code lanes returned `CLEAN`:

- arrival/provenance/finalizer/local-lifetime lane: 36 targeted tests and the original ephemeral-destination differential matched `HEAD`;
- resolution/map/path/factory/boarding lane: 55 targeted tests and both prior actual-HEAD differentials matched;
- broad code/test/import/size lane: all four callable-lifetime HEAD differentials matched, no algorithm drift was found between direct and bulk selection, and no correctness, typing, import, leak, or coverage defect remained.

The in-frame bulk loop intentionally repeats the small selection kernel used by the direct helper. Factoring it back through a nested generator would reintroduce the proven Python-frame lifetime regression; direct and bulk ranking/provenance behavior is jointly pinned instead.

## Local validation

- Focused route-planning compatibility: 144/144 passed in 1.066 seconds.
- Full py313 core: 509 tests passed with 12 expected optional-RL skips in 6.972 seconds.
- Full exact-RL environment: 512/512 passed in 12.845 seconds.
- Ruff check and format: all nine changed Python files passed.
- Seeded differential: 2,400 outcomes and 44 canonical checkpoints match baseline, with four deliveries and no game over.
- API/import/identity: all nine public Mediator route signatures match; fresh `route_planner` import remains pygame/domain-free; protocol/task/training fingerprints are unchanged and final content fingerprint is `548d2fbd7a28abeec2ae45ef1c64e5239bc6ff5c7e2d1540336a12ee7c813394`.
- Size: Mediator is 1,110 lines, RoutePlanner is 231, and every changed test is below 500.

Changed-path pre-commit passed all hooks across the 37-file intended unit without rewrites. The complete cached audit covered 37 files with 2,955 insertions and 152 deletions; cached diff check, high-confidence credential scan, dependency-declaration scan, and `.agents/`/`output/` exclusion checks all passed.

## Remote implementation gate

Commit A `1b751e47cd3edce3556b32880a26851db3a072d2` passed exact [run 29351838271](https://github.com/yanfengliu/python_mini_metro/actions/runs/29351838271): `build` completed successfully in 34 seconds and `rl-smoke` in 3 minutes 43 seconds. Evidence-only Commit B is the remaining GM-03c transaction.
