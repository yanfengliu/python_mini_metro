# AGENTS.md — python_mini_metro

## What this is

A Python 3.13 `pygame-ce` implementation of Mini Metro: optimize how many passengers your metro system delivers. Human and programmatic play are both supported; a Gymnasium player-equivalent pixel environment plus Stable-Baselines3 training/evaluation scripts (`scripts/train_rl.py`, `scripts/evaluate_rl.py`) make RL training a first-class purpose.

The recursive playtest loop runs on Node ≥ 20.6 against the built ignored `/.civ-engine-pin/` checkout described by `scripts/civ-engine-pin.json`; it never relies on or mutates `../civ-engine`. Keep workflow guidance rooted in the repo's existing Python commands and root-level documentation.

This repo's own rules live in [docs/policies/local-rules.md](docs/policies/local-rules.md). They add repository constraints consistent with the fleet constitution below.

<!-- FLEET-CANON:BEGIN sha=fa6416c07600 generated from ../fleet/FLEET.md by `npm run sync-canon` — do not edit inside this block; this repo's own rules go in docs/policies/local-rules.md -->
## Fleet constitution

Shared rules for every repo under `github/`, kept in `../fleet/FLEET.md`; `../fleet/` is fleet's checkout beside this repo's primary checkout. Where a rule gives its reason, use the reason to judge cases the rule does not name; each `[Rn]`'s history is in `../fleet/docs/canon-rationale.md`. This repo's `docs/policies/local-rules.md` may add rules but cannot change these permissions or limits. [R13]

The main agent owns delivery and may implement directly. Use subagents when bounded, independent work or independent judgment materially improves speed or quality; keep small or tightly coupled work with one agent (owner directive, 2026-11-07). [R2, R3]

The designated coordinator reads `../fleet/docs/skills/coordinator.md` before planning and after each compaction, and any agent reads that file's "Delegate" section before delegating. Before these kinds of work, read the matching section of `../fleet/docs/work-rules.md`: standing loops and unattended runs; editing skills, agent instructions or rules; handing off or stopping mid-task.

### Permissions

- Commit, merge to main and push without asking. Force-pushing and rewriting history (they destroy history), and deploying and publishing (they reach other people), need the owner's OK. [R14]
- Ask before a major architecture or product change, a new major dependency, a change to a persistent format or a security boundary, or any other consequential action outside this machine, such as posting or sending something. [R8]
- Change fleet rules (FLEET.md, fleet skills and runbooks, agent memory) or add a rule to a repo's `docs/policies/local-rules.md` only when the owner asks, because the owner sets policy. You may add a proposal with its evidence to `../fleet/canon-candidates.md`, but not edit its entries. [R8]

### Sharing the machine

- Other Claude and Codex sessions may be working in this checkout, and you cannot see them. Do anything beyond a quick read in your own worktree, because two sessions in one tree spoil each other's gates and commits. Never revert, overwrite or delete changes you did not make. When resuming, check which worktrees, branches and files already exist. [R7]
- Done means merged to main and pushed: the owner archives sessions, and work left on a branch is lost. Merge on your branch, get the gates passing there, then move main, because other worktrees build on local main. Judge the merged result itself, not a worker's summary. Then remove your worktree and branch, and report where any unmerged work is. [R14]

### Doing the work

- The repo's gates must pass on the tree that is handed back or reaches main. Unless the repo's own rules ask more of a commit, commit on your own branch at every stopping point and say in the message what was not checked, because a session can end without warning. Docs-only changes need content checks and any gate the repo names for docs, not runtime tests or CI waits. [R14]
- Check the thing that should have changed (the file, the page, the number), not just the exit code or a tool's report: both can pass over a defect. Retest a blocker you inherit before repeating it. Never weaken a test or hide a failure to get green. [R9]
- Look at visual and interactive work rendered at full resolution, through the real controls, from fixed and random views, because passing tests say nothing about pixels. Run it headless unless a visible window is needed. [R16]
- Slowness on the critical path, such as a gate rendering on the CPU of a machine with a GPU, is a defect to fix. [R22]
- After pushing code, follow CI to the end; read a failed job's steps before blaming the code, since a billing limit fails jobs before any step runs. [R15]
- If a fix fails twice for one reason, rethink it. After five real repair attempts at one problem, whatever the approach and counting earlier sessions, stop and report, unless the owner set another limit; for a problem that keeps winning, run the search in `../fleet/docs/skills/hard-problem.md`. Stop when the task's criteria are met; do not invent follow-up work. [R11]
- For substantial or high-risk changes, use independent review when available. High-risk includes persistence and migrations, security and auth, concurrency, money, supply chain, and code changes in another repo. Review the exact revision against the task's criteria, and say so when review was unavailable. Fix the findings that matter and have those fixes checked; note minor ones instead of starting another round. `../fleet/docs/skills/multi-cli-review.md` provides the review mechanics. [R10]
- A defect the owner reports gets a test for its whole class and an entry in `docs/learning/defect-register.md`, because a fix without a check tends to come back. [R17]
- Sessions run long: take new requests in the same session, and never hand off to a new session to shed context. Split work expected to need more than about 200k tokens of context into milestones, each merged to main. [R6]

### Records, sized to the work

- Read `docs/learning/lessons.md` at session start; it lists this repo's known traps, and its header says how to add one. [R18]
- Every change that alters behaviour adds a dated line to `docs/devlog/summary.md` (`../fleet/docs/devlog-template.md`) when it lands, because later sessions orient from its newest entries. Work that spans sessions, has several agents writing, or gets an independent review also keeps its plan and review records in `docs/work/` (`../fleet/docs/work-docs.md`); other work needs none. [R24]
- Raw output (logs, captures, screenshots) stays in ignored folders. Never commit a binary over 512 KiB or any file over 1 MiB; LFS needs the owner's OK. [R23]

### Style and environment

- Plain words; one line per paragraph, no hard wrapping. A report says what changed, how it was checked (including any check skipped or failed) and what is not done. [R25]
- Node 24 is the baseline. Products pin the model IDs they call in their own repo, and nowhere else. Reviewer model pins live only in `../fleet/docs/skills/multi-cli-review.md`. Runtime model calls are allowed and paid for; make per-item calls one-shot, not agent sessions. [R28, R29]
<!-- FLEET-CANON:END -->

## Gates

- Python is pinned to 3.13 by `environment.yml` (`python=3.13`, conda env `py313`) — the env the Python gates below run in. Three places carry their own copy of that number and are bumped with it: `pyproject.toml` (ruff `target-version`), CI (`.github/workflows/test.yml`), and the lockfile re-resolution (`uv pip compile --python-version 3.13`).
- Every code or behavior change: full unit suite in `py313` — `python -m unittest -v`.
- Any change under `test/`, `scripts/` or `src/`: also run `python scripts/run_without_rl_extras.py -m unittest`. It hides the RL extras, which a development machine has and CI's `build` job does not, so a test that reaches for torch, Stable-Baselines3, sb3-contrib, tensorboard or Pillow without skipping is caught here instead of in CI. It hides those five roots and nothing else, so it says nothing about any other difference between a laptop and a runner. A test that skips itself in `build` must be named in the `rl-smoke` module list, or it runs nowhere.
- Changed Python files: `python -m ruff check <files>` and `python -m ruff format --check <files>`.
- Close each validated unit of change by writing the formatting in before you commit: `python -m ruff format <files>` then `python -m ruff check --fix <files>`. If either edits a file, re-run the unit suite — a formatting pass is a code change. No commit hook catches this any more, so an unformatted commit is the author's to prevent.
- Full-repo `ruff check .` and `ruff format --check .` are required for lint/format cleanup tasks; if they fail on known baseline drift during unrelated work, report that honestly and keep changed files clean.
- Loop machinery: under the trusted canonical npm/Node bootstrap, `npm test` is the guarded fixed full `node --test` contract suite and accepts no forwarded package-script arguments; focused development runs use direct `node --test <files>`. The setup and guard mains require `NODE_OPTIONS` to be unset or empty and `process.execArgv` to be empty before their own effects. Each guard checks its setup-exclusive verification lease before and after verification and holds it through child completion, but the token lock remains advisory against out-of-band filesystem tampering while the child runs. CI (`.github/workflows/test.yml`) dogfoods isolated setup on Ubuntu and Windows, then runs those contracts, a clean recursive pass, `python -m unittest -v`, and the Windows RL smoke job — local validation is intentionally stricter on changed Python files.
- Dependency audit gate (any change to `requirements*.txt` or `environment.yml`): re-resolve the hash-pinned lockfile — `uv pip compile requirements.txt --python-version 3.13 --universal --generate-hashes --output-file requirements-locked.txt` (same pattern for `requirements-rl.txt`) — then run `pip-audit -r requirements-locked.txt --disable-pip`; a new CVE is a blocker; note the result in the commit message.

## Environment

- `conda activate py313`; install from `requirements-locked.txt` (RL extras: `requirements-rl-locked.txt`).
- Machine-local fallbacks when shell activation is not applied: use `C:\Users\38909\miniconda3\envs\py313\python.exe` directly, and `C:\Users\38909\miniconda3\Scripts\conda.exe` when `conda` is not on PATH. These paths are machine-specific — portable docs and scripts use `conda activate py313` plus `python ...`.
- Recursive loop: Node ≥ 20.6; `npm run setup:civ-engine` is the canonical cross-platform materialize/build/install/verify command for the ignored `/.civ-engine-pin/` checkout, and `node scripts/civ-engine-setup.mjs --verify-only` is the strict read-only check.
- Bootstrap boundary: the tracked `package.json` and `.npmrc`, selected top-level npm and Node executables, and their pre-start environment/configuration are trusted for canonical setup and guarded commands. The entry-point assertion detects non-empty `NODE_OPTIONS` or `process.execArgv` after module startup and refuses later effects, but Node can already have executed a preload, so no Node code can undo or attest caller-selected bootstrap overrides. Once setup starts cleanly, its Git/npm/build children still receive the scrubbed allowlisted environment; do not confuse that child isolation with sanitizing the already-started setup process.
- After clean startup, the setup command fails closed on unsafe or shadowed resolution, foreign or ownership-changed active setup artifacts, any non-generated pin byte that differs from `HEAD`, root install-graph or exact `.npmrc` drift, and substituted npm/TypeScript executables; npm runs only for the pin dependency graph as the Node-distribution CLI through `process.execPath`, the build runs only the pin-local TypeScript CLI, and root repair exclusively creates a missing exact symlink/junction after contract validation without invoking root npm or replacing a stale slot. `--verify-only --allow-dirty` is reserved for recursive execution, and the public command body selects it only when the shared recursive parser sees `--allow-dirty` in an option position rather than as a consumed value; tests and standalone verification stay strict.

## Session start

Read `ARCHITECTURE.md` and `README.md`; also `GAME_RULES.md` when touching game mechanics, progression, balancing, controls, rendering rules, station/passenger/metro behavior, or programmatic game actions. Check current validation status rather than assuming the baseline is clean.

## Invariants & boundaries

- TDD for behavior changes: tests first, testing the app-experience and mechanism contract, not implementation details.
- Locally high-risk (escalates to multi-cli-review): process/workflow docs (`AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `pyproject.toml`, `environment.yml`), public API changes in `src/env.py` or `src/mediator.py`, new architectural boundaries, and substantive game-mechanic or balance/config changes in `src/` (including `src/config.py`).
- Check `git status --short --branch` before editing; preserve unrelated user changes, including deleted files. Keep generated caches (`.pytest_cache`, `.ruff_cache`, `.coverage`, `__pycache__`) out of commits.
- Keep files small and focused (under 500 LOC, hard ceiling 1000) — split rather than grow god-objects.
- Visual changes: prefer deterministic surface-based tests or screenshots (`pygame.Surface`, `pygame.image.save`, pixel/array comparison); when impractical, run `python src/main.py` in `py313`, verify manually, and record what was checked.

## Conventions

- The canon devlog is this repo's only log — there is no changelog. Entries go under the latest `## YYYY-MM-DD` section of `docs/devlog/summary.md`, or a new dated section when the date changes; skip pure test-run notes and redundant bookkeeping. Historical note: entries written before 2026-08-07 are detailed-grade paragraphs sitting in the summary, from when this file was `PROGRESS.md` and predated the canon split; new work writes a short line here and puts the detail in `docs/devlog/detailed/`.
- `README.md`: install/run instructions, manual controls, public programmatic API, user-facing behavior.
- `GAME_RULES.md`: game mechanics, progression, scoring, spawning, route behavior, controls, balance.
- `ARCHITECTURE.md`: file layout, new/removed modules, meaningful boundary or data-flow changes only — not test-only, wording-only, or narrow implementation changes.
- `docs/rl-model-selection.md` records the RL model-selection decision for the player-pixel task.
- Do not create or reference documentation trees that don't exist here unless the user explicitly asks to introduce one.
- Multi-CLI review mechanics and pins live in the fleet runbook `../fleet/docs/skills/multi-cli-review.md`. Local delta: reviews here are driven from PowerShell, where a multi-line prompt splits into unexpected arguments — pass the prompt as a single quoted string (or via a file) rather than relying on line continuation.
