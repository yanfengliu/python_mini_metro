# Game maturity roadmap review - Codex

You are a senior code reviewer. Review the persistent implementation roadmap for evolving `python_mini_metro` from its current playable alpha into a maintainable, content-complete game and validated long-horizon RL testbed. Do not modify files or propose patches. Return only real, important findings with severity, impact, and file/line evidence; if there is no issue, say APPROVED.

Begin your review with the literal token `===BEGIN-REVIEW===` on its own line and end with `===END-REVIEW===` on its own line. Do not emit those markers anywhere else.

Mandatory grounding directive: Verify each claim in the plan against the live codebase - grep for every symbol, function signature, schema key, action, observation field, checkpoint field, renderer behavior, CLI flag, and file path it references; do not approve based on prompt text alone.

Read at minimum:

- `AGENTS.md`, especially planning, validation, documentation, review, and Git requirements.
- `docs/threads/current/game-maturity/2026-07-11/1/PLAN.md`
- `docs/threads/current/game-maturity/2026-07-11/1/STATE.md`
- `docs/threads/current/game-maturity/2026-07-11/1/DECISIONS.md`
- `docs/threads/current/game-maturity/2026-07-11/1/EVIDENCE.md`
- `ARCHITECTURE.md`, `README.md`, `GAME_RULES.md`, and `PROGRESS.md`
- Relevant live code and tests under `src/`, `scripts/`, and `test/`.

Task-specific review questions:

1. Does the durable resume contract prevent false completion, duplicated work, skipped dependencies, stale state, and ambiguous restart points across context compaction and sessions?
2. Is the deliveries/line-credits compatibility plan safe for direct field assignment, structured observations, rewards, recursive findings/checkpoints, agent-play records, pixel terminal metrics, old saved RL artifacts, and deterministic replay?
3. Is threshold two supported only as a bounded initial balance correction, with adequate future evidence requirements?
4. Does `decision-history-v1` with offsets `[128,64,32,16,7,6,5,4,3,2,1,0]` preserve recent interaction context and add meaningful history without an unsafe unmeasured memory claim? Check terminal observations, vector auto-reset, zero padding, manifest v1/v2 compatibility, CLI semantics, content/training fingerprints, timeout bootstrapping, and recurrent masks.
5. Are mediator decomposition and later route editing, fleet, save, menu, tutorial, settings, audio, maps, crossings, weekly progression, upgrades, balance, and policy-training increments ordered at boundaries small enough to implement and verify one by one?
6. Do later product systems share one canonical simulation and preserve manual, structured, recursive, save/replay, and pixel-control parity?
7. Flag process regressions, stale documentation assumptions, missing validation, hidden dependency changes, unsafe persistence, state duplication, resource loss, nondeterminism, and any increment that still needs finer substeps.

Known baseline: exact RL Python suite 316/316 with no skips; full Ruff/format pass; remote build/RL CI green; local Node tests fail only because live sibling civ-engine 2.4.1 differs from pinned 2.2.0; `Mediator` and its main test exceed 1,000 lines; current local RL artifacts are smoke/profile runs and do not prove competent play.
