# GM-03c live-code map

The code-map lane verified all eight public tail methods, their callers, graph/BFS and TravelPlan consumers, direct monkeypatch seams, path invalidation, and checkpoint identity use against baseline `00ea38c`.

Its initial narrow recommendation was a stateless planner for station filtering, ordered path queries, cached-plan eligibility, in-place node compression, unconstrained best-route selection, and required-first-path selection. The planner receives fresh graphs plus `bfs` and public facade callbacks. It owns no state and returns exact supplied nodes; Mediator retains RNG, TravelPlan construction, maps, and effects.

The lane estimated that the narrow search-only extraction would leave `mediator.py` around 1,125-1,140 lines, which fails GM-03c's required below-1,112 recovery. That sizing finding blocks the narrow plan by itself and requires the reviewed lazy constrained-boarding planning boundary without moving general passenger flow.

Verified invariants include shuffled candidate tie order, `(raw BFS length, reduced length)` cost, immediate-arrival versus unreachable distinction, exact list mutation/identity in compression, required-first ID comparison, canonical Path identity, fresh ephemeral Node retention, and public/module callback dispatch.

## Precise-plan findings

The first precise review found two high and one medium gap. The lazy boarding contract did not explicitly carry the single newly built `TravelPlan`, risking loss or double RNG/callback work. The size allocation still lacked enough credible extraction while all mutation stayed in the facade, so a second lazy bulk-proposal iterator was required. Finally, constrained planning and bulk planning have different station-node mapping lookup timing, including empty-destination behavior. The plan now specifies the exact boarding tuple/marker/application contract, a lazy bulk proposal applied before resume, an 85-line code-shaped mediator budget, and lookup/exception-order characterization.

The next size review proved the 39-line seven-wrapper allocation infeasible and identified the behavior-neutral correction. The planner may wire a newly factory-created constrained plan before it is owned, but a bulk plan must be installed in `travel_plans` before next-hop hooks run. Moving constrained construction/wiring plus compact live-plan next-hop field logic behind resolver thunks lowers the estimated complete replacement to 95-96 lines, meeting the hard 1,111-line gate without moving collection mutation or unrelated ownership.

Final re-review result: **APPROVED**.
