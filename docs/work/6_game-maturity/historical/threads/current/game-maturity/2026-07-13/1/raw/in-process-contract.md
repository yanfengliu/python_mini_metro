# Initial live-contract review

Live-code conclusion: the repo can support a small semantic hybrid lane, but it must be treated as a new observation task. `README.md` explicitly classifies `MiniMetroEnv` state as privileged and `PlayerPixelEnv` as the official player-equivalent boundary. Even exact tensors for visually represented facts bypass perception, so they cannot silently inherit the current pixel fingerprints.

Current reusable implementation sources:

- Directly reusable/derivable from `MiniMetroEnv.observe()`:
  - station positions and shape types;
  - waiting passenger destination types and station locations;
  - line station sequences, loop flags, and colors;
  - metro positions, line assignment, and onboard passenger destination types;
  - deliveries, line credits, pause, and game-over state.
- Reusable from `PlayerPixelEnv`/`Mediator`, but missing from `MiniMetroEnv.observe()`:
  - rendered cursor and pressed state;
  - active speed/pause control;
  - path-button locked/empty/assigned state;
  - passenger warning-blink category;
  - fixed maximums: 20 stations, 4 lines, 4 metros, 7 destination shapes.
- Existing ragged arrays need a new padded/masked encoder; they cannot directly define a Gym fixed-shape space.

Player-semantic features appropriate for a research observation:

- station centers/shapes;
- visible waiting destination icons and whether they are in the visually signaled blinking class;
- visible line edges, color, and loop closure;
- visible metro position, line, and onboard destination icons;
- HUD deliveries/credits;
- visible controls, game-over overlay, cursor, and pointer-down marker.

Do not expose:

- UUIDs or ID/index dictionaries;
- exact `time_ms`, `steps`, decision count, seed, RNG state, spawn counters, or sampled spawn intervals;
- exact passenger `wait_ms`—only the blink category;
- `travel_plans`, BFS paths, next path/station;
- hidden station pool/future unlock contents;
- metro segment index, exact speed/direction, stop timer, boarding progress;
- reward baselines or terminal metrics before termination.

Smallest concrete fixed-shape contract:

```text
spaces.Dict({
    "pixels": Box(uint8, (3, H, W)),       # history wrapper outputs (30, H, W)
    "state":  Box(float32, (2178,), -1, 1)
})
```

Exact `state` layout:

```text
0:480       20 station records x 24
             present 1 + normalized xy 2 + shape one-hot 7
             + waiting destination counts 7 / 12
             + blinking destination counts 7 / 12

480:2080    4 x 20 x 20 per-line symmetric adjacency, flattened

2080:2100   4 line records x 5
             present 1 + loop 1 + normalized RGB 3

2100:2156   4 metro records x 14
             present 1 + normalized xy 2 + line one-hot 4
             + onboard destination counts 7 / 6

2156:2178   globals/controls 22
             squashed deliveries 1 + squashed credits 1
             + active pause/1x/2x/4x one-hot 4
             + game-over 1 + cursor xy 2 + pointer-down 1
             + 4 path-button states x locked/empty/assigned one-hot 3
```

Use a bounded monotone transform such as `log1p(x) / (1 + log1p(x))` for unbounded deliveries/credits. Station slots should remain stable by unlock order; line slots should follow current path-button assignment. The adjacency representation avoids imposing an unsupported maximum route-sequence length.

This vector is 8.51 KiB as `float32`; 8 environments × 128 rollout steps add about 8.51 MiB, tiny beside the current 607.5 MiB raw ten-frame pixel payload.

Smallest model baseline:

- `MultiInputLstmPolicy` is available in the installed SB3-Contrib 2.9.0.
- Pixel branch: existing `MiniMetroCNN`, 30-channel ten-frame multiscale input → 256 features.
- State branch: `Linear(2178, 128) + ReLU`.
- Fusion: concatenate 256 + 128, then `Linear(384, 256) + ReLU`.
- Keep current RecurrentPPO settings and separate 256-unit actor/critic LSTMs.
- Stack/history-sample only `pixels`; pass the latest aligned `state` once per decision.
- Add a structured-only recurrent ablation using the same state encoder to measure the symbolic planning ceiling.
- Use an MLP over the fixed adjacency first; GNN/Transformer attention is a later ablation, not the reference implementation.

Contract changes required:

- Current protocol hardcodes `rgb_pixels`, Box observation, and `pixels_only_info_contains_no_live_game_state`; hybrid must use a distinct protocol family/version.
- Current task fingerprint hardcodes a Box shape; it must describe the exact Dict keys, shapes, dtypes, bounds, normalization, slot ordering, and state schema.
- Current history fingerprint says sample-major RGB channels. A Dict-aware history needs a new descriptor/version specifying “history applies to pixels; structured state is latest-only.” Do not reuse the current history fingerprint unchanged.
- Manifest v2 has strict exact keys and cannot reconstruct observation mode. Add a v3 observation contract/schema field; hyperparameters alone are insufficient.
- Record `MultiInputLstmPolicy`, hybrid extractor, state schema/dimension, branch sizes, and fusion size in authenticated hyperparameters.
- Preserve v1/v2 pixel artifact loading; mismatched pixel/hybrid resume and evaluation must fail before model bytes open.
- Add any semantic encoder/environment file to the content-fingerprint whitelist; add extractor/Dict-history/training files to `TRAINING_SOURCE_PATHS`.
- Evaluation comparisons may match dynamics, action, reward, horizon, and seeds, but task fingerprints must intentionally differ. This is an observation ablation, not a same-task architecture comparison.

Primary risks/tests:

- Pixel and state values must describe the same post-transition instant, including terminal observations and VecEnv autoreset.
- Extend temporal history fail-closed for Dict terminal observations, reset clearing, and latest-state handling.
- Golden-test all masks, padding, normalization, and fingerprints.
- Add leakage tests showing changes to time, spawn cadence, travel plans, hidden station pool, and metro timers do not change `state` when visible semantics do not.
- The blink-category tensor is semantically visible over a short sequence but not necessarily in one instantaneous blink-off frame; document that this is a perception-assist lane. A strict instantaneous alternative would omit those 140 values, producing a 2,038-value state vector.
- Do not call `MiniMetroEnv` as a second environment; factor pure encoding from the same live mediator so pixels and structured state cannot diverge.

# First re-review

- [P1] `PLAN.md` versions `TaskSpec` but does not explicitly version/preserve the protocol identity. The live `protocol_descriptor()` is globally pixel-only and `protocol_fingerprint()` is hard-required during manifest reconstruction. GM-12 must preserve the exact pixel protocol-v1 fingerprint while assigning semantic/hybrid observations a distinct protocol ID/version or equivalent legacy-aware parameterized descriptor; otherwise extending the global protocol would invalidate genuine pixel v1/v2 artifacts despite the stated compatibility requirement.

# Final re-review

CLEAN

# Final-diff review

**High — `docs/rl-model-selection.md` overstates the current `player_pixel` actor inputs.** `PlayerPixelEnv` exposes pixels only; evaluation passes observations, recurrent state, and episode-start masks to `model.predict()`, not prior actions or rewards. Describing action/reward history as already received silently changes the official task boundary. State that the deployed actor receives rendered pixels plus recurrent state, and reserve action/reward histories for a separately declared future feature or ablation.

# Final-diff re-review

CLEAN
