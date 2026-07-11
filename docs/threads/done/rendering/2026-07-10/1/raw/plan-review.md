# In-process rendering plan review

Three independent reviews grounded every claim in the live code. Required amendments were accepted: preserve the alternating logical segment state machine; prepare station/button/game-over hitboxes before input; snapshot mutable render state beyond recursive checkpoints; fully specify cadence, backlog, pause/restart, and pacing; add pure pose interpolation; prune effects in updates; bound cache ownership and specify z-order/invalidation; cover future geometry revision and zero-sized viewports; and extract a shared player session for the future pixel RL environment.

The deterministic test design uses real software surfaces and semantic masks/centroids rather than cross-platform font or whole-frame hashes. It covers symmetric even lanes, cache/segment identity, progress-preserving metro projection, repeated-pixel/render-state purity, corners/loops/reversals, and an exact before/after evidence scene.

Re-review corrected one overreach: zero-length padding keeps its current logical transition tick and is smoothed only in presentation. It also required lazy renderer-owned bundled fonts and a fresh-process displayless pixel test so state-only RL workers never initialize graphics resources.
