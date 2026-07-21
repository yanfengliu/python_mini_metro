# GM-05c rendering and cache plan review

Status: `NOT CLEAN` on the initial candidate.

## Findings

1. **P1 - Motion-triggered one-stroke handles steal or prevent valid full redraws.** Seed 0 button `(840,1030)` to target station `(1232,318)` passes `6.18 px` from an insertion handle; button to one insertion midpoint passes `5.17 px` from another. Desktop sampling and PlayerPixel destination jumps diverge. Separate selection and require a fresh handle down.
2. **P1 - Midpoint/outward handles are not universally visible or hittable.** Seed 4 puts midpoint `(1244,849)` inside station 2 at `(1247,848)`; seed 671 puts a plausible outward endpoint inside a path button; two-station-loop reverse edges coincide; a metro can hide a marker drawn below it. Deterministically relocate colliding handles with leader geometry against entities, controls, bounds, quantization, and other handles; handle two-station loops explicitly; draw actionable markers above stations/metros and below controls.
3. **P1 - Shortening preview does not show removal.** The complete old line remains below a candidate that is only its subset. Add a deterministic non-erasing strike/dashed removal primitive and prove it away from the cursor and at crossings in both profiles.
4. **P1 - Ambiguous handle hits can still trigger legacy release actions.** Record ambiguity as a consumed invalid edit.
5. **P2 - Shared geometry lacks an authoritative style source.** Define canonical input geometry or a supported style handoff and test nondefault injected style.
6. **P2 - Center-only PlayerPixel reachability is insufficient.** Round-trip each registered profile's chosen action coordinate and prove it stays in the handle envelope and outside precedence blockers.
7. **P2 - Handle cache behavior is underspecified.** Prefer an explicitly cache-free primitive renderer or give it a finite primitive-only key.

## Disposition

All findings are accepted in the revised live plan. Selection and operation now use separate gestures; one canonical config-driven builder collision-resolves primitive descriptors and registered-profile envelopes; two-station loops collapse canonically; ambiguous down is consumed; shortening gains explicit removal styling; handle markers render above entities; injected renderer style is non-authoritative for interactivity; and the handle renderer is cache-free. Fresh rereview is required.

## First revised reread

One P1 remained: button-to-empty selection was still sample-dependent because a dense desktop path could cross and capture a station while PlayerPixel jumped directly to the empty destination. Live seed 374 button `(840,1030)` to empty `(840,950)` passes within 23 px of station `(863,963)`; seed 11 has the same class. The accepted disposition makes final in-viewport empty release latch selection regardless of intermediate draft samples or invalidity, while off-viewport release remains cancellation. A second fresh reread is required.

One P2 test-contract defect also remained: `PlayerPixelEnv.render()` returns the canonical 1920-by-1080 surface regardless of profile, so it cannot prove fast/fidelity visibility. The accepted disposition requires cursor-masked marker/ring and shortening-overlay assertions in the actual downscaled CHW observation returned by `step_result[0]` for both profiles.

## Final reread

`CLEAN` - the final live plan is implementable against the current input, rendering, cache, and PlayerPixel contracts. The final-target empty-release rule and actual downscaled CHW observation requirements close the remaining actionable gaps.
