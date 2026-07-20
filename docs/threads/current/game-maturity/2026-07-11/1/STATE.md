# Game maturity resume state

Last updated: 2026-07-20

Active goal thread: `019f7c1a-897b-7c31-9662-4edbb4e128a6`

Current increment: GM-05 - Route editing

Current substep: GM-05b - selected-line mouse redraw

Current status: GM-05b implementation and fresh three-lane adversarial re-review are clean; the final core suite passed 674 tests with 12 expected optional-stack skips, the exact RL environment passed 677 tests without skips, historical input/replay identities remain green, and the exact 38-path pre-commit, scoped staging, and cached audits passed; Commit A is ready to create and push

Durability transaction: GM-05a is remotely finalized through Commit B; GM-05b implementation Commit A is the active transaction and no GM-05b commit exists yet

Last remotely finalized work unit: GM-05a at Commit B `47b93491662ebe56a38aba8653d868ae66249d6c`, which passed [run 29776631928](https://github.com/yanfengliu/python_mini_metro/actions/runs/29776631928)

Expected remote implementation baseline: `47b93491662ebe56a38aba8653d868ae66249d6c`, whose exact [run 29776631928](https://github.com/yanfengliu/python_mini_metro/actions/runs/29776631928) passed `build` job `88467464598` and `rl-smoke` job `88467464551`

Current transaction marker: `[GM-05b:A]`

## Resume here

1. Preserve remotely finalized GM-05a history, the pre-existing `.agents/` tree, unrelated ignored `output/`, the retained isolated pin, and the live `../civ-engine` sibling outside GM-05b.
2. Commit and push the exact reviewed 38-path `[GM-05b:A]` payload.
3. Wait for Commit A's exact `build` and `rl-smoke` jobs, then deliver evidence-only `[GM-05b:B]`; GM-05c remains closed through B's own exact workflow.

## Increment ledger

| ID | Status | Commit | Remote CI | Notes |
| --- | --- | --- | --- | --- |
| GM-00 | complete | `16a0e73` / `0411e68` | [A run 29172923371](https://github.com/yanfengliu/python_mini_metro/actions/runs/29172923371) and [B run 29173071970](https://github.com/yanfengliu/python_mini_metro/actions/runs/29173071970) succeeded | Durable plan and reviews |
| GM-01 | complete | `5e00763` / `6c77033` / `3523ea4` / `18ef714` / `648025f` / `14050af` | GM-01a/GM-01b/GM-01c A/B green | Canonical objective and baseline rules remotely finalized |
| GM-02 | complete | `bab6b15` / `ab8e6eb` / `a5744c0` / `53bc510` / `9b75f37` / `812e426` / `02ceb54` / `3c68472` / `36cf058` / `dc35cd6` / `27a0304` / `60b4174` | GM-02a through GM-02e A/B green | Long-history baseline and hybrid-memory research remotely finalized |
| GM-03 | complete | `83d02d4` / `fbcb31d` / `36e89d9` / `00ea38c` / `1b751e4` / `5e6186d` / `9321dcd` / `b1e419e` / `7ac89cf` / `7ff9d9c` / `c676c30` / `be0b1e1` | GM-03a through GM-03f A/B green | Mediator decomposition remotely finalized |
| GM-04 | complete | `8cff620` failed setup; `16d7860` failed downstream; `069973c` implementation success; `41ecfc6` GM-04b finalization; `60ac953` / `8c4ba85` GM-04c A/B | [run 29748574695](https://github.com/yanfengliu/python_mini_metro/actions/runs/29748574695) and [run 29753292420](https://github.com/yanfengliu/python_mini_metro/actions/runs/29753292420) failed; [run 29757294004](https://github.com/yanfengliu/python_mini_metro/actions/runs/29757294004), [run 29758092140](https://github.com/yanfengliu/python_mini_metro/actions/runs/29758092140), [run 29763804498](https://github.com/yanfengliu/python_mini_metro/actions/runs/29763804498), and [run 29764619993](https://github.com/yanfengliu/python_mini_metro/actions/runs/29764619993) succeeded | Isolated pinned recursive tooling remotely finalized |
| GM-05 | in progress | `c7effd8` / `47b9349` | [GM-05a A run 29776047898](https://github.com/yanfengliu/python_mini_metro/actions/runs/29776047898) and [B run 29776631928](https://github.com/yanfengliu/python_mini_metro/actions/runs/29776631928) succeeded | GM-05a remotely finalized; GM-05b implementation reviewed and locally green before Commit A |
| GM-06 | pending | - | - | Fleet and carriages |
| GM-07 | pending | - | - | Menus, save/resume, high scores |
| GM-08 | pending | - | - | Tutorial, settings, audio |
| GM-09 | pending | - | - | Maps, rivers/tunnels |
| GM-10 | pending | - | - | Weekly progression and upgrades |
| GM-11 | pending | - | - | Evidence-based balance and recursive playtest |
| GM-12 | pending | - | - | Multi-seed training and held-out evaluation |
| GM-13 | pending | - | - | Final reconciliation and release review |

## Work-unit and phase ledger

| Work unit or phase | Status | Commit A / CI A | Commit B marker / CI B | Exact resume detail |
| --- | --- | --- | --- | --- |
| GM-00a | complete-local | - | - | Independent live-code plan design incorporated |
| GM-00b | complete-local | - | - | Codex findings resolved; three compensating re-review lanes approved |
| GM-00c | complete | `16a0e73` / run `29172923371` success | - | Plan Commit A passed build and RL smoke |
| GM-00d | complete | - | `0411e68` / run `29173071970` success | Plan finalization Commit B passed build and RL smoke |
| GM-01a | complete | `5e00763` / run `29175325493` success | `6c77033` / run `29175470189` success | Canonical semantics and persisted compatibility schemas remotely finalized |
| GM-01b | complete | `3523ea4` / run `29177705475` success | `18ef714` / run `29177848669` success | HUD, game-over, cadence, and docs remotely finalized |
| GM-01c | complete | `648025f` / run `29180986088` success | `14050af` / run `29181130841` success | Threshold-two runtime and v3 replay migration remotely finalized |
| GM-02a | complete | `bab6b15` / run `29207490781` success | `ab8e6eb` / run `29207697382` success | History identity and manifest migration remotely finalized |
| GM-02b | complete | `a5744c0` / run `29209101298` success | `53bc510` / run `29209297952` success | Temporal ring and lifecycle/resource tests remotely finalized |
| GM-02c | complete | `9b75f37` / run `29211060401` success | `812e426` / run `29211292517` success | Descriptor-driven CLI/train/eval/recurrent/legacy integration remotely finalized |
| GM-02d1 | complete | `02ceb54` / run `29293092427` success | `3c68472` / run `29293344902` success | Benchmark harness remotely finalized before measurement |
| GM-02d2 | complete | `36cf058` / run `29297091497` success | `dc35cd6` / run `29297764352` success | Valid fallback promoted exact ten-frame pixel-only default and remotely finalized |
| GM-02e | complete | `27a0304` / run `29299216859` success | `60b4174` / run `29302064550` success | Hybrid/semantic memory research remotely finalized |
| GM-03a | complete | `83d02d4` / run `29303936139` success | `fbcb31d` / run `29304181859` success | Behavior-neutral mediator test partition remotely finalized |
| GM-03b | complete | `36e89d9` / run `29310175226` success | `00ea38c` / run `29311017088` success | Network progression ownership remotely finalized |
| GM-03c | complete | `1b751e4` / run `29351838271` success | `5e6186d` / run `29352432028` success | Route-planning ownership remotely finalized |
| GM-03d | complete | `9321dcd` / run `29386046847` success | `b1e419e` / run `29386306430` success | Path-lifecycle extraction remotely finalized |
| GM-03e | complete | `7ac89cf` / run `29719845761` success | `7ff9d9c` / run `29720233286` success | Passenger-flow extraction remotely finalized |
| GM-03f | complete | `c676c30` / run `29724753115` success | `be0b1e1` / run `29725101133` success | Input/layout coordination extraction remotely finalized |
| GM-04a | complete | `585dc60` / run `29730625404` success | `28a6c7e` / run `29731075431` success | Isolated pin contract remotely finalized |
| GM-04b | complete | `8cff620` / run `29748574695` setup failure; `16d7860` / run `29753292420` downstream failure; `069973c` / run `29757294004` success | `41ecfc6` / run `29758092140` success | Corrective history and safe setup/verifier remotely finalized |
| GM-04c | complete | `60ac953` / run `29763804498` success | `8c4ba85` / run `29764619993` success | Final reproducibility and mismatch proof remotely finalized |
| GM-05a | complete | `c7effd8` / run `29776047898` success | `47b9349` / run `29776631928` success | Atomic replacement remotely finalized |
| GM-05b | implementation-reviewed | - | `[GM-05b:A]` active | Redraw, preview, and no-tick continuity implementation plus fresh re-review are clean; final local delivery gates remain |
| GM-05c | pending | - | - | Endpoint/interior editing handles |
| GM-06a | pending | - | - | Locomotive inventory |
| GM-06b | pending | - | - | Assignment and redistribution |
| GM-06c | pending | - | - | Carriages |
| GM-06d | pending | - | - | Fleet edge cases |
| GM-07a | pending | - | - | AppController and screens |
| GM-07b | pending | - | - | Versioned snapshots and public IDs |
| GM-07c | pending | - | - | Atomic autosave/Continue |
| GM-07d | pending | - | - | Map/rules high scores |
| GM-08a | pending | - | - | Typed settings |
| GM-08b | pending | - | - | Domain events/audio/null backend |
| GM-08c | pending | - | - | Real-control tutorial |
| GM-09a | pending | - | - | Classic map identity/parity |
| GM-09b | pending | - | - | Terrain and first river map |
| GM-09c | pending | - | - | Crossing/tunnel accounting |
| GM-09d | pending | - | - | Second map |
| GM-09e | pending | - | - | Third map |
| GM-09f | pending | - | - | Menu/save/high-score/RL integration |
| GM-10a | pending | - | - | Calendar/pause reasons |
| GM-10b | pending | - | - | Dedicated-RNG offers |
| GM-10c | pending | - | - | Choice controls |
| GM-10d | pending | - | - | Line upgrades |
| GM-10e | pending | - | - | Locomotive upgrades |
| GM-10f | pending | - | - | Carriage upgrades |
| GM-10g | pending | - | - | Tunnel upgrades |
| GM-10h | pending | - | - | Persistence/replay reconciliation |
| GM-11a | pending | - | - | Scenario fixtures |
| GM-11b | pending | - | - | Paired scripted baselines |
| GM-11c | pending | - | - | Sustained manual evidence |
| GM-11d | pending | - | - | Recursive fix/prove passes |
| GM-11e | pending | - | - | One-family balance tuning |
| GM-12a | pending | - | - | Freeze post-balance benchmark; inventory and draft observation/conformance rules |
| GM-12b | pending | - | - | Implement/test observation candidates; freeze versions and experiment matrix |
| GM-12c | pending | - | - | Replace with one remotely finalized transaction row per training configuration/seed |
| GM-12d | pending | - | - | Replace with one remotely finalized transaction row per checkpoint/held-out seed |
| GM-12e | pending | - | - | Clustered statistics/resource curves |
| GM-12f | pending | - | - | Promotion decision |
| GM-13a | pending | - | - | Full local gates and audits |
| GM-13b | pending | - | - | Three-lens review/fix/re-review |
| GM-13c | pending | - | - | Docs/archive/final remote verification |

GM-00a/GM-00b are design/review phases inside the GM-00 transaction; GM-00c/GM-00d are its Commit-A/Commit-B phases and are not independent green work units. Failing TDD tests live only in the working tree inside a work unit and are never remotely finalized red.

Before GM-12c starts, replace its placeholder with one row per configuration and training seed. Before GM-12d starts, add one row per authenticated checkpoint and held-out evaluation seed. Each row gets its own `[<row>:A]` and `[<row>:B]` transaction, exact artifact locator/digests, and remote CI results before the next row begins. The current cursor must name the exact row; directory presence is never completion evidence.

## Known external state

- GM-05a Commit B is remotely green at `47b93491662ebe56a38aba8653d868ae66249d6c`; before the GM-05b plan edit, `main` and `origin/main` equal that SHA and only the pre-existing `.agents/` tree is untracked. Unrelated ignored `output/` and the retained ignored pin remain outside the tracked transaction.
- GM-05b intentionally advances the environment-content fingerprint from `2aaff2849ab18c0f07bdb009b0cb55d380bad3b49fa8a550384b769fa172802b` to `81671dfe5457eaec53c4e64b3e3921587b470db470b2a7c6c54cf394da5dd4a0`; protocol `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`, default-task `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`, and fidelity-task `cd713a6891d8e74dab1aac2ded2edc88a727cb2b5b420948c65731d3a0eb3418` identities remain exact.
- The live sibling `../civ-engine` is clean version 2.4.1 at commit `2632daca2ea1d1330cf1270962941005354f775b` while root resolution now targets the retained clean 2.2.0 pin at `e0cb614a516c449159a4562c2ac45bd40bffd3df`; the sibling remains untouched and outside setup.
- Retained ignored recursive evidence lives at `output/recursive/recursive-2026-07-20T16-21-12-855Z-ea664784`. Repeated-setup stdout, the 245/241/four-skip suite output, and isolated-drill JSON were terminal-observed ephemeral evidence rather than retained artifacts; the exact isolated fixture was removed.
- Four old ignored output pre-commit cache roots remain retained because ACL-blocked descendants prevent safe complete removal: `output/gm04a-precommit-cache`, `output/gm04b-a3-precommit-cache`, `output/gm04b-final-precommit-cache`, and `output/gm04b-precommit-cache-final2`. Exact task cache `C:\tmp\python-mini-metro-gm04b-precommit-cache` was removed after the final GM-04c Commit B hook run.
- The fleet `loop-ops/DIRECTIVES.md` does not list this repository as an active scheduled shift. Use repo-local persistent state and bare verified passes unless the owner later activates it there.

## Blockers

- No blocker to GM-05b Commit A delivery. A pre-existing concurrent civ-engine setup lease remains outside this work and was not deleted or disturbed; exact hosted builds will run the guarded Node suite. Safe cleanup of the four old ignored output cache roots remains ACL-limited and outside this payload.
