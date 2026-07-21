# GM-06a conserved locomotive inventory diff ledger

Status: remotely finalized through exact-green implementation Commit A and evidence-only Commit B

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

Commit A's exact staged payload contained 34 paths: four public/project documents, three parent roadmap documents, three reconciled GM-05c documents, 16 iteration-5 evidence documents, four production Python files, and four test files. Its 1,403 insertions and 41 deletions passed cached whitespace, forbidden-path, credential, and unstaged-drift audits; only the preserved `.agents/` tree remained untracked. Commit A `d587b63` passed run `29795915449`; evidence-only Commit B `0a69d64` passed run `29796331734` and was reconciled by GM-06b.
