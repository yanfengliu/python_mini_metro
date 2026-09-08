# GM-05c input and state plan review

Status: `NOT CLEAN` on the initial candidate.

## Findings

1. **P1 - Held-motion handle activation steals valid GM-05b full redraws.** The event abstraction carries sampled positions only, so it cannot distinguish intentional handle entry from crossing one en route. A live seed-43 route demonstrates this: button `(840,1030)` to intended station `(1018,819)` passes within `2.64 px` of another edge midpoint `(977,863.5)` before reaching the station. Human intermediate motion selects insertion while PlayerPixel's single jump does not. Activate handles only when a fresh pointer-down begins on an independently visible handle or use another explicit phase. Keep outward endpoint centers because station-centered endpoints are incompatible with station-first creation/redraw.
2. **P1 - Two-station loops make both midpoint handles unselectable.** A loop creates A-to-B and B-to-A path edges with the same lane and midpoint. Exact-tie rejection suppresses both. Collapse the physical pair to one deterministic canonical insertion handle, distinctly offset them, or narrow acceptance.
3. **P1 - Finite short edges can expose visible but unreachable midpoint handles.** Seed 1 has midpoint `(569.5,820)` inside station 1's radius-30 circle at `(551,807)`; foreign stations/buttons can cause the same problem. Define collision-aware relocation/suppression or accessible offset geometry.
4. **P1 - Ambiguous-hit cancellation conflicts with the legacy release matrix.** Selecting no handle on a tie lets mouse-up delegate deletion/purchase/speed. Record a consumed invalid edit or remove the no-delete claim.
5. **P2 - Rebinding cancellation lacks captured evidence.** Capture/validate the originating mapping or narrow the promise.
6. **P2 - Malformed cancellation was broader than local validation.** Narrow it to malformed handle/source state and leave canonical path/metro/passenger malformation to GM-05a preflight.

## Disposition

All six findings are accepted in the revised live plan. Two-phase selection removes held-motion interception; canonical collision resolution and the two-station collapse make physical handles accessible; ambiguous down is consumed; button rebinding is explicitly irrelevant; and malformed-state claims now match the local versus GM-05a validation boundary. Fresh rereview is required.

## Revised reread lifecycle findings

1. **P1 - Off-viewport cancellation cannot work through the live desktop path.** `main.py` drops every mouse event whose window position maps outside the viewport, including mouse-up. Releasing in letterboxing therefore leaves pointer/redraw state active. The accepted disposition routes an outside-position mouse-up through conversion and adds a resized-window integration test proving cancellation with no selection or release-target action.
2. **P2 - Active-handle cleanup on game over was unspecified.** Passenger waiting can set game over during the tick after handle-down, and desktop input then stops dispatching gameplay events. The accepted disposition clears active redraw/handle, weak selection, pointer-down, and hover on the exact false-to-true transition in the existing Mediator/passenger-flow boundary, with a real tick-driven strong-reference regression.

A final fresh reread is required.

## Final reread

`CLEAN` - the final live plan resolves the input, state, desktop-adapter, and game-over lifecycle findings against the current code.
