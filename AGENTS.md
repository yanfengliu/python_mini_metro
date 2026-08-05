# AGENTS.md — python_mini_metro

## What this is

A Python 3.13 `pygame-ce` implementation of Mini Metro: optimize how many passengers your metro system delivers. Human and programmatic play are both supported; a Gymnasium player-equivalent pixel environment plus Stable-Baselines3 training/evaluation scripts (`scripts/train_rl.py`, `scripts/evaluate_rl.py`) make RL training a first-class purpose.

The recursive playtest loop runs on Node ≥ 20.6 against the built ignored `/.civ-engine-pin/` checkout described by `scripts/civ-engine-pin.json`; it never relies on or mutates `../civ-engine`. Keep workflow guidance rooted in the repo's existing Python commands and root-level documentation.

<!-- FLEET-CANON:BEGIN sha=2d7b45473798 generated from fleet/FLEET.md by `npm run sync-canon` — do not edit inside this block; this repo's own rules go in docs/policies/local-rules.md -->
## Fleet constitution

- Work headlessly by default. If only a browser or GUI can finish or verify the task, say why, and close what you opened.
- Concurrent sessions share one worktree and one index: commit by explicit pathspec (`git commit -- <files>`), never `git commit -a`, `git add -A`, or `git add .` — a sweeping commit captures whatever another session has staged. (voxel c024b33.)
- Commit early and often: the moment a minimal, coherent unit of change is verified, commit it to `main` without being asked, and push. Never batch several units into one commit, and never commit failing or partial work as a checkpoint. Gates pass before any commit that touches code; a dependency change re-runs the audit gate.
- Toolchain baseline is Node 24, pinned per repo in `.nvmrc`. A repo that must keep an older major says so in its Gates section and keeps a CI job proving it.
- Runtime model calls are authorized and already paid for — this fleet has one user, with Claude Code and Codex subscriptions — so a program here may call a model at runtime, vision included, wherever that beats a hand-written heuristic. Model output proposes; a deterministic check disposes.
- A fix is done when the failing case has been rerun and a regression test or fixture fails if the fix reverts. A diff is not evidence.
- High-risk work — persistence/migrations, security/auth, concurrency, money, supply chain, edits that reach sibling repos — escalates to the multi-cli-review skill.
- Error messages are a product surface: audit them as a class, including paths the task did not touch. Every path that rejects or throws names what happened, which input caused it, and what would satisfy it — never a bare `Validation failed`.
- Docs are part of the change: update every affected surface in the same commit, and write prose one line per paragraph (no hard wrapping).
- Task-run evidence — raw traces, per-sample results, screenshots, recordings, generated reports, archives — lives only under ignored paths and is deleted once nothing active needs it; never commit, push, or move it to LFS. Tracked docs keep conclusions and provenance only. Such output enters Git only when review promotes it into a genuine repository input — a fixture, golden, snapshot, or contract.
- Git blob ceilings: a new or changed blob over 256 KiB needs an explicit repository-input reason; over 512 KiB binary, or 1 MiB anything, never enters ordinary Git. An external asset store or LFS requires explicit user approval, and an existing oversized blob is never precedent for another.
- Steering compounds: when the user gives a direction that outlives the immediate task, land it that same session — `../fleet/FLEET.md` if fleet-wide, else this repo's `docs/policies/local-rules.md` — and say where it went.
- Citations are part of the deliverable: anything with a public answer — a numerical method, a library's behaviour, an engine parameter, a format, a protocol — carries the source it was read from, and so does any mechanism offered to explain a measured result. A dependency's source is one call away (`gh api repos/<owner>/<repo>/contents/<path>`).
- Reviewer model pins live only in `../fleet/docs/skills/multi-cli-review.md`; a model a product itself calls is pinned in the repo that calls it. Never hardcode a model ID anywhere else.
<!-- FLEET-CANON:END -->

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
- After clean startup, the setup command fails closed on unsafe or shadowed resolution, foreign or ownership-changed active setup artifacts, any non-generated pin byte that differs from `HEAD`, root install-graph or exact `.npmrc` drift, and substituted npm/TypeScript executables; npm runs only for the pin dependency graph as the Node-distribution CLI through `process.execPath`, the build runs only the pin-local TypeScript CLI, and root repair exclusively creates a missing exact symlink/junction after contract validation without invoking root npm or replacing a stale slot. `--verify-only --allow-dirty` is reserved for recursive execution, and the public command body selects it only when the shared recursive parser sees `--allow-dirty` in an option position rather than as a consumed value; tests and standalone verification stay strict.

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
- Thread artifacts: `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/` holding `raw/` reviewer outputs (preserved verbatim as a live audit window while the theme is in flight), `diff.md`, and `REVIEW.md` (synthesis with severity, evidence, disposition); when moving or merging into `docs/threads/done/<theme>/` on completion, **strip `raw/` — archived threads keep synthesis only** (`REVIEW.md`/`diff.md`), since raw has zero downstream reuse and the `REVIEW.md` is the cited record. Never replace an existing done theme wholesale, and check both trees before picking the next iteration number; full-codebase themes use `full`.
- Do not create or reference documentation trees that don't exist here unless the user explicitly asks to introduce one.
- Multi-CLI review mechanics and pins live in the fleet runbook `../fleet/docs/skills/multi-cli-review.md`. Local delta: reviews here are driven from PowerShell, where a multi-line prompt splits into unexpected arguments — pass the prompt as a single quoted string (or via a file) rather than relying on line continuation.
