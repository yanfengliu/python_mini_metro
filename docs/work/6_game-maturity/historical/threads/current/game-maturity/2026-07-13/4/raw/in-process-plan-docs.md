# GM-03c tests and process map

The documentation lane verified baseline `00ea38c`, mediator blob `c6a2f5db97db955fd42e8a58a26b73ed70d89a70`, 1,193 mediator lines, the exact 145-line tail cluster, eight routing tests in the 270-line routing module, and the green 80-test focused/coupling slice.

It identified eight public AST signatures to freeze: `get_stations_for_shape_type`, `find_shared_path`, `passenger_has_travel_plan`, `find_next_path_for_passenger_at_station`, `get_path_by_id`, `get_travel_plan_starting_with_path`, `skip_stations_on_same_path`, and `find_travel_plan_for_passengers`. It required raising/recording overrides because existing tests do not cover most public-to-public dispatch seams.

Required characterization includes shuffled-copy/RNG behavior, ordered first-live-object queries, cached-plan eligibility, next-station clearing, same-list compression identity, raw-before-reduced route cost, strict first-candidate ties, required-first path IDs, loop/in-progress behavior, unreachable retry, adjacent arrival timing, read-only lookahead, transfer/path-removal replanning, and exact mutable TravelPlan fields.

The hard size budget is a reduction of at least 82 lines to no more than 1,111. A search-only extraction is insufficient; the reviewed constrained boarding-planning boundary supplies the additional reduction while general passenger flow stays on Mediator. New planner/test files remain below 500, and all changed tests must be split before crossing that limit.

The lane also required complete iteration prompts/raw reports, parent state/evidence/decision updates, architecture/progress updates, cached-diff/secret/exclusion proof, direct/focused/full/exact-RL/static gates, three adversarial implementation lanes, and the two-commit remote transaction. README and GAME_RULES remain unchanged because neither mechanics nor public API changes.

## Precise-plan findings

The first precise review found four medium gaps: no explicit 178-line source-to-96/85-line replacement budget; no missing-metro-path no-inspection/no-RNG characterization; incomplete training-fingerprint, recursive-oracle, and pygame-free import proof; and an inaccurate untracked-worktree/convergence/prompt state. The plan, state, review synthesis, prompts, and verification matrix were corrected before production work.

The final documentation re-review found the two plan prompts still described the earlier boarding-only boundary and omitted the lazy bulk iterator, 1,110 target/95-96 allocation, constrained-unowned versus bulk-installed visibility, and sentinel identity guard. Both retry prompts were refreshed before convergence.

Final re-review result: **APPROVED**.
