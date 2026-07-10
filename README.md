[![Demo](https://i.imgur.com/xpUow2f.png)](https://youtu.be/W5fCgqlECeI)

# python_mini_metro

This repo uses `pygame-ce` to implement Mini Metro, a fun 2D strategic game where you try to optimize the max number of passengers your metro system can handle. Both human and program inputs are supported. One of the purposes of this implementation is to enable reinforcement learning agents to be trained on it.

# Installation

Activate the Python 3.13 environment and install the game dependencies:

```powershell
conda activate py313
python -m pip install -r requirements.txt
```

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

* If you are running for the first time, install the requirements using `pip install -r requirements.txt`
* Activate the virtual environment by running `conda activate py313`
* Run `python src/main.py`
* Hold down the mouse left button on a station and drag onto other stations to create a path for the metro.
* Press SPACE to pause / unpause the game.
* Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
* View the score on the top left corner of the screen.
* The number of grey circles on bottom of the screen is the number of available metro lines left.
* Click on the colored circle at the bottom to cancel an established line.
* Click on the empty circles at the bottom to buy new lines with scores.

## To play programmatically

Use the Gym-like environment in `src/env.py`:

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
  - If `seed` is provided, Python and NumPy RNG are seeded for deterministic runs.
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

Every default pass creates `output/recursive/<run-id>/` with `source-state.json`, an optional dirty `source-diff.patch`, recorded `inputs.json`, one-row-per-operation `transcript.jsonl`, `findings.authored.json`, `run-result.json`, drive logs, fresh-process replay evidence under `redrive/`, `verification.json`, verified and verification findings, and complete run/pass manifests. Source state carries deterministic SHA-256 inventories for this repository and the resolved linked engine plus relevant Git status, and both manifests embed its validated portable summary. The driver recaptures both sources immediately before finalization; drift produces `source-state.final.json`, an optional final local diff, and a failed pass rather than verified stale evidence. The append-only run and pass ledgers are `output/recursive/ledger.jsonl` and `output/recursive/passes.jsonl`; pending write-ahead intents under `output/recursive/ledger-intents/` repair interrupted manifest/ledger persistence and are removed only after both manifest files and rows are durably confirmed. Everything under `output/` is generated evidence and remains uncommitted.

Authored findings are always `unverified`. The verifier re-drives the exact recorded operations in a fresh process and requires exact replayable input metadata, transcript results, full canonical checkpoint vectors, and finding semantics to match. Only replay-side findings that pass those checks become `verified` with `verificationMethod: "replay"` and an addressed bundle evidence reference to the original run. Any mismatch is an unverified nondeterminism finding and fails the run.

Pass outcomes are `no-fix-candidate`, `proposal-only`, or `run-failed`. `proposal-only` reports the highest-severity verified fix-classified finding; this repository adds no automatic apply or fix arm, so the driving agent must implement the fix through the normal TDD and review workflow, rerun the pass, prove the finding's stable bug class absent, and preserve a regression test. A failed drive, replay, or validation exits nonzero and records `run-failed` manifests and ledger rows.

# Testing

```powershell
python -m unittest -v
npm test
```
