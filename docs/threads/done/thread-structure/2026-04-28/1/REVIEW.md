# Thread Structure Review - 2026-04-28 Iteration 1

## Scope

Rename the work artifact system from review-only folders to the broader thread lifecycle:

- active work under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/`
- completed work under `docs/threads/done/<theme>/<YYYY-MM-DD>/<iteration>/`
- completed full-codebase review work under the `full` theme

## Plan Check

- Codex reviewed the implementation plan and flagged three process risks: recurring theme collisions when moving `current` into `done`, preserving raw evidence, and making the lifecycle apply to more than review-only artifacts.
- Claude was unavailable due quota exhaustion.

Disposition: accepted. The implemented guidance defines merge semantics for recurring themes, documents the broader thread lifecycle, preserves raw reviewer output verbatim, and keeps completed `full` history under `docs/threads/done/full`.

## Reviewers

- Codex: `raw/codex.md`
- Claude Opus: unavailable due quota exhaustion; raw quota output is saved in `raw/opus.md`

## Findings

### Medium - Raw reviewer artifacts were rewritten

Codex found that the initial path sweep rewrote existing `raw/` reviewer outputs, which made at least one historical finding self-contradictory.

Disposition: accepted and fixed. Existing `docs/threads/done/**/raw/*.md` files were restored from the committed pre-migration raw artifacts, and `AGENTS.md` plus `docs/threads/README.md` now explicitly require preserving raw reviewer output verbatim.

## Validation

- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files <changed-files>` passed after end-of-file hooks normalized new thread artifacts.
- `git diff --check` passed.
- Folder checks passed: `docs/threads/current`, `docs/threads/done`, `docs/threads/done/full`, and `docs/threads/done/agents-repo-fit` exist; the old review-artifact directories do not exist.
- A live-doc scan excluding raw reviewer evidence and diff artifacts found 0 references to the outdated review folder paths.
- `git diff --name-status -- docs/threads/done/**/raw/*.md` showed no content changes to restored historical raw reviewer outputs.
