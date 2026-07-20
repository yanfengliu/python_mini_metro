# AGENTS.md — python_mini_metro

## What this is

A Python 3.13 `pygame-ce` implementation of Mini Metro: optimize how many passengers your metro system delivers. Human and programmatic play are both supported; a Gymnasium player-equivalent pixel environment plus Stable-Baselines3 training/evaluation scripts (`scripts/train_rl.py`, `scripts/evaluate_rl.py`) make RL training a first-class purpose.

The recursive playtest loop runs on Node ≥ 20.6 against the built ignored `/.civ-engine-pin/` checkout described by `scripts/civ-engine-pin.json`; it never relies on or mutates `../civ-engine`. Keep workflow guidance rooted in the repo's existing Python commands and root-level documentation.

## Fleet constitution

- Work headlessly by default; go non-headless only when nothing else can complete or verify the task, and say why.
- These rules are strong defaults, not law: when one would make the work worse, deviate and say why.
- Scale the approach to the task: trivial changes directly; substantial work as explore → plan → implement → verify, with subagents when work is genuinely parallel.
- Delivery boundary: each minimal coherent verified unit is reviewed, staged (scoped files only), and committed promptly — never commit failing or partial work as a checkpoint. Commit to `main`; push at the end of every task.
- The repo's gates must pass before every commit that touches code; doc-only changes need a self-reviewed diff.
- Review: self-review trivial changes; adversarially review non-trivial ones — independent agents that try to refute the change against the live code. High-risk work (persistence/migrations, security/auth, concurrency, money, supply chain, edits that reach sibling repos) escalates to the multi-cli-review skill. Reviewers must read the live code; verify reviewer claims against the codebase before acting on them; substantive findings outweigh approval votes.
- Dependency changes: re-resolve the lockfile, run the repo's audit gate (a new HIGH/CRITICAL is a blocker), and note the audit result in the commit message.
- Docs are part of the change: update every affected surface in the same commit; write prose one line per paragraph (no hard wrapping); never reference or mandate files that don't exist.
- Bias to continue: work through the whole accepted plan without mid-plan check-ins; context management is the harness's job, never a reason to stop. Stop only for a genuine blocker, a direction-changing decision, or an explicit stop. (Established 2026-05-01; reinforced 2026-07-05.)
- Model pins live only in `../loop-ops/docs/skills/multi-cli-review.md` — never hardcode model IDs anywhere else.
- Lessons files (`docs/learning/lessons.md` where present) require evidence anchors — source, fix commit, test id, behavior delta; unanchored lessons are folklore.
- Recursive loop: before running or driving a pass, read `../loop-ops/docs/skills/recursive-playtest.md`; before building loop machinery, read `../loop-ops/docs/skills/building-recursive-loop.md`.

## Gates

- Every code or behavior change: full unit suite in `py313` — `python -m unittest -v`.
- Changed Python files: `python -m ruff check <files>`, `python -m ruff format --check <files>`, and `pre-commit run --files <files>` for hook parity.
- Full-repo `ruff check .`, `ruff format --check .`, and `pre-commit run --all-files` are required for lint/format cleanup tasks; if they fail on known baseline drift during unrelated work, report that honestly and keep changed files clean.
- Loop machinery: under the trusted canonical npm/Node bootstrap, `npm test` is the guarded fixed full `node --test` contract suite and accepts no forwarded package-script arguments; focused development runs use direct `node --test <files>`. The setup and guard mains require `NODE_OPTIONS` to be unset or empty and `process.execArgv` to be empty before their own effects. Each guard checks its setup-exclusive verification lease before and after verification and holds it through child completion, but the token lock remains advisory against out-of-band filesystem tampering while the child runs. CI (`.github/workflows/test.yml`) dogfoods isolated setup on Ubuntu and Windows, then runs those contracts, a clean recursive pass, `python -m unittest -v`, and the Windows RL smoke job — local validation is intentionally stricter on changed Python files.
- Dependency audit gate (any change to `requirements*.txt` or `environment.yml`): re-resolve the hash-pinned lockfile — `uv pip compile requirements.txt --python-version 3.13 --universal --generate-hashes --output-file requirements-locked.txt` (same pattern for `requirements-rl.txt`) — then run `pip-audit -r requirements-locked.txt --disable-pip`; a new CVE is a blocker; note the result in the commit message.

## Environment

- `conda activate py313`; install from `requirements-locked.txt` (RL extras: `requirements-rl-locked.txt`).
- Machine-local fallbacks when shell activation is not applied: use `C:\Users\38909\miniconda3\envs\py313\python.exe` directly, and `C:\Users\38909\miniconda3\Scripts\conda.exe` when `conda` is not on PATH. These paths are machine-specific — portable docs and scripts use `conda activate py313` plus `python ...`.
- Recursive loop: Node ≥ 20.6; `npm run setup:civ-engine` is the canonical cross-platform materialize/build/install/verify command for the ignored `/.civ-engine-pin/` checkout, and `node scripts/civ-engine-setup.mjs --verify-only` is the strict read-only check.
- Bootstrap boundary: the tracked `package.json` and `.npmrc`, selected top-level npm and Node executables, and their pre-start environment/configuration are trusted for canonical setup and guarded commands. The entry-point assertion detects non-empty `NODE_OPTIONS` or `process.execArgv` after module startup and refuses later effects, but Node can already have executed a preload, so no Node code can undo or attest caller-selected bootstrap overrides. Once setup starts cleanly, its Git/npm/build children still receive the scrubbed allowlisted environment; do not confuse that child isolation with sanitizing the already-started setup process.
- After clean startup, the setup command fails closed on unsafe or shadowed resolution, foreign or ownership-changed active setup artifacts, any non-generated pin byte that differs from `HEAD`, root install-graph or exact `.npmrc` drift, and substituted npm/TypeScript executables; npm runs only as the Node-distribution CLI through `process.execPath`, the build runs only the pin-local TypeScript CLI, and repair is limited to trusted ignored build/dependency drift plus the exact root dependency slot. `--verify-only --allow-dirty` is reserved for recursive execution, and the public command body selects it only when the shared recursive parser sees `--allow-dirty` in an option position rather than as a consumed value; tests and standalone verification stay strict.

## Session start

Read `ARCHITECTURE.md`, `PROGRESS.md`, and `README.md`; also `GAME_RULES.md` when touching game mechanics, progression, balancing, controls, rendering rules, station/passenger/metro behavior, or programmatic game actions. Check current validation status rather than assuming the baseline is clean.

## Invariants & boundaries

- TDD for behavior changes: tests first, testing the app-experience and mechanism contract, not implementation details.
- Locally high-risk (escalates to multi-cli-review): process/workflow docs (`AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`), public API changes in `src/env.py` or `src/mediator.py`, new architectural boundaries, and substantive game-mechanic or balance/config changes in `src/` (including `src/config.py`).
- Check `git status --short --branch` before editing; preserve unrelated user changes, including deleted files. Keep generated caches (`.pytest_cache`, `.ruff_cache`, `.coverage`, `__pycache__`) out of commits.
- Keep files small and focused (under 500 LOC, hard ceiling 1000) — split rather than grow god-objects.
- Visual changes: prefer deterministic surface-based tests or screenshots (`pygame.Surface`, `pygame.image.save`, pixel/array comparison); when impractical, run `python src/main.py` in `py313`, verify manually, and record what was checked.

## Known traps

- `pre-commit run --files ...` can modify files (the Ruff hook runs `--fix --exit-non-zero-on-fix`): treat it as part of the edit loop — inspect its edits, rerun the relevant checks, and never commit unreviewed hook edits.
- An interrupted civ-engine setup or guarded public Node command deliberately leaves its exact repository-root `/.civ-engine-setup.lock` when ownership-safe automatic release cannot complete; only setup can also leave `/.civ-engine-setup-<suffix>/` transactions or a marker-free partially published `/.civ-engine-pin/`. After proving no setup or guarded command is active, remove only individually inspected physical artifacts attributable to that run: the lock must be one regular JSON-token file, each transaction must be one physical directory with its own regular JSON-token `.setup-owner` and only physical descendants, and a partial pin must be preserved unless its matching transaction-side physical `.setup-promotion-claim` record, current destination `dev`/`ino`, token, and physical descendants are independently proven. A crash between final-directory creation and claim-record creation is deliberately unattributed and is never safe for this recovery procedure. Never pass wildcards to deletion or follow links.

## Conventions

- `PROGRESS.md` is the only project log (no changelog, no devlog): after substantive work, one short bullet under the latest `## YYYY-MM-DD` section, or a new dated section when the date changes; skip pure test-run notes and redundant bookkeeping.
- `README.md`: install/run instructions, manual controls, public programmatic API, user-facing behavior.
- `GAME_RULES.md`: game mechanics, progression, scoring, spawning, route behavior, controls, balance.
- `ARCHITECTURE.md`: file layout, new/removed modules, meaningful boundary or data-flow changes only — not test-only, wording-only, or narrow implementation changes.
- `docs/rl-model-selection.md` records the RL model-selection decision for the player-pixel task.
- Thread artifacts: `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/` holding `raw/` reviewer outputs (preserved verbatim), `diff.md`, and `REVIEW.md` (synthesis with severity, evidence, disposition); move or merge into `docs/threads/done/<theme>/` when complete — never replace an existing done theme wholesale — and check both trees before picking the next iteration number; full-codebase themes use `full`.
- Do not create or reference documentation trees that don't exist here unless the user explicitly asks to introduce one.
- `.claude/skills/multi-cli-review/SKILL.md` is this repo's stub (PowerShell-safe invocation forms); mechanics and pins live in the fleet runbook.
