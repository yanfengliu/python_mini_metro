# GM-06c implementation re-review - simulation, rendering, and UI

Status: `CLEAN`.

Exact 7-carriage real `Path.move_metro` cap route passes all 21 alphas `.109` through `.111` with finite positions, all-pair clearance, and less than `0.1` pixel consecutive-body motion. Turnaround/layout/rebase/stale suites pass 19/19; solver degenerate/infeasible/global-P1 suite passes 3/3; broader render/pixel/control/purity/service suite passes 41/41.

An independent production-shaped randomized sweep covered 23,000 samples across 1,000 folded routes with 2-8 bodies: zero exceptions or nonfinite outputs, with worst clearance ratio `0.9999999999796`. Feasibility-expansion continuity was probed at both on/off boundaries down to plus or minus `1e-11` alpha: scale approached 1 continuously, all-pair ratios stayed at least `0.99999999999995`, and neighbor motion shrank with the perturbation. Ordinary half-circles, endpoints, loops/nonterminal interpolation, both-terminal 4/6-body cases, rebase/stale fallback, cache purity, Ruff, and format checks remained green. No actionable finding remained.
