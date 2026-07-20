# Protocol and roadmap plan review

## Residual findings

[P1] PLAN:18-20 has mutually exclusive release contracts. L18 says station-up calls replace exactly once; L19 says fewer-than-two/invalid station-up cancels with no call, and says any up away has no game effect; L20 says plain assigned-button click still deletes. Add an explicit precedence matrix: no gesture + assigned up => historical delete; armed/zero stations + up on original button => plain-click delete; captured draft + resulting <2/invalid/off-station/button => cancel/no hook; resulting valid 2+ station-up => clear then exactly one hook. Explicitly decide down-on-A/up-on-B with zero stations (baseline deletes B) rather than leaving compatibility ambiguous.

[P1] PLAN:38 rebase is not yet safe. `previous.segment is current.segment` proves only both cached snapshots share one OLD transition; it does not prove that old transition is the NEW live segment. Concrete stopped case: old A-B-C arrives/stops at B with both snapshots on old B padding; replace A-B-D retains arrival AB but binds live metro to a different B padding. Position is unchanged and old snapshots share identity, yet blindly rebasing changes heading/transition. Require live semantic/geometric equivalence (path segment same exact station pair/endpoints modulo reversal; padding same retained triple/geometry) before direction-flip/rebase, else live-pose fallback. Add this changed-outgoing stopped-station regression.

[P2] PLAN:32 “successful commit increments [static cache] once” contradicts GM05a exact same-route no-op (`path_replacement.py:438-443`) returning True without topology/signature change. Say topology-changing commit increments once; exact no-op stays zero, and add a gesture no-op regression.

[P2] PLAN:45 covers fast+fidelity but pins only default/fast task hash. Pin fidelity TaskSpec too: `cd713a6891d8e74dab1aac2ded2edc88a727cb2b5b420948c65731d3a0eb3418f`, or explicitly assert its pre/post equality.

Checkpoint/schema, protocol/content separation, PlayerPixel timing/determinism, second raw probe, primary-pointer wording, and D-007 cursor are now coherent.

## Final reread

CLEAN on the fresh live iteration-3 PLAN/REVIEW. The explicit zero-station release-target delegation at PLAN:18 plus cross-target tests at :44 closes compatibility; topology-change/no-op cache semantics at :32 are exact; transition keys at :38 now carry sufficient path/padding context and :46 pins unsafe stopped-padding fallbacks; checkpoint/schema, both PlayerPixel profiles and exact fingerprints, content drift, GM05b/GM05c scope, and D-007 downstream-A reconciliation remain coherent. No remaining actionable plan finding.
