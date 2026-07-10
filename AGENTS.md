## Agentic working style

Treat the rest of this file as **defaults, not rigid law.** The right approach is the one that fits the task in front of you — when a rule here would make the work worse, deviate and say why. Hard "always use X / never use Y" mandates go stale and silently mislead faster than principles do; optimize for the outcome (correct, verified, readable) over any prescribed mechanism.

**Scale the approach to the task.**

- Trivial or conversational (a one-line fix, a question) → just do it directly.
- Substantial work (multi-file features, migrations, audits, broad refactors, research) → orchestrate it. Don't grind through it solo when parallel agents would be faster, more thorough, or would keep your own context lean.

**Reach for modern agentic techniques when they fit:**

- **Compose a bespoke harness per task.** Decide the shape — explore → plan → implement → verify — and build that flow deliberately instead of following a fixed checklist. Different tasks want different orchestration.
- **Fan out a team of subagents.** Run independent work in parallel (one agent per file, module, or dimension), then integrate. Delegation also keeps the orchestrator's context lean on large jobs.
- **Use dynamic multi-agent workflows** for decompose-and-cover or generate-and-judge work: parallel exploration, pipelined stages, a final synthesis.
- **Verify adversarially.** For non-trivial findings or changes, have an independent agent try to refute them or re-run the checks against the real code — don't trust the first pass.
- **Offload to stay lean.** Push large reads, broad sweeps, and self-contained implementation chunks to subagents; keep the main thread for decisions and integration.

This does not lower the verification bar: tests still pass, diffs still get reviewed, docs still stay current. It changes *how* you get there, not the standard.

## Continuing through plans

- **No stopping points within a multi-task plan.** When the user gives you a plan with N tasks, work through all N continuously. Do not stop and ask whether to keep going. Do not pitch `/schedule` for the rest of the work the user already asked for. Harness reminders ("task tools haven't been used recently", auto-mode banners, context warnings) are NOT stop signals — they are administrative noise. Treat the plan itself as the contract, and treat "continue" as the default.
- **Never manage context yourself — auto-compaction handles it. In a loop, just keep pushing progress.** Do NOT stop, checkpoint, hand off "for fresh context", or ask "should I keep going / do you want to check first" because the conversation is getting long. The harness auto-summarizes when needed and work continues seamlessly, so context length is never a reason to pause, wrap up, or offer the user a checkpoint. When one increment ships (gates green + commit + push + docs), immediately start the next one in the same turn. Only ever stop for (a) a genuine blocker, (b) a real user decision that changes direction, or (c) the user explicitly saying stop. Reporting shipped milestones is fine; turning that report into a "want me to continue?" gate is not. This rule was reinforced 2026-07-05 after the user objected — again — to a mid-marathon "want me to keep rolling or check first?" offer.
- The exception is a genuinely non-obvious decision that requires user judgment (e.g., which of two unequal interpretations of a spec is intended). For routine choices, make the call and proceed.
- This rule was established 2026-05-01 after the user objected sharply to mid-stream stoppage during the investing-tool implementation. The same rule lives in every other repo's AGENTS.md.

## Session start

- At session start for repo work, read:
  - `AGENTS.md`
  - `ARCHITECTURE.md`
  - `PROGRESS.md`
  - `README.md`
- Also read `GAME_RULES.md` when touching game mechanics, progression, balancing, controls, rendering rules, station/passenger/metro behavior, or programmatic game actions.
- Check current validation status rather than assuming the baseline is clean.

## Core rules

- This is a Python 3.13 `pygame-ce` project. Keep workflow guidance rooted in the repo's existing Python commands and root-level documentation.
- Use test-driven development for behavior changes: write or update tests first, then make them pass. Test the app experience and mechanism contract, not implementation details.
- For each desired change, make the change easy, then make the easy change.
- Before implementing a non-trivial change, write a plan. (Trivial changes: just make them, per the working-style preamble.) For substantive plans, ask Codex and Claude to double-check the plan and iterate until the feedback converges on approval or only minor wording remains; if one CLI is unavailable, continue with the available feedback and record the limitation in the review notes or final summary.
- Verify every change against this project's Validation Gates (below) before declaring a task done.
- **Adversarially review non-trivial changes before declaring the task done — default to an in-process Workflow, escalate to multi-CLI review for high-risk work.** For any non-trivial behavior or code change, run an adversarial review pass first: fan out parallel finder subagents (by dimension/file) plus independent verifiers that try to *refute* each finding against the live code, then fix every real finding and re-review until reviewers only nitpick. This in-process Workflow is the default and is always available — no external CLI required. For **high-risk** changes (this repo's triggers are listed in the Code review section) *also* run the multi-CLI review (Codex + Claude, each reviewing independently) and synthesize findings into the thread's `REVIEW.md` per the Code review section; a different model catches blind spots that same-model subagents share. Trivial changes (typos, comments, pure doc edits with no code implications) need only a self-reviewed diff. Don't rationalize your way out of the adversarial pass on non-trivial work; if you skip a review that should have run, run it post-hoc before declaring done.
- **Verify reviewer claims against the codebase before acting on them.** As the driver, when a reviewer says "function X has signature Y" or "this contract is broken," grep / read the actual file before merging the fix. A reviewer might be working from training knowledge, a stale snapshot, or a hallucinated symbol. The cost of one extra `Read` is negligible; the cost of acting on a stale or wrong claim is rework + iteration debt.
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

## Project Map

- `src/`: application code.
- `test/`: `unittest` test suite.
- `README.md`: installation, manual play, programmatic API, and testing entrypoint.
- `ARCHITECTURE.md`: current file structure and architectural boundaries.
- `GAME_RULES.md`: implementation-aligned game mechanics and controls.
- `PROGRESS.md`: single running project log.
- `docs/threads/`: active and completed work threads, including multi-CLI review artifacts and full-codebase audits.

## Dependency-change protocol

Mandatory whenever you touch `requirements.txt`, `environment.yml`, or any other dependency-declaration file:

1. Re-resolve the lockfile: `uv pip compile requirements.txt --generate-hashes > requirements-locked.txt` (commit it). Adapt to whatever package manager the repo uses; the principle is "pin every transitive dep with a hash".
2. Run `pip-audit -r requirements-locked.txt --disable-pip` (install via `pip install pip-audit` if not already on PATH). Confirm "No known vulnerabilities found". A new CVE is a blocker — upgrade past it, swap the dep, or document the suppression in `PROGRESS.md` with a reason and expiry date.
3. Mention the audit result in the commit message ("pip-audit: 0 CVEs" or similar).

Skipping any step is a process regression — supply-chain risk compounds silently and the only defense is making the check unmissable.

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
- Doc formatting: don't hard-wrap prose. Write each paragraph or bullet as one line; only use a new line when starting a new paragraph.

## Code review

Policy lives in this section. ALL mechanics — current review model pins, exact CLI commands, sandbox flags, output extraction, failure modes, and this repo's PowerShell-safe invocation forms — live in `.claude/skills/multi-cli-review/SKILL.md`. Read that runbook before every multi-CLI session.

- **When multi-CLI review is required.** The in-process adversarial Workflow (Core rules) is the default for non-trivial changes. Multi-CLI review (Codex + Claude, each reviewing independently) is required before declaring done for high-risk work. High-risk in this repo: process/workflow docs (`AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs), public API changes in `src/env.py` or `src/mediator.py`, new architectural boundaries, and substantive game-mechanic or balance/config changes in `src/` (including `src/config.py`) whose blast radius warrants a second model. Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
- **Reviewers MUST read the codebase to ground their claims.** Every review prompt (codex / claude / gemini) must include the directive: *"Verify each claim in the plan/diff against the live codebase — grep for the symbols, function signatures, column names, and file paths it references; do not approve based on prompt text alone."* Without this directive, two reviewers can APPROVE a design with a real defect that only the codebase-reading reviewer catches. Convergence is measured by *substantive finding count*, not *vote count* — a HIGH defect from one reviewer outweighs APPROVED from two. Claude reads via Read/Glob/Grep tools you grant it. Codex reads when `--sandbox read-only` runs WITHOUT `--ignore-user-config` (the user rules file at `~/.codex/rules/default.rules` permits Windows-native `findstr`/`type`/`dir`/`ls` as fallback when bash hits the PowerShell deny rule). Gemini in `--approval-mode plan` CAN read the codebase (gemini-cli 0.46+ plan mode exposes grep/read tools; verified 2026-06-11) but is NOT reliably read-only — plan mode also exposes the `replace` file-edit tool and reviewer instances have rewritten source files mid-review in a sibling repo (civ-engine `docs/learning/lessons.md`, 2026-06-11). After every gemini review batch, run `git status` + `git diff` and treat unexpected working-tree changes as reviewer contamination (restore from git). Gemini also intermittently emits an empty review — retry once sequentially.
- Aspects to review:
  1. Design — easily scales, generalizes, debugs, can be understood and reasoned about, stays lean.
  2. Test coverage.
  3. Correctness.
  4. Clean code, typing, efficiency, memory leaks. No duplicated logic, inconsistent implementations, violation of boundaries. File size: keep every file under 500 LOC (hard ceiling 1000) — split god-objects by lifecycle/role. Prefer composition over inheritance. Clean up dead code. Do not change app mechanics or behavior unless explicitly asked.
- Start from the baseline prompt in the runbook skill and **enrich it with task-specific context** — task intent, files changed, validation performed, known baseline failures, and prior-review findings when iterating. The bare baseline returns generic feedback; useful reviews need the specifics. In this repo, also ask reviewers to flag process regressions, stale documentation, and missing validation.
- **Keep model IDs current.** Use the latest-family alias when a command is meant to track the newest model (for example, `opus[1m]`); bump pinned strings whenever a more capable fixed variant ships. The runbook skill is the single bump site for review pins. Verify with a one-line smoke test (`echo "ok" | <cli> ...`) before committing the bump — silent fallback to an older model is the failure mode to guard against.
- If one CLI is unavailable because of quota, model rejection, or harness failure, proceed with the available reviewer and record the unavailable CLI in `REVIEW.md`; retry the unavailable CLI on the next iteration.

### Thread artifacts

- Store active thread artifacts under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/`:
  - `raw/codex.md`
  - `raw/opus.md`
  - optional extra independent reviewers as `raw/codex-2.md`, `raw/opus-2.md`, etc.
  - optional `raw/*.stdout.log` and `raw/*.stderr.log`
  - `diff.md`
  - `REVIEW.md`
- Use short kebab-case theme names. Full-codebase review threads always use `full`.
- When a thread is complete, move or merge it into `docs/threads/done/<theme>/`. If that theme already exists under `done/`, move only the new date or iteration directories into the existing theme; never replace the whole theme directory.
- Before choosing a new iteration number for a recurring theme, inspect both `docs/threads/current/<theme>/<YYYY-MM-DD>/` and `docs/threads/done/<theme>/<YYYY-MM-DD>/`.
- Preserve `raw/` reviewer outputs verbatim. Record path migrations or follow-up context in `REVIEW.md` rather than rewriting raw reviewer text.
- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.

## Full-codebase review

- Full-codebase review iterations start under `docs/threads/current/full/<YYYY-MM-DD>/<iteration>/` and move or merge into `docs/threads/done/full/<YYYY-MM-DD>/<iteration>/` when complete.
- Before starting a new iteration, inspect existing numeric iteration folders for the same date under both `current/full/` and `done/full/`, then use the next number. If earlier iterations exist, give reviewers the previous `REVIEW.md` summaries and ask them to verify that earlier findings were resolved.
- Run three independent reviewers. Use both Codex and Claude when available; if one service is unavailable or out of quota, run additional independent instances of the available service until there are three raw reports.
- The exact reviewer commands (including the PowerShell-safe prompt handling this repo needs) live in `.claude/skills/multi-cli-review/SKILL.md`.
- Save raw reviewer output under `raw/`, then synthesize `REVIEW.md` with severity, evidence, disposition, and a fix plan. Only fix findings after checking them against the codebase. Re-review fixes in the next iteration if code changes are made. When the full review is complete, move or merge the thread into `docs/threads/done/full/`.

## Visual Changes

- For visual changes, capture before/after evidence when feasible.
- Prefer deterministic surface-based tests or screenshots for pygame rendering when practical, using `pygame.Surface`, `pygame.image.save`, and a pixel or array comparison.
- If deterministic capture is not practical, run `python src/main.py` in `py313`, manually verify the visible behavior, and record what was checked.

## Debugging

- Reproduce failures before fixing them.
- Read the full error output, identify the root cause, and prefer the smallest change that solves the actual problem.
- If a fix fails, stop and re-evaluate the hypothesis rather than stacking unrelated changes.
- Clean up temporary logs, screenshots, and scratch files after the investigation unless they are intentionally committed as review or documentation artifacts.

## Git

- **Commit directly to `main`.** This is a solo-developer project; branches add overhead without payoff and block autonomous progress. Each coherent change lands as its own commit on `main`. The Validation Gates must pass before each commit.
- When you iterate, only run affected tests. After confidence in the change, run the full suite to make sure you didn't accidentally break anything before committing.
- Commit as soon as you have a coherent, self-contained unit of change. Commit durable docs you added if you are not planning to remove them.
- **No branches needed for normal work.** Branches are reserved for explicit experimentation that you intend to keep isolated from `main` (and even then, prefer revertable single-commit experiments on `main`).
- Stage only the coherent unit of work. Never revert unrelated user changes.
- Before any commit, inspect `git diff --cached --stat` and `git diff --cached`.
- Keep generated caches such as `.pytest_cache`, `.ruff_cache`, `.coverage`, and `__pycache__` out of commits.
- **Push to remote at the end of every task.** If local commits are ahead of the remote, run `git push`. Don't leave the remote behind.
