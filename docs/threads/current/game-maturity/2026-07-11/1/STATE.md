# Game maturity resume state

Last updated: 2026-07-12

Active goal thread: `019f5286-dfca-75e1-9e79-58719dbe1efb`

Current increment: GM-02 - Add strategically spaced long visual history

Current substep: GM-02b - vectorized temporal ring and lifecycle tests

Current status: GM-02b implementation, local gates, and adversarial review are green; stage Commit A without `.agents/`

Durability transaction: GM-02a Commit B `ab8e6eb1d9a4006b514d113e6ad2b93c3f6d9b48` is remotely green; GM-02b Commit A is locally ready

Last remotely finalized work unit: GM-02a at Commit B `ab8e6eb1d9a4006b514d113e6ad2b93c3f6d9b48`, which passed [run 29207697382](https://github.com/yanfengliu/python_mini_metro/actions/runs/29207697382)

Expected remote implementation baseline: `ab8e6eb1d9a4006b514d113e6ad2b93c3f6d9b48`

Current transaction marker: `[GM-02b:A]`

## Resume here

1. Inspect and stage only the GM-02b implementation, tests, docs, review artifacts, and cursor; never stage the pre-existing `.agents/` tree.
2. Commit `[GM-02b:A]`, push, and wait for pinned build plus RL-smoke success.
3. Record A's exact SHA and remote run in Commit B, push, and wait for B's remote success before beginning GM-02c runtime integration.

## Increment ledger

| ID | Status | Commit | Remote CI | Notes |
| --- | --- | --- | --- | --- |
| GM-00 | complete | `16a0e73` / `0411e68` | [A run 29172923371](https://github.com/yanfengliu/python_mini_metro/actions/runs/29172923371) and [B run 29173071970](https://github.com/yanfengliu/python_mini_metro/actions/runs/29173071970) succeeded | Durable plan and reviews |
| GM-01 | complete | `5e00763` / `6c77033` / `3523ea4` / `18ef714` / `648025f` / `14050af` | GM-01a/GM-01b/GM-01c A/B green | Canonical objective and baseline rules remotely finalized |
| GM-02 | in progress | `bab6b15` / `ab8e6eb` | GM-02a A/B green | GM-02b temporal ring locally green; A/B pending |
| GM-03 | pending | - | - | Mediator and test decomposition |
| GM-04 | pending | - | - | Isolated pinned civ-engine local setup |
| GM-05 | pending | - | - | Route editing |
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
| GM-02b | local green | `[GM-02b:A]` / pending | - | Temporal ring, lifecycle/resource tests, and adversarial refutation pass |
| GM-02c | pending | - | - | CLI/train/eval/legacy integration |
| GM-02d | pending | - | - | Resource profile and default promotion |
| GM-03a | pending | - | - | Split mediator tests |
| GM-03b | pending | - | - | Extract progression |
| GM-03c | pending | - | - | Extract route planning |
| GM-03d | pending | - | - | Extract topology/path lifecycle |
| GM-03e | pending | - | - | Extract passenger flow |
| GM-03f | pending | - | - | Extract input/layout facade |
| GM-04a | pending | - | - | Isolated pin contract |
| GM-04b | pending | - | - | Setup/verification command |
| GM-04c | pending | - | - | Complete pinned Node-suite proof and mismatch proof |
| GM-05a | pending | - | - | Atomic path replacement |
| GM-05b | pending | - | - | Selected-line redraw |
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
| GM-12a | pending | - | - | Freeze benchmark/baselines |
| GM-12b | pending | - | - | Create per-configuration/seed experiment matrix |
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

- `main` and `origin/main` are equal at GM-02a Commit B `ab8e6eb1d9a4006b514d113e6ad2b93c3f6d9b48` before GM-02b Commit A.
- The only pre-existing untracked path is `.agents/`; preserve it.
- The live sibling `../civ-engine` is 2.4.1 while this repository pins 2.2.0, so unisolated local `npm test` fails by design. GM-04 owns the durable setup fix.
- The fleet `loop-ops/DIRECTIVES.md` does not list this repository as an active scheduled shift. Use repo-local persistent state and bare verified passes unless the owner later activates it there.

## Blockers

- None.
