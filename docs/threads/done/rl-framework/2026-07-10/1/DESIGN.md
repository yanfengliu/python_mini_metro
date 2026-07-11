# Player-equivalent RL framework design

## Decision

Add an official Gymnasium environment over the same `GameSession`, `convert_pygame_event`, `Mediator`, and `GameRenderer` used by the player window. The policy receives only downsampled RGB pixels plus a rendered cursor and emits low-level mouse/keyboard events. Keep the existing structured `MiniMetroEnv` unchanged for recursive verification and debugging; it is not the learning observation.

## Versioned pixel/control protocol

- Canonical render: 1920x1080 software `pygame.Surface`; the default `fast` observation profile is channel-first `uint8` RGB at 192x108 (`Box(0, 255, (3, 108, 192))`), with an optional `fidelity` profile at 320x180. `render()` returns the conventional canonical HWC RGB frame.
- Action space: `MultiDiscrete([8, observation_width, observation_height])`. Kind 0 is no-op; 1 mouse motion; 2 left-button down; 3 left-button up; 4 Space key-up; 5/6/7 key-up for 1x/2x/4x speed. Integer endpoint mapping reaches every canonical edge exactly. Mouse down/up first moves the software pointer when needed; duplicate button transitions are no-ops. Keyboard/no-op actions ignore coordinates.
- A deterministic arrow cursor and pressed-state marker are composited into observations after gameplay rendering so the policy sees the player pointer/proprioceptive state without adding privileged game state.
- Each decision applies one event and advances an exact configurable count of fixed ticks; the default is six ticks (17/17/16 twice, 100 simulated milliseconds and 10 decisions/second). This exact-step path shares the clock cadence but cannot clamp/drop updates like wall-time catch-up. Headless rendering uses alpha 1 and therefore observes only completed simulation state.
- The environment publishes a JSON protocol descriptor and SHA-256 fingerprint covering schema version, spaces, coordinate mapping, cursor, and decision cadence. Training manifests record the fingerprint and evaluation refuses incompatible artifacts by default.

## Gymnasium contract

- `reset(seed=...) -> (observation, info)` creates a fresh mediator/session/renderer and prepares layout before the first observation.
- `step(action) -> (observation, reward, terminated, truncated, info)` validates the action, routes a real pygame event through `convert_pygame_event` and `GameSession.dispatch`, advances 100 ms, then renders.
- `terminated` is game over. `truncated` is a configurable decision horizon. Calling `step` after either requires `reset`.
- Default reward is delivered-passenger delta (`total_travels_handled`), so buying a useful line does not create a -90/-210/-350 learning penalty. A `display_score_delta` task remains available for the strict spendable-bank objective. Reward mode is named/versioned and evaluation reports both deliveries and displayed score.
- Live info contains protocol/task identifiers plus cursor and decision bookkeeping, but no hidden stations, routes, delivery totals, score deltas, seed, or simulation clock. Deliveries, displayed score, seed, and time are emitted only as terminal episode metrics after the final action. The privileged snapshot helper used by tests and the curriculum demonstrator is a separate, explicitly named module and is never attached to the training policy.

## Determinism and vectorization

Add a `SimulationContext` owned by each mediator with `random.Random` and NumPy `Generator` instances. Station placement, colors, spawning, destinations, and shuffling consume only that context; recursive checkpoints record it. Interleaved same-process environments therefore cannot perturb one another, while `SubprocVecEnv(start_method="spawn")` remains the scalable default for parallel training.

## Training stack

- Gymnasium is a core lightweight dependency so the pixel contract runs in normal CI; Stable-Baselines3 and TensorBoard are in `requirements-rl.txt` so normal game installs do not pull PyTorch.
- PPO uses `CnnPolicy`, four-frame channel-first stacking, shorter rollouts, and a repo-owned strided/adaptive-pooling CNN by default. CLI configuration covers seed, environments, timesteps, horizon, render profile, fixed ticks per decision, reward mode, device, checkpoint/evaluation intervals, output directory, and resume model.
- Every run writes a zero-step recovery checkpoint and a JSON manifest before learning, then refreshes recovery provenance after periodic checkpoints and final save. The manifest records protocol/reward versions, model and dependency versions, hyperparameters, callback/device settings, seeds, Git revision/dirty paths, exact environment/trainer fingerprints, parent run digests, and an authenticated artifact-index digest. The index binds selected model paths, sizes, and SHA-256 values; versioned index files keep the prior recovery pair valid across an interrupted refresh.
- Evaluation recreates the manifest-declared environment/frame stack, verifies protocol/task/content/trainer/runtime compatibility and exact model bytes, runs deterministic episodes, and emits reward, length, deliveries, and displayed-score JSON metrics for every episode. Content, trainer, and runtime overrides are separate explicit flags and add compatibility tags.

## Compatibility boundary

Future stations, routes, passengers, controls, and visual content automatically appear in pixels. Existing mouse semantics remain stable. Render profiles come from one registered protocol set so spawned workers and manifests can reconstruct them exactly. Adding a new player keyboard control, registered profile, or cursor representation requires an explicit protocol update; rendering/game-content changes update a separate environment-content fingerprint, while the Git revision and dirty-path inventory preserve full source provenance.

The canonical low-level task is deliberately difficult: random exploration must discover multi-decision pointer drags before deliveries occur. Ship a deterministic low-level demonstration/curriculum generator and a positive-delivery integration test so users can validate the task and seed future imitation/curriculum work. Smoke PPO proves the training pipeline, not that a competent policy emerges in a few updates.
