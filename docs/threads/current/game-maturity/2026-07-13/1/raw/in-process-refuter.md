# Initial adversarial review

1. **High — The proposed independent observation fingerprint conflicts with the existing task identity.** The current protocol and task descriptors explicitly assert a pixels-only `Box` observation. A hybrid `Dict` cannot retain those fingerprints and merely add another fingerprint without making the manifest internally contradictory. GM-12 needs a versioned task/protocol descriptor that incorporates observation mode, plus genuine v1/v2 manifest normalization. Structured-only also cannot satisfy the current mandatory positive `frameStack`/RGB history fields.

2. **High — The “player-observable” boundary is not yet enforceable and currently permits privileged precision.** Exact normalized simulator coordinates, ordered topology, per-passenger entities, metro direction, and warning state can differ while fast-profile pixels remain identical because of raster quantization, overlapping routes, blink-off phases, and entities lacking visible persistent IDs. Either label this honestly as semantic state augmentation, or require render-grid quantization, aggregate queue/onboard counts rather than hidden entity identity, and a causal non-interference test: identical emitted pixel/action/reward traces must produce identical structured and derived tensors.

3. **High — Lifecycle support is materially larger than the plan states.** `MultiInputLstmPolicy` itself is feasible—the pinned 2.9.0 implementation supports `Dict` observations, `MultiDiscrete`, multiprocessing, and recurrent reset masks. But the repository’s `VecTemporalHistory` rejects anything except a three-channel `Box`, and training always constructs `PlayerPixelEnv` then applies that wrapper. GM-12 must explicitly add a Dict-aware visual-history/derived-memory wrapper with terminal-copy-before-autoreset semantics, reward/action update ordering, prehistory fill, and multi-slot termination/truncation tests—not merely say “reset both.”

4. **High — The final-state inventory is incomplete.** Because implementation waits until after GM-11, the contract must cover GM-05–GM-10 player-visible state: selected-route/edit handles, fleet inventory and assignments, carriage capacity/composition, map/river/crossing geometry and tunnel inventory, calendar/progression state, upgrade offers/modal state, upgrades, and pause reason. The current station/line/metro/passenger/HUD list omits these. GM-12a should require an exhaustive renderer/control/action inventory from the final game, not extrapolate from today’s `MiniMetroEnv.observe()`.

5. **Medium — Identity is assigned to the wrong persistence layers.** Artifact indexes currently authenticate file bytes; training fingerprints hash implementation source; checkpoints store model/space data but not semantic descriptors. Duplicating observation semantics into all three creates multiple authorities. Make the versioned manifest’s observation descriptor/fingerprint authoritative, have it authenticate indexed checkpoints/evaluation artifacts, and add every new snapshot/wrapper/extractor file to the correct content or training source-hash boundary. Otherwise a new `src/rl/*` hybrid module could be excluded by the current explicit `TRAINING_SOURCE_PATHS` and RL content exclusions.

6. **Medium — GM-12 freezes the contract before proving it executable.** The plan versions/freezes the schema in GM-12a, then implements and smokes it in GM-12b. Reverse that boundary: GM-12a freezes the post-balance benchmark and drafts observability/conformance rules; GM-12b implements and adversarially tests candidate schemas; only after feasibility/resource smokes should an immutable observation version and experiment matrix be frozen. Also retain the parent roadmap’s task-specific action-head lane explicitly; it disappears from the draft’s required comparison set.

# Second adversarial review

1. **High — Protocol identity remains ambiguous.** The plan versions `TaskSpec` and its task fingerprint, but the current task descriptor embeds a global protocol fingerprint whose descriptor explicitly promises `rgb_pixels` and a pixels-only policy boundary. A semantic-only or Dict-hybrid task cannot truthfully retain that meaning. Require either a versioned protocol descriptor per observation tier, or explicitly redefine the existing fingerprint as a base player-control/render protocol and store it as `baseProtocolFingerprint` beneath the new task identity. Genuine pixel manifests must retain their exact old bytes.

2. **Medium — The artifact-authentication direction is stated incorrectly.** The plan says artifact indexes authenticate exact manifest/model bytes, but `write_artifact_index()` deliberately excludes `training-manifest.json`. Today the manifest authenticates the index by digest, and the index authenticates models/checkpoints; the index does not authenticate the manifest. Reword the contract accordingly and specify how evaluation/transaction evidence authenticates the exact manifest bytes.

# Final adversarial review

CLEAN

# Final-diff review

**Medium — The persistent cursor is stale and contradicts the review artifacts.** `STATE.md` still says review is in progress, tells the next session to repeat the now-completed independent re-review, and retains `research-review`; meanwhile `REVIEW.md` records final clean convergence. Before committing, advance the cursor to “review complete / validation and staging next” and make staging/validation the first resume action.

# Final-diff re-review

CLEAN
