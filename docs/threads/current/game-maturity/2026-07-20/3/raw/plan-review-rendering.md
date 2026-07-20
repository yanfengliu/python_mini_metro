# Rendering and interpolation plan review

## Residual finding

One remaining MEDIUM contract mismatch, so not yet CLEAN: line 38 says kind + station identities where present + endpoint geometry excludes stopped outgoing-padding reroutes, but `PaddingSegment` has no station fields and at centered lane order its old/new endpoints are both the same station coordinate. With only the planned strong segment ref/boolean stopped snapshot, old A-B-C padding at B and new A-B-D padding at B are indistinguishable by those listed properties, so that rebase can still falsely pass. The red fallback tests would expose it, but the plan should make the implementable rule explicit: on topology mismatch, never rebase a stopped snapshot whose old/current segment is padding (live-pose fallback), or capture/compare an immutable padding semantic context key (adjacent station identities) in each snapshot. The unconditional stopped-padding fallback is simpler and loses no meaningful sub-tick motion while stopped. Everything else in the current plan/diff/review is CLEAN.

## Final reread

CLEAN. Fresh reread confirms the immutable normalized padding key is implementable from the containing path, reversal-invariant, distinguishes changed outgoing adjacency even when centered padding endpoints coincide, and fails closed on missing context. The linked stopped-reroute/terminus, normal-transition, reversal/turnaround, retention, preview parity/cache, PlayerPixel, and line-budget tests cover the remaining risk surface. No actionable plan or REVIEW findings remain.
