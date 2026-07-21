NOT CLEAN — red tests should not start yet.

1. [P1] Executable-action planning must also govern the approach/stop predicate. The plan only applies it to duration seams, while `PassengerFlow.should_stop_at_next_station()` currently stops for any transfer candidate, even when both train and station are full and zero actions can execute (`src/passenger_flow.py:245-258`). Add an exact blocked-transfer test proving no deceleration/stop, while preserving queued-return stopping separately.

2. [P1] Mid-stop composition semantics are undefined. Active dwell uses precomputed `stop_time_remaining_ms` plus fractional `boarding_progress_ms` (`src/passenger_flow.py:325-350`), and stale capacity is only noticed after a later slot (`src/passenger_flow.py:398-420`). The plan permits attach/detach during movement and pause, so it must specify whether remaining service is recomputed, preserved, or rejected. Test attach/detach at 249/250/499/500 ms, including newly enabled boarding and removal down to current occupancy.

3. [P1] A fixed initial boarding-candidate list cannot yet guarantee equality with execution. Production mutates/recomputes candidates before scheduling and after each transfer (`src/passenger_flow.py:319-324,373-403`). Either freeze an executable service plan consumed by the real loop, model the dynamic transition inputs, or prove an invariant preventing post-transfer eligibility changes. Add a transfer/replan case where candidate eligibility changes and assert planned actions equal executed actions.

4. [P1] `VisualPath + MetroPose` is not a coherent route anchor across interpolation. Existing evidence already produces `position=(290,100)`, padding segment index `1`, and `progress=.45` (`test/test_gm05b_render_continuity.py:188-205`). Using segment/progress places the consist at the corner rather than behind the rendered locomotive. Route-replacement rebases can similarly change the segment index while retaining pose values. Define a coherent sampled arclength/anchor representation and test:

   - path→padding and padding→path transitions at all alphas;
   - loop wrap;
   - retained-edge/padding replacement rebases;
   - stale-topology fallback;
   - endpoint reversal, where interpolation currently uses current direction for every alpha (`src/rendering/interpolation.py:350-370`).

5. [P1] The terminal-extrapolation rule in `PLAN.md:44` is incorrect. Extrapolation is required whenever available arclength behind the head is insufficient, even when the total route is much longer than the consist. A newly assigned forward train at the start of a long route is the simplest counterexample. Test both terminals, both directions, multiple carriages, short loops requiring repeated wraps, and all-zero geometry with a defined finite fallback.

6. [P1] The promised control/station disjointness is not achievable with static second-row constants. Stations may spawn through y=972 (`src/utils.py:22-32`), existing fleet controls are centered at y=972, and input resolves stations first (`src/input_coordinator.py:381-390`). A read-only scan found an active collision at seed 117: station `(1030,965)`, fleet control `(1019,972)`, making the control unreachable. Define deterministic station-aware relocation, a versioned reserved UI band, or revise the acceptance claim. Test seeded and adversarial collisions for every slot and both pixel profiles.

7. [P2] Pin control topology. “Per assigned path slot” conflicts with disabled locked/unassigned controls. Specify whether every stable `PathButton` owns visible/hittable carriage controls or only assigned slots do; also prevent overlap with locked-line Buy/price text above the current fleet row. Quantized reachability tests must map center → action grid → canonical point and prove the exact intended control is hit.

8. [P2] Preserve `PrivilegedSnapshot.fleet_control_positions` exactly and add a separate carriage-control field; the existing field is a locomotive pair consumed by tests and the demonstrator (`src/rl/privileged_oracle.py:17-22,75-110`). The demonstrator must budget two extra DOWN/UP actions and assert a carriage was actually attached and availability decreased before only issuing NOOPs.

No files were edited.
