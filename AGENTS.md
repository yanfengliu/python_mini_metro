## Core Rules

- This is a Python 3.13 `pygame-ce` project. Keep workflow guidance rooted in the repo's existing Python commands and root-level documentation.
- Use test-driven development for behavior changes: write or update tests first, then make them pass. Test the app experience and mechanism contract, not implementation details.
- Before implementing a substantive change, write a short plan and ask Codex and Claude to double-check it. Iterate until the feedback converges on approval or only minor wording remains. If one CLI is unavailable, continue with the available feedback and record the limitation in the review notes or final summary.
- Work directly on `main` unless the human explicitly asks for a branch. Commit only coherent, validated units, and only when the user asked for a commit or the current workflow clearly calls for one.
- Check `git status --short --branch` before editing. Preserve unrelated user changes, including deleted files.
- Split files when they grow unwieldy; prefer small, focused modules over one file doing too much.
- `CLAUDE.md` includes this file with `@AGENTS.md`; do not duplicate these instructions there.

## Environment

- Preferred interactive setup:
  - `conda activate py313`
  - `python -m pip install -r requirements.txt` if dependencies are missing
- Reliable Windows automation setup:
  - Use `C:\Users\38909\miniconda3\envs\py313\python.exe` directly when shell activation is not applied.
  - If `conda` is not on PATH, use `C:\Users\38909\miniconda3\Scripts\conda.exe`.
- The direct interpreter path is machine-specific. In portable docs or scripts, prefer `conda activate py313` plus `python ...`.

## Startup Context

- At session start for repo work, read:
  - `AGENTS.md`
  - `ARCHITECTURE.md`
  - `PROGRESS.md`
  - `README.md`
- Also read `GAME_RULES.md` when touching game mechanics, progression, balancing, controls, rendering rules, station/passenger/metro behavior, or programmatic game actions.
- Check current validation status rather than assuming the baseline is clean.

## Project Map

- `src/`: application code.
- `test/`: `unittest` test suite.
- `README.md`: installation, manual play, programmatic API, and testing entrypoint.
- `ARCHITECTURE.md`: current file structure and architectural boundaries.
- `GAME_RULES.md`: implementation-aligned game mechanics and controls.
- `PROGRESS.md`: single running project log.
- `reviews/`: multi-CLI review artifacts for substantive changes.

## Validation Gates

- For every code or behavior change, run the full unit suite in `py313`:
  - `python -m unittest -v`
  - Non-interactive equivalent: `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`
- For changed Python files, run changed-file lint and format checks:
  - `python -m ruff check <changed.py ...>`
  - `python -m ruff format --check <changed.py ...>`
- For hook parity on changed files, use:
  - `pre-commit run --files <changed files>`
- `pre-commit run --files ...` may modify files because the Ruff hook is configured with `--fix --exit-non-zero-on-fix`. Treat it as part of the edit loop: inspect the changes, rerun the relevant checks, and never commit unreviewed hook edits.
- Full-repo `ruff check .`, `ruff format --check .`, and `pre-commit run --all-files` are required for lint/formatting cleanup tasks. For unrelated tasks, if full-repo checks fail due to known baseline drift, report that honestly and keep changed files clean.
- Current CI runs `python -m unittest -v`; local validation is intentionally stricter when touching Python files.

## Documentation

- `PROGRESS.md` is the only project log. There is no separate changelog or devlog. After substantive completed work, append one short bullet under the latest `## YYYY-MM-DD` section, or start a new dated section when the date changes. Skip pure test-run notes and redundant bookkeeping.
- Update `README.md` for install/run instructions, manual controls, public programmatic API, or user-facing behavior.
- Update `GAME_RULES.md` for game mechanics, progression, scoring, spawning, route behavior, controls, or balance changes.
- Update `ARCHITECTURE.md` for file-layout changes, new modules, removed modules, or meaningful boundary/data-flow changes. Do not update it for test-only, wording-only, or narrow implementation changes that leave structure intact.
- Do not create or reference documentation trees that do not exist in this repo unless the user explicitly asks to introduce a new documentation system.

## Review Policy

- Multi-CLI review is required before declaring done for substantive behavior, public API, architecture, config, workflow, or process-doc changes.
- Review is required for changes to files such as `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs.
- Review is also required for game-mechanic changes in `src/`, public API changes in `src/env.py` or `src/mediator.py`, balance/config changes in `src/config.py`, and new architectural boundaries.
- Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
- Store review artifacts under `reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
  - `raw/codex.md`
  - `raw/opus.md`
  - optional `raw/*.stdout.log` and `raw/*.stderr.log`
  - `diff.md`
  - `REVIEW.md`
- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md reviews/README.md`.
- Reviewer prompt baseline:

```text
You are a senior code reviewer. Flag bugs, process regressions, stale documentation, missing validation, and maintainability risks. Do NOT modify files or propose patches. Only return findings, explanations, and suggestions in plain text. Only point out an issue if it is real and important. If there is no issue, say so instead of nit-picking.
```

- Enrich the prompt with task intent, files changed, validation performed, known baseline failures, and prior-review findings when iterating.
- If one CLI is unavailable because of quota, model rejection, or harness failure, proceed with the available reviewer and record the unavailable CLI in `REVIEW.md`.

## Visual Changes

- For visual changes, capture before/after evidence when feasible.
- Prefer deterministic surface-based tests or screenshots for pygame rendering when practical, using `pygame.Surface`, `pygame.image.save`, and a pixel or array comparison.
- If deterministic capture is not practical, run `python src/main.py` in `py313`, manually verify the visible behavior, and record what was checked.

## Debugging

- Reproduce failures before fixing them.
- Read the full error output, identify the root cause, and prefer the smallest change that solves the actual problem.
- If a fix fails, stop and re-evaluate the hypothesis rather than stacking unrelated changes.
- Clean up temporary logs, screenshots, and scratch files after the investigation unless they are intentionally committed as review or documentation artifacts.

## Git Hygiene

- Stage only the coherent unit of work.
- Never revert unrelated user changes.
- Before any commit, inspect `git diff --cached --stat` and `git diff --cached`.
- Keep generated caches such as `.pytest_cache`, `.ruff_cache`, `.coverage`, and `__pycache__` out of commits.
