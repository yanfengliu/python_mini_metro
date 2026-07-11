[![Demo](https://i.imgur.com/xpUow2f.png)](https://youtu.be/W5fCgqlECeI)

# python_mini_metro

This repo uses `pygame-ce` to implement Mini Metro, a fun 2D strategic game where you try to optimize the max number of passengers your metro system can handle. Both human and program inputs are supported. One of the purposes of this implementation is to enable reinforcement learning agents to be trained on it.

# Installation

Activate the Python 3.13 environment and install the game dependencies:

```powershell
conda activate py313
python -m pip install -r requirements-locked.txt
```

Gymnasium and the player-equivalent pixel environment are part of the normal install. Training a model also needs PyTorch, Stable-Baselines3, SB3-Contrib, and TensorBoard:

```powershell
python -m pip install -r requirements-rl-locked.txt
```

Both lockfiles are universal Python 3.13 resolutions with hashes and platform markers; pip selects the matching Linux or Windows wheels while preserving the same reviewed dependency graph.

The recursive playtest also requires Node.js 20 or newer and a built `civ-engine` sibling at `../civ-engine`. The checked-in package lock expects civ-engine 2.2.0 through that relative link; CI pins the sibling to commit `e0cb614a516c449159a4562c2ac45bd40bffd3df` and verifies the imported engine version before testing.

```powershell
cd ../civ-engine
npm ci
npm run build
cd ../python_mini_metro
npm ci
python -m pip install -r requirements-locked.txt
```

Set `PYTHON` to a specific interpreter path when `python` is not the intended executable. Recursive runs set `PYTHONHASHSEED` to `0` by default unless it is already defined.

# How to run

## To play manually

* If you are running for the first time, install the requirements using `python -m pip install -r requirements-locked.txt`
* Activate the virtual environment by running `conda activate py313`
* Run `python src/main.py`
* The window uses a fixed 60 Hz simulation cadence with interpolated metro motion; resizing preserves the 1920x1080 player view without changing game timing.
* Hold down the mouse left button on a station and drag onto other stations to create a path for the metro.
* Press SPACE to pause / unpause the game.
* Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
* View the score on the top left corner of the screen.
* The number of grey circles on bottom of the screen is the number of available metro lines left.
* Click on the colored circle at the bottom to cancel an established line.
* Click on the empty circles at the bottom to buy new lines with scores.

## To play programmatically

Expose the source directory when importing the environments directly from a repository checkout:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
```

Then use the Gym-like environment in `src/env.py`:

```python
from env import MiniMetroEnv

env = MiniMetroEnv(dt_ms=16)
obs = env.reset(seed=42)
obs, reward, done, info = env.step(
    {"type": "create_path", "stations": [0, 1, 2], "loop": False}
)
obs, reward, done, info = env.step({"type": "remove_path", "path_index": 0})
```

### API
- `MiniMetroEnv(dt_ms: int | None = None)`
  - `dt_ms` is the default simulated milliseconds advanced after each `step(...)`.
  - If `dt_ms=None`, time only advances when you pass `dt_ms` to `step(...)`.
- `reset(seed: int | None = None) -> observation`
  - Resets the game and returns the initial observation.
  - If `seed` is provided, independent session-owned Python and NumPy random streams make gameplay mechanics, array views, and rendered pixels deterministic without changing host-global RNG state. Opaque entity ID strings remain unique per runtime session and should not be compared across resets.
- `step(action: dict | None = None, dt_ms: int | None = None) -> (observation, reward, done, info)`
  - Applies one action, optionally advances time, then returns:
    - `observation`: latest state
    - `reward` (`int`): score delta since previous step
    - `done` (`bool`): `True` when game is over
    - `info` (`dict`): currently contains `{"action_ok": bool}`
  - Once `done` is `True`, later `step(...)` calls are stable no-ops: actions are rejected, time does not advance, and `info["action_ok"]` is `False` until `reset(...)`.

### Valid `action` inputs
- `None`
  - Treated as `{"type": "noop"}`.
- `{"type": "noop"}`
  - No direct game command; only time progression happens (if `dt_ms` resolves to an integer).
- `{"type": "create_path", "stations": [i0, i1, ...], "loop": bool}`
  - Required:
    - `stations`: list of station indices (`int`) with length `>= 2`
    - all indices must satisfy `0 <= idx < len(observation["structured"]["stations"])`
  - Optional:
    - `loop` (default `False`): when `True`, creates a loop that ends at the first station.
  - Fails (`action_ok=False`) if inputs are invalid or if no unlocked line is available.
- `{"type": "remove_path", "path_index": k}`
  - Removes an existing path by index.
  - Valid only when `0 <= k < len(observation["structured"]["paths"])`.
- `{"type": "remove_path", "path_id": "..."}`
  - Removes an existing path by path id string from `observation["structured"]["paths"][*]["id"]`.
- `{"type": "buy_line"}`
  - Buys the next locked line if affordable.
  - Price follows configured incremental unlock costs (derived from `path_unlock_milestones`).
- `{"type": "buy_line", "path_index": k}`
  - Attempts to buy a specific locked line button index.
  - Must be the next purchasable locked index (sequential purchase rule); otherwise fails.
  - `path_index` must be an integer in `[0, num_paths - 1]`.
- `{"type": "pause"}`
  - Pauses simulation updates.
- `{"type": "resume"}`
  - Resumes simulation updates.

Any unknown `type`, or malformed action payload, returns `info["action_ok"] == False` without mutating game state.

### `step(..., dt_ms=...)` behavior
- `dt_ms` argument to `step(...)` overrides constructor `dt_ms` for that call.
- If effective `dt_ms` is an integer, simulation advances by that many milliseconds.
- If effective `dt_ms` is `None`, action is applied but time is not advanced.
- If the action is rejected, no simulation time advances for that step.
- If the environment is already game-over, no simulation time advances regardless of `dt_ms`.

### Observation shape
`observation` is:
- `observation["structured"]`: Python dict/list representation
  - includes `stations`, `paths`, `metros`, `passengers`, `score`, `time_ms`, `steps`, `is_paused`, `is_game_over`, and ID-to-index maps in `index`.
- `observation["arrays"]`: NumPy-friendly arrays/lists
  - includes station positions/types/counts, path station-index sequences, metro positions/path indices, passenger destination types and locations.

# Player-equivalent reinforcement learning

`PlayerPixelEnv` is the official learning boundary. A policy receives only the same rendered game pixels a player can see, including a deterministic software cursor, and acts through low-level mouse motion/button and keyboard events routed through the normal player event path. The older `MiniMetroEnv` remains available for structured debugging and recursive verification; its privileged state is not the learning observation.

```python
import numpy as np

from rl.player_env import PlayerPixelEnv
from rl.protocol import ActionKind

env = PlayerPixelEnv(max_episode_steps=36_000)
observation, info = env.reset(seed=42)
action = np.asarray([ActionKind.DOWN, 50, 40], dtype=np.int64)
observation, reward, terminated, truncated, info = env.step(action)
env.close()
```

The default observation is channel-first `uint8` RGB with shape `(3, 108, 192)`; the registered `fidelity` profile is `(3, 180, 320)`. The action is `MultiDiscrete([8, width, height])`: `0` no-op, `1` mouse motion, `2` left-button down, `3` left-button up, `4` Space, and `5`/`6`/`7` for the `1`/`2`/`3` speed keys. Pointer coordinates are integer observation-grid locations mapped exactly onto the canonical 1920x1080 player view. Each default decision advances exactly six fixed ticks (100 simulated milliseconds). The default reward is newly delivered passengers; `display_score_delta` is available when line-purchase penalties are intentionally part of the objective.

Live `info` dictionaries contain protocol and pointer bookkeeping, not hidden stations, routes, deliveries, or simulation state. Game-level deliveries and displayed score appear only in terminal episode metrics, after the last action. The deterministic helper in `rl.privileged_oracle` is deliberately separate and is used only by tests and the scripted curriculum demonstrator.

Fresh training defaults to SB3-Contrib `recurrent_ppo` with eight spawned environments, an eight-frame stack, and recurrent minibatches of 64. At the default 10 Hz decision rate, eight RGB frames become 24 input channels and provide a nominal 0.8 seconds of local history (0.7 seconds between the oldest and newest samples). `MiniMetroCNN` extracts 256 visual features, then separate one-layer, 256-unit actor and critic LSTMs carry episode memory across decisions. Feed-forward PPO retains its prior batch size of 256; recurrent batch 64 materially reduced peak process-tree memory in the local one-rollout profile documented in the model-selection note.

The recurrent hidden state persists within one game and resets at the next game's episode boundary; a new training or evaluation process also starts with blank hidden state. Learned network weights are different: authenticated checkpoints persist them across process restarts and resumed training.

The default delivery-delta rewards sum exactly to the episode's terminal total deliveries. Fresh recurrent runs therefore use `gamma=1.0` and `gae_lambda=0.99`, and evaluation reports `meanDeliveries` as the primary metric for the objective of maximizing passengers delivered before the game ends. Evaluation also reports game-over and horizon-truncation counts/rates, marks the primary metric as censored whenever any episode hits the external horizon, and reports `meanDeliveriesAmongGameOverEpisodes` separately. A horizon-truncated delivery count is a right-censored lower bound, not a final game-over score.

Train the default recurrent policy and evaluate the resulting strict manifest with:

```powershell
python scripts/train_rl.py --total-timesteps 1000000 --n-envs 8 --device auto
python scripts/evaluate_rl.py output/rl/recurrent_ppo-RUN-ID/final_model.zip --episodes 10
```

Standalone evaluation uses the run manifest's recorded evaluation seed by default; pass `--seed` only when you intentionally want a different deterministic episode suite.

Use feed-forward PPO and an explicit frame stack as controlled ablations:

```powershell
python scripts/train_rl.py --algorithm ppo --frame-stack 4 --total-timesteps 1000000 --n-envs 8 --run-dir output/rl/ppo-four-frame
```

For a quick pipeline smoke test, use a new empty run directory:

```powershell
python scripts/train_rl.py --total-timesteps 128 --n-envs 1 --max-episode-steps 4 --run-dir output/rl/smoke
python scripts/evaluate_rl.py output/rl/smoke/final_model.zip --episodes 1
```

Resume from any authenticated periodic or final checkpoint into a new run directory; the saved manifest supplies the algorithm and frame stack when those flags are omitted, and explicit mismatches are rejected. Repeat any non-default task flags so they match the parent manifest:

```powershell
python scripts/train_rl.py --resume output/rl/recurrent_ppo-RUN-ID/checkpoints/mini_metro_recurrent_ppo_100000_steps.zip --run-dir output/rl/resumed --total-timesteps 500000
```

Every run immediately writes a recovery checkpoint and `training-manifest.json`, writes each new periodic checkpoint before refreshing the manifest and authenticated index, then saves and authenticates the final model. The manifest authenticates a versioned artifact index, and the evaluator hashes and parses one exact index snapshot before loading the exact model bytes it authenticated; a swapped or partially written model is never reopened by path for SB3. It also records the exact pixel/control protocol, task horizon and reward, frame stack, hyperparameters, callback intervals, requested/resolved device, seeds, gameplay dependency versions, Git state, an environment-content fingerprint, and a separate trainer-source fingerprint that includes both lockfiles. Resumed runs retain parent manifest/model digests and use the newly requested seed consistently in the model and environments.

Resume and evaluation fail closed on protocol, task, content, trainer-source, runtime, or artifact drift. `--allow-content-drift`, `--allow-training-drift`, and `--allow-runtime-drift` are explicit, tagged compatibility overrides; use the content override when intentionally testing an old model against new stations, mechanics, or graphics, and use the other overrides only when the reported implementation/runtime difference is understood. Legacy feed-forward PPO artifacts created before the recurrent dependency and training-source contract may require `--allow-training-drift` and/or `--allow-runtime-drift` after the reported differences have been reviewed.

The recurrent default is a research-backed production baseline, not a claim that a short smoke run learns competent play. Low-level line construction is a sparse multi-action problem, so `rl.demonstrator.run_delivery_demonstration` provides a deterministic curriculum trajectory that creates a route through player actions and reaches a real delivery for the reference seed. See [RL model selection for the player-pixel task](docs/rl-model-selection.md) for the CNN, recurrent PPO, Transformer, visual-transformer, and Dreamer comparison plus the experiment and reporting protocol.

# Recursive self-improvement loop

The deterministic fixture at `scripts/fixtures/recursive-playtest.json` uses seed `42` to create a line, advance time, exercise pause/resume, remove the line, and verify rejected actions. The harness drives `MiniMetroEnv` directly; it does not use the pygame GUI clock or an LLM.

Run the Node contract tests and one proposal-only recursive pass with:

```powershell
npm test
npm run playtest:recursive
```

Use another strict scenario or keep artifacts under a different subdirectory of `output/` with:

```powershell
npm run playtest:recursive -- --scenario path/to/scenario.json
npm run playtest:recursive -- --output-root output/my-recursive-runs
```

Normal recursive runs fail closed when relevant runtime source under `src/`, `scripts/`, `package*.json`, or `requirements*.txt` is dirty. They also require the resolved `civ-engine` package to match the pinned version, Git commit, and full runtime-tree digest, so a modified ignored `dist/` build cannot masquerade as the pinned engine. Commit or restore those files first. Deliberate canary and development runs may opt in explicitly; the resulting source inventories, dirty or mismatched status, and local patch are retained with the evidence:

```powershell
npm run playtest:recursive -- --allow-dirty
```

Re-verify an existing run in a fresh Python process with:

```powershell
npm run playtest:verify -- output/recursive/<run-id>
```

Each public verification attempt is append-only under the run's `verification-attempts/` directory. There is no separate public `playtest:pass` script: `npm run playtest:recursive` executes the pass, while `scripts/recursive-pass.mjs` provides its candidate selection, complete-manifest validation, and transactional ledger persistence.

Every default pass creates `output/recursive/<run-id>/` with `source-state.json`, an optional dirty `source-diff.patch`, recorded `inputs.json`, one-row-per-operation `transcript.jsonl`, `findings.authored.json`, `run-result.json`, drive logs, fresh-process replay evidence under `redrive/`, `verification.json`, verified and verification findings, and complete run/pass manifests. Source state carries deterministic SHA-256 inventories for this repository and the resolved linked engine plus relevant Git status, and both manifests embed its validated portable summary. New rows carry the `source-state-v2` tag while earlier immutable `source-state-v1` rows remain readable. The driver recaptures both sources immediately before finalization; drift produces `source-state.final.json`, an optional final local diff, and a failed pass rather than verified stale evidence. The append-only run and pass ledgers are `output/recursive/ledger.jsonl` and `output/recursive/passes.jsonl`; pending write-ahead intents under `output/recursive/ledger-intents/` repair interrupted manifest/ledger persistence and are removed only after both manifest files and rows are durably confirmed. Everything under `output/` is generated evidence and remains uncommitted.

Authored findings are always `unverified`. The verifier re-drives the exact recorded operations in a fresh process and requires exact replayable input metadata, transcript results, full canonical checkpoint vectors, and finding semantics to match. Only replay-side findings that pass those checks become `verified` with `verificationMethod: "replay"` and an addressed bundle evidence reference to the original run. Any mismatch is an unverified nondeterminism finding and fails the run.

Pass outcomes are `no-fix-candidate`, `proposal-only`, or `run-failed`. `proposal-only` reports the highest-severity verified fix-classified finding; this repository adds no automatic apply or fix arm, so the driving agent must implement the fix through the normal TDD and review workflow, rerun the pass, prove the finding's stable bug class absent, and preserve a regression test. A failed drive, replay, or validation exits nonzero and records `run-failed` manifests and ledger rows.

# Testing

```powershell
python -m unittest -v
npm test
```

The pygame renderer is also the canonical headless pixel source: it works with software `pygame.Surface` objects without opening a display, emits repeatable pixels for identical state, and does not mutate simulation state. This boundary is intended for player-equivalent reinforcement-learning observations as well as the interactive window.
