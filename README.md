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

The recursive playtest also requires Node.js 20.6 or newer and the isolated civ-engine checkout described by `scripts/civ-engine-pin.json`. The checkout is retained at the ignored repo-local `/.civ-engine-pin/` path; neither setup nor recursive execution reads or mutates a sibling `../civ-engine` checkout. The engine build uses its own development lock, while the root exposes only an exact validated link and never installs that nested build-only graph into root `node_modules`. The package lock, Git commit, package version, physical resolution path, and complete runtime-tree digest are verified against the descriptor before recursive execution.

```powershell
npm run setup:civ-engine
node scripts/civ-engine-setup.mjs --verify-only
python -m pip install -r requirements-locked.txt
```

`npm run setup:civ-engine` is the only supported setup path. After its trusted top-level npm/Node bootstrap passes the startup assertion, it validates the checked-in descriptor, exact root package, descriptor-pinned canonical parsed-lock digest, and exact `.npmrc` contract; serializes setup with a repository-local lock; uses an owned transaction and restricted child-process environment; authenticates every physical non-generated checkout file to its exact detached-`HEAD` blob identity modulo LF/CRLF normalization allowed only by the independently authenticated repository-wide `* text=auto` policy before any install or build; atomically claims a missing final pin directory, records that directory's physical identity in the owned transaction, and recursively publishes directories, exclusive file copies, and contained links through no-replace filesystem primitives; reauthenticates the complete detached checkout at the final path before root linking; materializes or rebuilds only the exact ignored pin; installs the pin development graph through the validated Node-distribution npm CLI; builds through the exact pin-local TypeScript CLI under `process.execPath`; exclusively creates a missing root `node_modules/civ-engine` symlink/junction without invoking root npm; and finishes with strict provenance verification. Publication never renames or deletes at the final pin path: a destination or child-entry race fails without replacing or removing the winner, and any failure after the directory claim retains the matching source transaction and partial pin for inspection while releasing only the owned setup lock. The explicit `--verify-only` command is read-only and fails if setup is active or any required identity is unavailable.

Setup fails closed instead of replacing an existing suspicious checkout or following untrusted links. It refuses a linked pin, any non-generated checkout file without exact `HEAD` blob identity outside the authenticated `* text=auto` LF/CRLF normalization, suspicious Git identity or metadata, generated-tree links that resolve outside the audited tree, a pre-existing setup lock, an ownership-changed artifact from the active setup, any root lock semantics outside the descriptor-pinned digest, and resolution through any nested, external, or otherwise unexpected dependency slot. After the checkout's complete source identity is authenticated, setup may rebuild missing or mismatched ignored dependencies and `dist/` output and may create only an absent exact root dependency link below a validated physical `node_modules` container. It refuses a stale link, a physical slot, or any other root `node_modules` entry instead of replacing or removing it. Strict verification never repairs: it rejects unavailable, unsafe, or shadowed state and every disallowed version, commit, status, physical-path, runtime-entry, or runtime-digest mismatch. Inspect and resolve suspicious state; do not delete or replace `/.civ-engine-pin/` merely to make the check pass.

An interrupted setup can intentionally leave `/.civ-engine-setup.lock`, one or more `/.civ-engine-setup-<suffix>/` transactions, and a partially published `/.civ-engine-pin/`; an interrupted guarded public Node command can leave the lock but never a setup transaction or partial publication. First prove that no setup or guarded command is still running and attribute each exact repository-root entry to the interrupted command. The lock must be a physical regular file containing one JSON `token` record, and each transaction must be a physical directory with a physical `.setup-owner` file containing its own JSON `token` record; every transaction descendant must also be a physical regular file or directory. After the final directory is claimed, the transaction normally contains a physical `.setup-promotion-claim` file whose JSON names `.civ-engine-pin`, records its physical `dev`/`ino` identity, and repeats the transaction token; a crash between the exclusive directory creation and that record can instead leave an unrecorded partial pin. A partial pin is not covered by the routine cleanup commands below: preserve it with its transaction for inspection, and do not remove it unless the physical claim record, current destination identity, token, physical descendants, and exact transaction ownership have been independently matched. A link, junction, reparse point, absent or changed claim record, identity mismatch, non-physical descendant, or unrecognized entry is not safe to remove. List the exact names and inspect each exact record, then remove only the individually reviewed routine lock/transaction literal paths:

```powershell
Get-Item -LiteralPath .\.civ-engine-setup.lock -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath . -Force -Directory | Where-Object Name -Like '.civ-engine-setup-*'
Get-Content -LiteralPath .\.civ-engine-setup.lock
Get-Content -LiteralPath .\.civ-engine-setup-<exact-suffix>\.setup-owner
Get-Content -LiteralPath .\.civ-engine-setup-<exact-suffix>\.setup-promotion-claim
Remove-Item -LiteralPath .\.civ-engine-setup.lock
Remove-Item -LiteralPath .\.civ-engine-setup-<exact-suffix> -Recurse
```

Never pass a wildcard to a deletion command or run broad repository cleanup for recovery, and never remove an artifact that cannot be attributed and physically inspected. A `/.civ-engine-pin/` without a matching transaction-side physical claim record is not safely attributable as a crash-publication artifact and must not be removed by this recovery procedure. Rerun `npm run setup:civ-engine` after the exact owned leftovers are gone.

Set `PYTHON` to a specific interpreter path when `python` is not the intended executable. Recursive runs set `PYTHONHASHSEED` to `0` by default unless it is already defined.

# How to run

## To play manually

* If you are running for the first time, install the requirements using `python -m pip install -r requirements-locked.txt`
* Activate the virtual environment by running `conda activate py313`
* Run `python src/main.py`
* The game opens on a title screen: click New Game (or press ENTER) to start, click Continue to resume the autosaved game (shown only when a save exists), or click Exit to quit. Programmatic runs with a frame limit (`PYTHON_MINI_METRO_MAX_FRAMES` or `run_game(max_frames=...)`) start directly in gameplay; an explicit `run_game(start_state=...)` overrides both.
* The window uses a fixed 60 Hz simulation cadence with interpolated metro motion; resizing preserves the 1920x1080 player view without changing game timing.
* Hold down the mouse left button on a station and drag onto other stations to create a line. New lines start unserved.
* Press SPACE to pause / unpause the game.
* Press ESC while playing to open the pause menu (any in-progress drag is cancelled first): Resume (click or ESC) returns to play, Restart starts a fresh game, and Exit to Title returns to the title screen. The menu freezes the game independently of SPACE, so gameplay input, including the SPACE toggle, cannot dismiss it, and resuming keeps a SPACE pause in place until you unpause.
* Opening the pause menu autosaves your game to `saves/autosave.json`; Exit to Title rewrites the same save before leaving, and closing the window mid-run keeps it, so Continue on the title screen resumes exactly where you left off. Reaching game over deletes the autosave, so a finished run cannot be Continued.
* Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
* The top-left HUD shows lifetime passengers delivered, currently spendable line credits, unassigned locomotives, and unassigned carriages as separate values.
* Each filled grey circle at the bottom is an unused unlocked metro line slot.
* Hold an assigned colored circle, drag through the replacement station order, and release on the final station to redraw that line; the selected circle is outlined and an invalid repeated-station draft turns red.
* Hold an assigned colored circle and release over empty in-view space to select that line's edit handles. On a fresh drag, a filled endpoint handle extends to a new station or shortens by one station when released on its adjacent interior station; a hollow edge handle inserts a new station. Loops expose insertion handles, including the closing edge, but no endpoint handles.
* Click and release a colored circle without leaving it to remove that established line.
* Empty rings are locked line slots; hover to see their price and click the next one to buy it with line credits when affordable.
* A fresh game has four total locomotives and two fungible carriages. Every stable line slot has four resource controls: locomotive plus/minus followed by carriage plus/minus. Locked or unbound controls remain visible but disabled.
* An empty locomotive already stopped at a real station returns immediately. An empty moving locomotive marked for return remains assigned, boards no passengers, stops at its next real station, and only then returns to the available inventory. Use this return-then-assign sequence to move capacity between lines.
* Carriage plus attaches a new six-seat body to the eligible locomotive with the fewest carriages on that line; carriage minus safely removes the last body from the eligible locomotive with the most carriages. Queued locomotives are ineligible, and a carriage cannot be removed when doing so would overfill its locomotive.

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
obs, reward, done, info = env.step(
    {"type": "assign_locomotive", "path_index": 0}
)
obs, reward, done, info = env.step(
    {"type": "attach_carriage", "path_index": 0}
)
obs, reward, done, info = env.step(
    {"type": "replace_path", "path_index": 0, "stations": [0, 2, 1]}
)
obs, reward, done, info = env.step(
    {"type": "detach_carriage", "path_index": 0}
)
obs, reward, done, info = env.step(
    {"type": "unassign_locomotive", "path_index": 0}
)
obs, reward, done, info = env.step({"type": "remove_path", "path_index": 0})
```

### API
- `MiniMetroEnv(dt_ms: int | None = None, *, reward_mode: str = "deliveries")`
  - `dt_ms` is the default simulated milliseconds advanced after each `step(...)`.
  - If `dt_ms=None`, time only advances when you pass `dt_ms` to `step(...)`.
  - `reward_mode="deliveries"` rewards newly delivered passengers and is the default objective. `reward_mode="line_credits_delta"` explicitly reconstructs the legacy spendable-credit delta, including negative rewards when credits buy a line.
- `reset(seed: int | None = None) -> observation`
  - Resets the game and returns the initial observation.
  - If `seed` is provided, independent session-owned Python and NumPy random streams make gameplay mechanics, array views, and rendered pixels deterministic without changing host-global RNG state. Opaque entity ID strings remain unique per runtime session and should not be compared across resets.
  - A fresh game uses `env.mediator.overdue_passenger_threshold == 2`: the first station passenger at the 40-second limit warns without ending the game, and the second ends it. The deprecated writable `max_waiting_passengers` mediator alias controls the same value for older callers.
- `step(action: dict | None = None, dt_ms: int | None = None) -> (observation, reward, done, info)`
  - Applies one action, optionally advances time, then returns:
    - `observation`: latest state
    - `reward` (`int`): delta for the selected reward mode; under the default this is newly delivered passengers
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
  - Removal conserves riders: onboard passengers alight at their locomotive's current or nearest route station (destination-shape matches count as deliveries), rejoin station queues past the normal capacity if needed, and replan; the whole transaction restores exact prior state if any step fails.
- `{"type": "replace_path", "path_index": k, "stations": [i0, i1, ...], "loop": bool}`
- `{"type": "replace_path", "path_id": "...", "stations": [i0, i1, ...], "loop": bool}`
  - Requires exactly one selector: either an existing path index or its nonempty id string.
  - `stations` must be an exact list of at least two active-station integer indices. After an optional single trailing copy of the first index is removed for a loop, every index and resolved station object must be unique.
  - `loop` is optional and defaults to `False`; when present it must be a boolean. Unrelated extra keys are tolerated.
  - A safe replacement preserves the path object, public id, color/button ownership, metros, riders, and each metro's physical pose while rebuilding route geometry. Waiting riders replan immediately; onboard riders keep a fresh marker to their next safe alight and replan there.
  - Invalid, ambiguous, or continuity-breaking replacements fail atomically with `action_ok=False`.
- `{"type": "assign_locomotive", "path_index": k}`
- `{"type": "assign_locomotive", "path_id": "..."}`
  - Requires exactly one selector resolving to one active, completed line.
  - Appends one new locomotive to that line when inventory is available. Multiple locomotives may serve the same line.
- `{"type": "unassign_locomotive", "path_index": k}`
- `{"type": "unassign_locomotive", "path_id": "..."}`
  - Requires exactly one selector resolving to one active, completed line with a nonqueued locomotive.
  - Prefers the last empty eligible locomotive; when every nonqueued locomotive is occupied, selects the one with the fewest riders (latest line order breaks ties). A queued locomotive cannot board; an occupied queued locomotive drains its riders at real stations and returns to inventory once empty.
- `{"type": "cancel_unassignment", "path_index": k}`
- `{"type": "cancel_unassignment", "path_id": "..."}`
  - Requires exactly one selector resolving to one active, completed line with at least one queued locomotive.
  - Restores the earliest queued locomotive to normal service with riders and carriages intact. Live-only: persisted recursive and agent-play recordings reject this action at every schema version.
- `{"type": "attach_carriage", "path_index": k}`
- `{"type": "attach_carriage", "path_id": "..."}`
  - Requires exactly one selector resolving to one active, completed line with an eligible nonqueued locomotive and available carriage inventory.
  - Selects the eligible locomotive with the fewest attached carriages, breaking ties by line order, and attaches one new six-seat carriage.
- `{"type": "detach_carriage", "path_index": k}`
- `{"type": "detach_carriage", "path_id": "..."}`
  - Requires exactly one selector resolving to one active, completed line with a safely detachable carriage.
  - Selects the eligible locomotive with the most carriages, breaking ties by latest line order, and removes its last carriage only when the remaining capacity can hold every onboard passenger.
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

Any unknown `type`, malformed action payload, or rejected action returns `info["action_ok"] == False` without mutating game state or advancing time.

### `step(..., dt_ms=...)` behavior
- `dt_ms` argument to `step(...)` overrides constructor `dt_ms` for that call.
- If effective `dt_ms` is an integer, simulation advances by that many milliseconds.
- If effective `dt_ms` is `None`, action is applied but time is not advanced.
- If the action is rejected, no simulation time advances for that step.
- If the environment is already game-over, no simulation time advances regardless of `dt_ms`.

### Observation shape
`observation` is:
- `observation["structured"]`: Python dict/list representation
  - includes `stations`, `paths`, `metros`, `carriages`, `passengers`, labeled `fleet` counts, lifetime `deliveries`, spendable `line_credits`, `time_ms`, `steps`, `is_paused`, `is_game_over`, and station/path/metro/passenger ID-to-index maps in `index`.
  - `fleet` contains locomotive total/assigned/available/queued and carriage total/assigned/available counts. Both available values are read-only nonnegative differences derived from canonical assigned Metro compositions; there is no preconstructed carriage object pool.
  - Each structured Metro entry includes its total `capacity`, ordered `carriage_ids`, and exact boolean `unassignment_queued`; each structured carriage records its ID, immutable capacity, owning Metro ID, and attachment index.
  - deprecated structured `score` mirrors `line_credits`; on `Mediator`, writable `score` and `total_travels_handled` compatibility properties alias `line_credits` and `deliveries` respectively.
- `observation["arrays"]`: NumPy-friendly arrays/lists
  - includes station positions/types/counts, path station-index sequences, metro positions/path indices, passenger destination types and locations.

### Save and load

`src/save_game.py` exposes the programmatic save/load API for `Mediator` state (GM-07b; the human application shell autosaves through it since GM-07c):

```python
import save_game

document = save_game.serialize_game(env.mediator)   # strict schema-v1 dict, never mutates the game
save_game.save_game(env.mediator, "saves/slot1.save.json")  # atomic canonical write
mediator = save_game.load_game("saves/slot1.save.json")     # read + validate + reconstruct
mediator = save_game.deserialize_game(document)             # reconstruct from an in-memory document
```

- Save documents are versioned strict JSON (`save_schema.SAVE_SCHEMA_VERSION == 1`, `stateContract "mini-metro-save-v1"`, `rulesVersion "rules-v1"`). `save_schema.validate_save(document)` rejects unknown/missing keys, wrong scalar types (including bool-as-int), forward versions, malformed or out-of-domain RNG state, ID-grammar violations, path or metro references to locked stations, inconsistent bound-service records, and duplicate or dangling entity references; `load_game` additionally rejects duplicate JSON object keys at every level. Every rejection raises `ValueError`.
- Bytes on disk are the pinned canonical encoding (`save_schema.canonical_save_bytes`: sorted-key, ASCII, compact separators, trailing LF). Saves go through a save-local atomic writer (mkstemp, fsync, `os.replace`), so a failed save leaves an existing destination untouched and no temporary file behind. The default directory name is `config.save_dir_name` (`saves/`, git-ignored); all functions accept explicit paths.
- Saving is permitted only at a quiescent input boundary: an active path-creation, redraw, or edit gesture raises `ValueError` (a bare pressed mouse button does not block).
- The human application shell (`src/main.py`) drives one canonical autosave slot at `saves/autosave.json`: it writes on opening the pause menu and on Exit to Title, keeps that save on a mid-run window close, deletes it at game over, and offers Continue on the title screen. Every autosave is best-effort and never blocks play or exit; the isolation-scanned headless, agent, recursive, and RL surfaces gain no save import.
- A loaded game is checkpoint-identical to the saved one, both RNG streams included, and replays the identical seeded trajectory as a never-saved control, in the same process and across fresh processes replaying the same save file. Each metro's bound station-service action (with its fractional boarding timers) persists in the document and restores verbatim — including boundaries where the bound action is legitimately stale after a same-tick cross-metro effect — so post-load service resumes exactly like the never-saved game. Held pause reasons (`user`, `menu`) restore verbatim, so a game saved from the pause menu loads paused; `release_pause_reason("menu")` resumes it.
- Entity ID strings survive save/load. Path IDs are structured-action selectors: a `path_id` observed before saving keeps selecting the same line against the loaded `Mediator`. Station, metro, carriage, and passenger IDs are stable observation/reference identity only — no structured action currently selects by them. IDs are minted per process, so two independently built games never share IDs (and their save files differ even under the same seed); determinism guarantees apply to reloading and replaying a given save file.
- A save whose `numPaths`, `numMetros`, or `numCarriages` disagrees with the running config is rejected; any trajectory-affecting balance-config change bumps the save schema version (see D-026). The frozen v1 example lives at `scripts/fixtures/save-v1.json`.

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

Live `info` dictionaries contain protocol and pointer bookkeeping, not hidden stations, routes, deliveries, or simulation state. Game-level values appear only in terminal episode metrics after the last action: `deliveries` is the lifetime objective, while the legacy `display_score` field means remaining line credits. The deterministic helper in `rl.privileged_oracle` is deliberately separate and is used only by tests and the scripted curriculum demonstrator.

Fresh training defaults to SB3-Contrib `recurrent_ppo` with eight spawned environments, recurrent minibatches of 64, and the resource-profiled ten-frame multiscale history `[128, 64, 7, 6, 5, 4, 3, 2, 1, 0]`. At the default 10 Hz decision rate, the 30 RGB input channels preserve dense local motion over the last 0.7 seconds plus route context 6.4 and 12.8 seconds back. `MiniMetroCNN` extracts 256 visual features, then separate one-layer, 256-unit actor and critic LSTMs carry episode memory across decisions. Feed-forward PPO retains its prior batch size of 256 and, when selected without a history flag, retains the legacy eight-contiguous-frame ablation rather than silently inheriting the recurrent default.

The recurrent hidden state persists within one game and resets at the next game's episode boundary; a new training or evaluation process also starts with blank hidden state. Learned network weights are different: authenticated checkpoints persist them across process restarts and resumed training.

Every fresh artifact uses training-manifest v2, which binds a canonical history descriptor and separate `historyFingerprint` without changing the single-frame task fingerprint. Genuine manifest-v1 artifacts derive the historical contiguous offsets `[frameStack-1, ..., 0]` in memory and retain their exact v1 serialized shape. Fresh training, resume, and evaluation now build the bounded descriptor-driven vector ring from that exact identity. A mismatched explicit history is rejected before model bytes are opened, including equal-channel layouts whose temporal meaning differs; a different channel count is also rejected by SB3 before learning or evaluation.

The default delivery-delta rewards sum exactly to the episode's terminal total deliveries. Fresh recurrent runs therefore use `gamma=1.0` and `gae_lambda=0.99`, and evaluation reports `meanDeliveries` as the primary metric for the objective of maximizing passengers delivered before the game ends. Evaluation also reports game-over and horizon-truncation counts/rates, marks the primary metric as censored whenever any episode hits the external horizon, and reports `meanDeliveriesAmongGameOverEpisodes` separately. A horizon-truncated delivery count is a right-censored lower bound, not a final game-over delivery result.

Train the default recurrent policy and evaluate the resulting strict manifest with:

```powershell
python scripts/train_rl.py --total-timesteps 1000000 --n-envs 8 --device auto
python scripts/evaluate_rl.py output/rl/recurrent_ppo-RUN-ID/final_model.zip --episodes 10
```

Standalone evaluation uses the run manifest's recorded evaluation seed by default; pass `--seed` only when you intentionally want a different deterministic episode suite.

Run the unpromoted twelve-frame multiscale candidate explicitly when reproducing that ablation:

```powershell
python scripts/train_rl.py --history-layout decision-history-v1 --total-timesteps 1000000 --n-envs 8 --run-dir output/rl/recurrent-multiscale-12
python scripts/evaluate_rl.py output/rl/recurrent-multiscale-12/final_model.zip --episodes 10
```

Profile the primary history campaign only from a committed source tree with no tracked/staged changes or unexpected untracked files. The pre-existing `.agents/` tree and ignored `output/` evidence are declared exclusions. This launches nine fresh worker processes in a cyclically balanced order, each running one warm-up and one measured 8-environment x 128-step recurrent update. Pin both Torch thread counts explicitly; `24/24` is the reviewed setting for the current Windows machine:

```powershell
python scripts/profile_rl_history.py --campaign primary --torch-threads 24 --torch-interop-threads 24 --output-dir output/rl-profile/gm02d-primary
```

The July 13 primary run was operationally invalid because one eight-frame control repeat exceeded the preregistered 100 ms sampling-gap limit; its aggregate ratios are therefore non-authoritative. The twelve-frame target repeats also exceeded the strict historical RAM cap. The required fresh fallback campaign completed with all eight interleaved repeats valid and promoted the exact ten-frame history:

```powershell
python scripts/profile_rl_history.py --campaign fallback --torch-threads 24 --torch-interop-threads 24 --output-dir output/rl-profile/gm02d-fallback
```

The fallback median process-tree peak was 3,636,346,880 bytes for eight contiguous frames and 4,043,184,128 bytes for ten multiscale frames (1.1119x, below the 1.25x gate and the 4,197,256,790-byte historical cap). Median end-to-end throughput was 86.3032 versus 73.2052 FPS (0.8482x, above the 0.75x gate). These gigabyte values are summed instantaneous working-set RAM across the trainer and eight environment processes, not disk output, and may double-count shared pages; the two complete raw campaign directories together occupy only about 16.7 MiB. The supervisor attaches before each worker imports NumPy/Torch, samples the launcher and all discovered descendants at an absolute 50 ms cadence, and invalidates a repeat on incomplete process queries or timing gaps/acquisitions over 100 ms. Full JSONL samples, worker logs, and run summaries stay under ignored `output/`; the committed compact evidence authenticates the raw samples and stdout/stderr logs by SHA-256, authenticates each aggregate summary by size and SHA-256, and preserves the parsed per-run evidence semantically. This promotion proves engineering safety only; matched passenger-delivery efficacy remains a separate multi-seed experiment.

Use feed-forward PPO and an explicit contiguous frame stack as controlled ablations. `--frame-stack` and `--history-layout` are mutually exclusive because channel count alone does not identify temporal meaning:

```powershell
python scripts/train_rl.py --algorithm ppo --frame-stack 4 --total-timesteps 1000000 --n-envs 8 --run-dir output/rl/ppo-four-frame
```

For a quick pipeline smoke test, use a new empty run directory:

```powershell
python scripts/train_rl.py --total-timesteps 128 --n-envs 1 --max-episode-steps 4 --run-dir output/rl/smoke
python scripts/evaluate_rl.py output/rl/smoke/final_model.zip --episodes 1
```

Resume from any authenticated periodic or final checkpoint into a new run directory; the saved manifest supplies the algorithm and exact history identity when those flags are omitted, and explicit frame-count or named-layout mismatches are rejected. Repeat any non-default task flags so they match the parent manifest:

```powershell
python scripts/train_rl.py --resume output/rl/recurrent_ppo-RUN-ID/checkpoints/mini_metro_recurrent_ppo_100000_steps.zip --run-dir output/rl/resumed --total-timesteps 500000
```

Every run immediately writes a recovery checkpoint and `training-manifest.json`, writes each new periodic checkpoint before refreshing the manifest and authenticated index, then saves and authenticates the final model. The manifest authenticates a versioned artifact index, and the evaluator hashes and parses one exact index snapshot before loading the exact model bytes it authenticated; a swapped or partially written model is never reopened by path for SB3. It also records the exact pixel/control protocol, task horizon and reward, temporal descriptor and fingerprint, compatibility `frameStack` summary, hyperparameters, callback intervals, requested/resolved device, seeds, gameplay dependency versions, Git state, an environment-content fingerprint, and a separate trainer-source fingerprint that includes both lockfiles plus the history/manifest implementation. Resumed runs retain parent manifest/model digests and use the newly requested seed consistently in the model and environments.

Resume and evaluation fail closed on protocol, task, history, content, trainer-source, runtime, or artifact drift. History mismatch has no drift override because it changes channel meaning. `--allow-content-drift`, `--allow-training-drift`, and `--allow-runtime-drift` are explicit, tagged compatibility overrides; use the content override when intentionally testing an old model against new stations, mechanics, or graphics, and use the other overrides only when the reported implementation/runtime difference is understood. Legacy feed-forward PPO artifacts created before the recurrent dependency and training-source contract may require `--allow-training-drift` and/or `--allow-runtime-drift` after the reported differences have been reviewed.

The recurrent default is a research-backed production baseline, not a claim that a short smoke run learns competent play. Low-level line construction is a sparse multi-action problem, so `rl.demonstrator.run_delivery_demonstration` provides a deterministic curriculum trajectory that creates a route, assigns a locomotive, attaches one carriage through the visible player controls, and reaches a real delivery for the reference seed. See [RL model selection for the player-pixel task](docs/rl-model-selection.md) for the CNN, recurrent PPO, Transformer, visual-transformer, and Dreamer comparison plus the experiment and reporting protocol.

# Recursive self-improvement loop

The deterministic v5 fixture at `scripts/fixtures/recursive-playtest.json` records the deliveries reward, overdue-passenger threshold `2`, explicit-locomotive-assignment contract, and explicit-carriage-attachment contract, then uses seed `42` to create a line, assign and attach by replay-safe path index, advance time, exercise pause/resume, remove the line, and verify rejected actions. Frozen v1/v2/v3/v4 fixtures retain their historical schemas and action meanings through shared compatibility transitions; fleet actions in v4/v5 and carriage actions in v5 are index-only so evidence never stores process-local path UUIDs. Recursive v5 uses UUID-free checkpoint schema v4, whose Metro and carriage records form an exhaustive indexed ownership bijection. The harness drives `MiniMetroEnv` directly; it does not use the pygame GUI clock or an LLM.

Run the Node contract tests and one proposal-only recursive pass with:

```powershell
npm test
npm run playtest:recursive
```

The canonical `npm test`, `npm run playtest:verify`, and `npm run playtest:recursive` commands enter `scripts/civ-engine-guard.mjs` after a trusted npm/Node bootstrap. Once the shared startup assertion confirms that `NODE_OPTIONS` is unset or empty and `process.execArgv` is empty, `npm test` accepts no forwarded arguments and always launches the complete `node --test` suite, so forwarded package-script arguments cannot become child Node options or file operands; use direct `node --test <files>` only for focused development runs. The guard parses recursive arguments before its effects, acquires the setup-exclusive verification lease, ownership-checks both before and after verifying the isolated engine, launches only its fixed Node command body with `shell: false`, holds the lease until that child completes, and releases it in `finally`; concurrent setup or another guarded command is excluded while each honors the same lock. The token lock is advisory against out-of-band filesystem tampering during child execution: the guard does not continuously monitor it, and release fails closed when lost ownership remains observable. Verification/spawn and release failures are preserved together behind a categorical guard diagnostic. The exact root `.npmrc` pins npm's prelude to `loglevel=silent`, so the standard canonical invocation does not echo its expanded command line before that diagnostic; setup rejects configuration drift. Suppressing lifecycle prehooks alone still reaches the in-body guard after a clean bootstrap.

The tracked `package.json` and `.npmrc`, the selected top-level npm and Node executables, and their pre-start environment/configuration are an explicit trusted bootstrap boundary for both setup and guarded commands. Both entry-point mains categorically refuse their own effects when they observe non-empty `NODE_OPTIONS` or `process.execArgv`, but Node applies those mechanisms before loading the modules, so the assertion detects taint only after any preload has already run and cannot undo pre-main effects. Caller-selected bootstrap overrides outside this boundary are not attested. By contrast, once setup starts cleanly, every Git/npm/build child receives the documented scrubbed allowlisted environment, including removal of inherited `NODE_OPTIONS` and npm behavior variables.

Use another strict scenario or keep artifacts under a different subdirectory of `output/` with:

```powershell
npm run playtest:recursive -- --scenario path/to/scenario.json
npm run playtest:recursive -- --output-root output/my-recursive-runs
```

Normal recursive runs fail closed when relevant runtime source under `src/`, `scripts/`, `package*.json`, or `requirements*.txt` is dirty. They also require ESM resolution to reach the exact physical `/.civ-engine-pin/` checkout and require that checkout to match the pinned version, Git commit, and full runtime-tree digest, so a sibling link, nested package shadow, or modified ignored `dist/` build cannot masquerade as the pin. A wrong remote, attached HEAD, physical location, dependency slot, runtime entry, or unavailable runtime is never overridable. Commit or restore local source first. The setup verifier's `--verify-only --allow-dirty` mode is reserved for recursive execution: its npm prehook is defense in depth, while the public command body and recursive body share one exact parser and select canary verification only when `--allow-dirty` occupies an option position, never when it is the value consumed by `--scenario` or `--output-root`; unknown or missing recursive arguments fail before lease acquisition, verification, or body launch. Tests and standalone verification always remain strict. The canary retains attributable source inventories, dirty or mismatched status, and the local patch with its evidence:

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
