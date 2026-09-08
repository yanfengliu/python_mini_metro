# GM-02e hybrid observation and memory research plan

## Intent

Treat the remotely finalized ten-frame multiscale recurrent policy as the bounded pixel-only baseline, not the complete long-horizon solution. Define cheaper semantic-state and training-time privileged-information lanes now, then implement and compare them only after the post-balance game contract is stable in GM-12. This work unit changes research guidance and the durable roadmap; it does not change the current runtime, observation space, model default, reward, or manifest schema.

## Live constraints

- `PlayerPixelEnv` exposes one channel-first `uint8` `Box`; the promoted history wrapper makes ten frames a 607.5 KiB raw observation and measured the eight-worker training tree at roughly 4.04 GB peak summed working set. Those GB values are comparative RAM, not disk use.
- `README.md` and `ARCHITECTURE.md` define `PlayerPixelEnv` as the official player-equivalent learning boundary and `MiniMetroEnv` as privileged structured debugging/verification state. Even a tensor containing only visually represented facts bypasses perception and must remain a separately labeled assisted task unless the deployed actor still receives pixels only.
- `MiniMetroEnv.observe()` already exposes variable-length structured stations, paths, metros, passengers, and NumPy arrays, but it is not a fixed-shape Gymnasium `Dict` observation, contains session IDs/index maps, and omits several decision-relevant visible-state details. It is useful source material, not a drop-in training contract.
- The current model path assumes `MiniMetroCNN` plus `CnnLstmPolicy`. SB3-Contrib 2.9.0 supports recurrent `Dict` observations through `MultiInputLstmPolicy`, so a hybrid baseline can remain inside the authenticated RecurrentPPO stack.
- `VecTemporalHistory` deliberately accepts only a channel-first `uint8` `Box`. A hybrid environment therefore needs a separately versioned Dict-aware history wrapper that stacks only the pixel key and forwards the aligned latest semantic keys, including terminal/autoreset handling; the existing history fingerprint cannot be reused unchanged.
- Current entity limits are small enough for padded masked tensors, but later fleet, carriage, map, tunnel, and progression work changes the final schema. Implementing the durable hybrid schema before GM-11 would create avoidable migrations.

## Observation boundary

Define three explicitly different experimental tiers rather than silently giving the pixel agent privileged simulator state:

1. `player_pixel`: the existing player-visible RGB/action contract and its exact history descriptor.
2. `semantic_hybrid`: a short visual window plus exact fixed-shape semantic features limited to facts represented in the rendered game or deterministically accumulated from that policy's own prior observations, actions, and rewards. This is a perception-assist/privileged-representation task, not player-equivalent, even though it excludes hidden dynamics.
3. `structured_oracle`: broader simulator state from `MiniMetroEnv` or other internal fields, used only as a diagnostic ceiling, teacher, or training-time critic/auxiliary target. It is never a deployable player-equivalent policy observation.

The semantic snapshot may encode masked station, line, metro, passenger, and global/HUD entities: normalized positions and shapes; station queue composition and a declared visible warning category; ordered line membership and loop state; metro position, occupancy, line/color, and visible onboard destination shapes; deliveries, line credits, speed/pause state, visible control states, and an in-progress pointer gesture derived from the policy's own actions. Persistent derived features may summarize observed arrivals, deliveries, waits, and route edits with bounded age bins or exponentially weighted counts, but those summaries are a separate ablation from learned recurrent state.

The semantic tier must not expose RNG state, future stations or spawns, internal travel-plan objects, shortest-path solver output, hidden UUIDs, future rewards, exact passenger wait time, exact simulator time/decision count, spawn counters/intervals, metro segment/direction/speed/stop/boarding timers, or any state belonging to another vector slot or episode. Direction or velocity may be derived only from the policy's own prior visible positions. Every tensor needs an explicit mask, units/range, reset rule, and stable ordering independent of session IDs. Leakage tests must prove that changing hidden fields without changing declared visible semantics leaves the semantic tensor unchanged.

GM-12a must build an exhaustive inventory from the final renderer, controls, and action contract rather than freezing today's entity list. That inventory includes route-selection/edit handles; locomotive inventory/assignment and carriage capacity/composition; map, river/crossing, and tunnel state; calendar/progression and pause reasons; upgrade offers, modal choice state, and applied upgrades; plus every future player-visible global introduced by GM-05 through GM-10.

## Model ladder

Promote complexity only through matched delivery-total evidence:

1. Add a semantic structured-only recurrent baseline. This measures the strategic value ceiling of compact non-visual state without paying for pixels, but remains explicitly assisted.
2. Add the first direct semantic-hybrid candidate: a short dense visual window, per-entity shared MLP encoders with masks and simple pooling, global features, and the existing separate actor/critic 256-unit LSTMs under RecurrentPPO. Use a custom multi-input feature extractor and authenticated observation/task/history identities.
3. If semantic assistance helps, add a player-equivalent transfer candidate whose actor receives pixels only at inference while privileged state is restricted to training-time semantic auxiliary targets, a teacher, or an asymmetric critic. Its evaluation must run with the privileged channel absent and fail if the actor path can access it.
4. Compare a small relation-aware entity encoder implemented with existing PyTorch primitives only if simple pooling leaves a verified route/topology diagnostic gap. Attention here is over a few current entities, not an unbounded temporal image sequence.
5. Compare GRU or gated Transformer-XL temporal memory only if a dedicated held-out memory diagnostic demonstrates an LSTM ceiling. Do not select a vanilla Transformer or ViT merely because the horizon is long.
6. Keep DreamerV3 as a separate later research lane after the cheaper semantic, hybrid, and pixel-transfer recurrent baselines are measured.

Retain the separately planned conditional pointer head as a required task-specific action ablation; observation and action-head changes must first be measured independently before any combined candidate is interpreted.

The first hybrid experiment should ablate a much shorter visual window against the ten-frame pixel-only baseline. Current route topology belongs in the structured snapshot; raw historical frames should pay only for motion, cursor/gesture, and other genuinely visual short-term cues.

## Identity, lifecycle, and evaluation contract

- A semantic or hybrid observation is a new task, not merely a new policy. Preserve the exact current pixel protocol-v1 descriptor/fingerprint for genuine artifacts and give each semantic/hybrid tier a distinct protocol ID/version (or an equivalent legacy-aware parameterized protocol descriptor) that truthfully replaces the pixels-only boundary. Extend/version `TaskSpec` and its descriptor/fingerprint to embed the selected protocol identity plus observation mode, exact Dict keys, shapes, dtypes, bounds, feature semantics, masks, ordering, normalization, and action/reward/horizon contract. Add an independently reusable state-schema fingerprint only if the task fingerprint incorporates it.
- Add a manifest schema that stores the observation contract and a Dict-aware history descriptor stating that history applies to pixels while semantic state is latest-only. Structured-only observations need an explicit no-visual-history representation instead of satisfying the old mandatory positive RGB `frameStack` fields. Preserve genuine pixel manifest v1/v2 loading; pixel/semantic resume or evaluation mismatches must fail before model bytes open.
- Make the versioned manifest observation descriptor/fingerprint the single semantic authority. The manifest authenticates the exact artifact-index snapshot by path and digest; that index authenticates models/checkpoints and intentionally excludes the manifest itself. Durable experiment/evaluation transaction evidence must therefore authenticate the exact manifest bytes/locator/digest separately, while SB3 checkpoint space metadata remains a compatibility check rather than a competing semantic descriptor. Record `MultiInputLstmPolicy`, extractor identity, branch/fusion dimensions, and every semantic encoder/history source file in the appropriate manifest hyperparameters and content/training source-hash boundary. Resume/evaluate must reconstruct the exact saved contract and reject same-shape semantic drift.
- Keep independent recurrent and derived-memory state per vector slot. Reset both at termination and truncation; never leak state across games, seeds, evaluation episodes, or workers.
- Preserve the canonical reward: the undiscounted sum of delivery deltas equals total passengers delivered at game over. Structured features are observations, not reward shaping.
- Compare at least pixel-only ten-frame recurrent, semantic structured-only recurrent, direct semantic-hybrid recurrent, player-equivalent transferred pixel recurrent, the conditional-pointer-head ablation, and existing feed-forward controls with matched dynamics/action/reward/horizon, training seeds, held-out environment seeds, environment-step budgets, and wall-clock/resource curves. Their task fingerprints intentionally differ when observations differ; this is an observation ablation, not a same-task architecture comparison. Headline selection remains run-clustered total deliveries with censoring reported separately.
- Treat semantic and oracle lanes as separately labeled strategy/teacher baselines, not proof that the player-pixel problem is solved. Promote a semantic-hybrid policy only within its assisted task; promote a player-equivalent policy only when privileged inputs are absent from the deployed actor/evaluation path and it improves held-out deliveries or sample efficiency at acceptable resource cost.

## Roadmap integration

- GM-12a freezes the final post-balance dynamics/action/reward/evaluation benchmark, inventories every final player-visible renderer/control/action field, and drafts semantic/oracle/player-pixel observability plus conformance rules without assigning an immutable observation version yet.
- GM-12b implements and adversarially contract-tests candidate schemas plus semantic structured-only, direct hybrid, and player-equivalent transfer models; measures tensor/resource footprints; runs short feasibility/leakage/lifecycle smokes; and only then freezes the selected observation versions and per-configuration/seed experiment matrix.
- GM-12c through GM-12f retain the existing durable per-run training, held-out evaluation, clustered-statistics, and promotion sequence.

## Evidence behind the ordering

- [SB3-Contrib RecurrentPPO](https://sb3-contrib.readthedocs.io/en/master/modules/ppo_recurrent.html) supports `MultiInputLstmPolicy`, `Dict` observations, multiprocessing, and `MultiDiscrete` actions, making a hybrid recurrent baseline an incremental extension of the current stack.
- [Relational Deep Reinforcement Learning](https://arxiv.org/abs/1806.01830) shows that entity-centric relational reasoning can improve planning and generalization, supporting a later small entity-attention ablation rather than more full-resolution temporal pixels.
- [GTrXL](https://arxiv.org/abs/1910.06764) shows gated Transformer-XL can outperform LSTM on demanding memory tasks, but [Memory Gym](https://www.jmlr.org/papers/v26/24-0043.html) found GRU significantly ahead of Transformer-XL on all endless variants and required auxiliary reconstruction for Transformer-XL's finite-task advantage. Architecture choice is task-sensitive.
- [R2D2](https://openreview.net/pdf?id=r1lyTjAqYX) demonstrates the importance of recurrent-state and sequence-boundary handling with replay, but its distributed off-policy DQN system is not the smallest next step for this repository's current on-policy `MultiDiscrete` stack.
- [Asymmetric Actor Critic](https://arxiv.org/abs/1710.06542) and [Learning by Cheating](https://arxiv.org/abs/1912.12294) support using simulator state only during training while keeping the deployed actor visual; [UNREAL](https://arxiv.org/abs/1611.05397) supports auxiliary representation-learning signals. These motivate a player-equivalent transfer lane, not silently feeding privileged tensors to the pixel actor.

## Validation and review

1. Verify every live-code claim against `README.md`, `ARCHITECTURE.md`, `src/env.py`, `src/rl/player_env.py`, `src/rl/model.py`, `src/rl/policy.py`, `src/rl/temporal_history.py`, `src/rl/training.py`, protocol/manifests, and current docs.
2. Obtain adversarial plan review from Codex and Claude when available; record any platform/model limitation and compensate with independent in-process live-code review.
3. Update `docs/rl-model-selection.md`, the parent game-maturity `PLAN.md`, `STATE.md`, and `EVIDENCE.md` without changing runtime files.
4. Run Markdown/pre-commit and diff-integrity checks, then use the normal A/B remote transaction before GM-03a begins.
