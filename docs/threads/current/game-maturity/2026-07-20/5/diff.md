# GM-06a conserved locomotive inventory diff ledger

Status: implementation Commit A is exact-head remote green; evidence-only Commit B is active and GM-06b remains closed

## Intended production surface

- Add one read-only late-derived `Mediator.available_locomotives` property while keeping total and assigned collections canonical and current lifecycle behavior exact.
- Add labeled structured fleet totals and a third HUD line, plus expand the config-owned route-handle HUD exclusion for three lines.
- Leave path-lifecycle mechanics, entity ownership, arrays, checkpoints, replay versions, actions, PlayerPixel info/protocol, carriages, and line-removal rider behavior unchanged.

## Implemented production surface

- `src/mediator.py`: add the read-only late-derived clamped availability property with no backing state.
- `src/env.py`: add exact labeled total/assigned/available structured fleet scalars without changing arrays.
- `src/rendering/game_renderer.py`: render the third HUD line through canonical/legacy/zero resolution while remaining 494 physical lines.
- `src/config.py`: expand the config-owned handle HUD exclusion exactly to `(0, 0, 840, 200)`.

## Intended evidence surface

- Add focused runtime/failure and render/pixel inventory tests plus targeted environment/checkpoint/handle compatibility coverage.
- Update public rules/API, architecture, progress, parent decision/state/evidence, GM-05c downstream reconciliation, and this iteration's reviewed evidence.

## Implemented evidence surface

- `test/test_gm06a_locomotive_inventory.py`: 13 runtime and exact partial-failure tests.
- `test/test_gm06a_inventory_state.py`: 16 observation/checkpoint/read-only and operation-stability tests.
- `test/test_gm06a_inventory_rendering.py`: five exact HUD/font/geometry/purity/low-level-pixel tests.
- `test/test_game_renderer.py`: directly affected canonical/legacy HUD expectations and pixel sensitivity.
- `README.md`, `GAME_RULES.md`, `ARCHITECTURE.md`, `PROGRESS.md`, parent D-021/STATE/EVIDENCE, and iteration 5 plan/review/raw evidence describe the same boundary.

Commit A's exact staged payload contained 34 paths: four public/project documents, three parent roadmap documents, three reconciled GM-05c documents, 16 iteration-5 evidence documents, four production Python files, and four test files. Its 1,403 insertions and 41 deletions passed cached whitespace, forbidden-path, credential, and unstaged-drift audits; only the preserved `.agents/` tree remained untracked. Commit A `d587b63424348c90b3c2f2499dba737e4e18d2dc` passed exact [run 29795915449](https://github.com/yanfengliu/python_mini_metro/actions/runs/29795915449), run number 136: `build` job `88527100922` passed in 1m15s and `rl-smoke` job `88527100934` passed in 5m06s. Commit B changes only five evidence documents and leaves GM-06b closed pending B's exact remote workflow.
