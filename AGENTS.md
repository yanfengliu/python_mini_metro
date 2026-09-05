# AGENTS.md — python_mini_metro

## What this is

A Python 3.13 `pygame-ce` implementation of Mini Metro: optimize how many passengers your metro system delivers. Human and programmatic play are both supported; a Gymnasium player-equivalent pixel environment plus Stable-Baselines3 training/evaluation scripts (`scripts/train_rl.py`, `scripts/evaluate_rl.py`) make RL training a first-class purpose.

The recursive playtest loop runs on Node ≥ 20.6 against the built ignored `/.civ-engine-pin/` checkout described by `scripts/civ-engine-pin.json`; it never relies on or mutates `../civ-engine`. Keep workflow guidance rooted in the repo's existing Python commands and root-level documentation.

<!-- FLEET-CANON:BEGIN sha=181e6b6bfe78 generated from ../fleet/FLEET.md by `npm run sync-canon` — do not edit inside this block; this repo's own rules go in docs/policies/local-rules.md -->
## Fleet constitution

### Fleet Orchestration Policy

Deliver the requested outcome with verified correctness, coherent architecture, and minimal necessary complexity. Optimize for useful progress—not agent count, code volume, or maximum reasoning. Adapt rigor to risk. This policy grants no additional permissions or capabilities.

#### Roles

Only an explicitly designated agent acts as coordinator. Use one accountable integration owner per scope. The coordinator owns planning, dependencies, shared interfaces, architectural consistency, integration, and acceptance. It may implement small changes directly.

Workers own bounded outcomes and local implementation decisions. They may use subagents within their scope and budget, but remain accountable. Organize threads around deliverables, not permanent departments. Avoid recursive manager hierarchies.

#### Plan and delegate

Inspect applicable instructions, relevant code/docs, working-tree state, and active tasks before changing anything. Establish the outcome, non-goals, acceptance criteria, dependencies, and verification method. Resolve routine ambiguity through evidence and reversible defaults.

Choose the simplest effective workflow: direct execution for localized work, subagents for bounded investigation or independent judgment, and separate threads/worktrees for substantial independent changes. Agree on shared contracts before parallel implementation. Avoid duplicate or blocked work.

Each assignment must identify its owner, outcome, relevant context, dependencies/contracts, base revision, workspace, allowed/excluded changes, verification, resource limits, and expected handoff. Specify read-only versus implementation work. Respect configured model/reasoning defaults; change them only through supported controls when evidence justifies it.

#### Coordinate safely

Use only capabilities actually available. Never assume visibility into other chats, shared memory, automatic messaging, workspace isolation, or persistent monitoring. Distinguish prepared assignments from dispatched work and observed status from assumptions. When coordination is unavailable, work directly or provide an explicit handoff.

Isolate concurrent edits with worktrees or equivalent mechanisms; otherwise serialize overlapping writes. Account for shared services, databases, ports, and compute limits. Never overwrite or discard another participant's work. Track delegated work through completion, cancellation, or handoff, and release only resources you own without losing work.

#### Preserve state and decision boundaries

Keep essential memory in the repository or existing tracker, not conversation history. Reuse conventions and maintain only useful documentation. Record owners, dependencies, revisions, status, blockers, and consequential decisions. The coordinator owns canonical status; workers supply scoped updates. Explicitly propagate changed contracts and revalidate stale information.

Distinguish intended requirements from actual behavior. Preserve evidence, unresolved issues, and next steps at handoff or interruption. Exclude secrets and unnecessary private data.

Workers act autonomously within scope. Escalate cross-task interfaces, persistent formats, security boundaries, major dependencies, and scope changes. The coordinator resolves these within the approved mandate. Unapproved major architecture/product changes and consequential external actions require human authorization. Continue safe independent work while blocked.

#### Implement and verify

Inspect, implement a coherent increment, run relevant checks, diagnose, fix, and recheck. Preserve established architecture; avoid unrelated rewrites, speculative abstractions, and unnecessary dependencies. Proceed beyond planning when implementation is requested.

Use task-appropriate evidence and establish baselines when needed. Inspect actual user flows for interactive products. For games/simulations, check relevant invariants, save compatibility, and realistic-scale performance. Prototype uncertain ideas before generalizing. For research, cite evidence and distinguish hypotheses, measurements, and conclusions.

Obtain independent, preferably read-only review for substantial or high-risk changes when available. Review the exact revision against acceptance criteria. Evaluate findings, fix justified issues, and rerun affected checks. Never weaken tests or conceal failures to claim success.

#### Integrate, report, and stop

Workers hand off outcomes, changes/revisions, checks and results, risks, blockers, and integration requirements. The integration owner inspects actual changes, integrates in dependency order, and verifies the combined result. Worker success alone does not establish integration success. Respect merge, push, deployment, and publication permissions.

After two failures for the same reason, reassess rather than repeat. Unless another budget is specified, cap automatic repair at five substantive attempts, then report evidence, blockers, and next steps.

Keep updates brief and decision-relevant. Clearly distinguish implemented, verified, reviewed, integrated, and blocked work. Stop when acceptance criteria and material findings are resolved; do not invent follow-up work. Report partial completion and unavailable verification honestly.

#### Final acceptance gate

The integration owner is accountable for final acceptance. Before reporting completion:

- Check every acceptance criterion against the final integrated revision, using actual changes and verification evidence—not worker summaries alone.
- Run relevant automated checks and exercise affected end-to-end behavior. Check cross-task interactions, not just each task in isolation.
- For substantial or high-risk work, obtain an independent read-only review of the integrated changes, including integration fixes. If unavailable, explicitly report the missing review rather than implying it occurred.
- Resolve material findings, rerun affected checks, and obtain focused re-review where fixes invalidate earlier review.
- Report the verified revision, checks and results, review status, and any failed, skipped, or unavailable checks. Mark unmet criteria as incomplete.

Do not declare the result fully verified while material findings or required checks remain unresolved. Respect the repair budget and report blockers.

### Fleet conventions

- Repository rules add concrete local constraints consistent with the Fleet Orchestration Policy; they do not override its permissions, adaptive workflow, or stopping limits.
- Verify visual work visually: capture the rendered result — screenshot, frame, recording — and look at it, because a passing test says nothing about what the pixels do. Work with no visual surface runs headlessly. For 3D work, one framing is not a check: sweep several camera angles and zoom levels, since a defect the chosen view happens to hide is the normal case. For 2D interfaces and artwork, inspect relevant viewport sizes, scales, and states. For games and other interactive visual deliverables, exercise real controls and representative user flows, and inspect how the rendered result responds over time. For static scenes and assets, inspect applicable viewpoints, using orbit, pan, or zoom in a viewer when available and useful. Use headless interaction and rendering when they provide adequate evidence; use a visible session only when necessary to verify behavior. An aggregate view — a contact sheet, grid, montage, or proof sheet — answers "is there one of each" and never "is each one right", and answers the first just as confidently when the second answer is no: inspect each item at the artifact's own native resolution, and bind the review to the digest of the bytes inspected, so regenerating the artifact strands its review instead of inheriting it. Badge's 63-source contact sheet read as cohesive while ten sources were wrong, and the lesson recurred four days after it was written down, against 48px proof sheets. For visual tasks, inspect the affected user flows and the surrounding rendered result for material regressions; choose the coverage from the change's risk and acceptance criteria.
- A defect the user reports is recorded and gated, never only fixed: an entry in `docs/learning/defect-register.md` — symptom as they saw it, investigation, root cause, and how it is checked from now on — plus a check that covers the defect's whole class rather than the one instance. Unlike a lesson, the entry stays after it becomes a gate: the register is the standing list of what the gates could not see, which is where the next defect comes from.
- Gates pass before any commit that touches code; a dependency change re-runs the audit gate. Commit, merge, push, deploy, and publish only within the user's authorization.
- For an authorized push, inspect the remote gate through completion when available. Read job steps and runner assignment before treating a failed run as a code failure: exhausted Actions allowance can fail before any job starts. Report unavailable remote verification and use the local gate as evidence within its bounds. Resolve failures that block the requested outcome within the repair budget; report unrelated failures without silently expanding scope.
- A repo chooses its own language and toolchain — Node, Python, and Rust all run here. Each pins its version where its own tooling reads it (`.nvmrc`, `requires-python`, `rust-toolchain.toml`) and names it in Gates, so a version mismatch is not read as a code failure. Node repos baseline at 24; an older major keeps a CI job proving it.
- Runtime model calls are authorized and already paid for — this fleet has one user, with Claude Code and Codex subscriptions — so a program here may call a model at runtime, vision included.
- Use `../fleet/docs/skills/hard-problem.md` to search across different approaches after repeated failure, within the orchestration policy's attempt and resource limits.
- For substantial or high-risk changes, use independent review when available. High-risk areas include persistence/migrations, security/auth, concurrency, money, supply chain, and edits that reach sibling repos; `../fleet/docs/skills/multi-cli-review.md` provides the review mechanics.
- Error messages are a product surface: check the affected class and relevant adjacent paths. Each names what happened, which input caused it, and what would satisfy it — never a bare `Validation failed`.
- When blocked, hand over the relevant artifact — screenshot, rendered page, log line, data row — with secrets and unnecessary private data removed, as soon as the blocker is named rather than after the analysis: your description of it is filtered through the misunderstanding that caused the block, so it cannot contain what you failed to notice.
- Task-run evidence lives only under ignored paths and is deleted once no active task, unresolved issue, or handoff needs it; it enters Git only when review promotes it into a repository input — a fixture, golden, snapshot, or contract. Tracked docs keep conclusions and provenance only. Blob ceilings for anything promoted: over 256 KiB needs a stated reason, over 512 KiB binary or 1 MiB of anything never enters ordinary Git, and an asset store or LFS needs the user's approval.
- Use the common word where it says the same thing as the rare one. This covers chat, docs, commit subjects and PR titles, comments, and error messages. One idea per sentence, unless another rule asks one line to carry more. Cut length, not facts: keep exact terms, numbers, and the evidence a claim rests on. It applies to sentences you write, not to text you quote or paste. Do not copy this canon's style.
- Write prose one line per paragraph (no hard wrapping).
- Keep a devlog: one short dated line per behaviour-changing session in `docs/devlog/summary.md`, newest first, and a section in `docs/devlog/detailed/` for anything a later session could trip over — what was believed and proved false, what a reviewer caught that the author missed, what number moved and from what. It is history, not status. Both shapes are in `../fleet/docs/devlog-template.md`.
- A lesson is prose only until it is a gate. It lands the session it is learned in `docs/learning/lessons.md` — read at session start — anchored to a measurement, commit, or test id, and naming the gate that will retire it: a test, a lint rule, a schema check, a fixed command. That file is a queue: an entry is deleted in the commit landing its gate, and a gate counts only once it has been made to go red by reintroducing the defect. Deleting the prose is safe only because the deletion is recoverable, so the gate carries the claim in its own header and `docs/learning/gate-proofs.md` carries the mutation, the failure it produced, and the pre-retirement commit that `git show <sha>:docs/learning/lessons-evidence.md` reads the whole evidence file back out of. A gate and the claim in its header can be wrong together and look exactly like a gate that is right, and auditing one means reaching what was believed, measured and abandoned at the time — never the sentence the gate carries about itself. An entry that can name no gate is not a lesson — fleet-wide knowledge is staged in `canon-candidates.md` for this constitution, repo-only knowledge goes to `docs/policies/local-rules.md`, and the rest is folklore and is dropped. An index that only grows is a list of things that failed to graduate: aoe2's reached 84 entries, none naming a gate. An index already holding ungated entries is emptied entry by entry as each one's area is next touched, not kept as a standing exception. Shape: `../fleet/docs/lessons-template.md`.
- A green gate proves less than it looks like. Every gate is bounded by something — a seed set, a tick window, a resolution, a fixture that ends early, an include list, a shared flag any one case can satisfy — and proves nothing past that bound, so name the bound in the gate's own header and pin every input that reproduces the defect, not just the one you thought of. Past its bound a gate does not merely miss the defect — it can measure a different phenomenon entirely and report it just as confidently: aoe2's stone-mining window opened at tick 11,000 on a fixture that resolves by conquest at 11,442, so it was reading a decided match, and a finished match and a deadlocked one are pixel-identical. A gate that cannot tell "passed" from "did not run" reports the second as the first, and a check built from the same symbol as the thing it checks proves only that the code agrees with itself. Retiring 356 lessons across 14 repos found **more than 40 whose evidence named a live, passing test that did not catch the defect** — every repo's `docs/learning/gate-proofs.md` records its own: an 800-decision rollout window hid a divergence that starts at 3,000, a Rust-side struct pin stayed green while the WGSL side it mirrors gained a field, and `replaceFootprintOwner(…, undefined)` passed all 873 tests.
- A command's exit status is a claim about the command, not about the work: a pipeline exits with its last stage's status, so `npm run x | tail` reports tail's success over any failure; `git add` fails all-or-nothing while the `commit` after it still succeeds and ships a message that lies about its contents; and a tool reporting that it applied a fix reports a no-op identically to a refusal — read the artifact it should have changed. Red deserves the same suspicion as green: a non-zero exit is equally a claim about the command, and a missing dev dependency, an unresolvable binary or a wrong working directory fails identically to a broken product — aoe2's `playtest:corpus` went red on a merge because `tsx` was gone from `node_modules`, not because the code was wrong. A blocker you inherited is the same kind of claim: retest it before repeating it, because its whole effect is to stop work. A RETURN VALUE is a claim of the same kind: a search that cannot match hands back a sentinel the next call uses without complaint, and an `indexOf` miss fed to `slice` deleted 319 lines of a tracked spec in one edit.
- Verify the instrument before trusting the measurement, because a critic is a backstop and not the first line. Confirm the flag took effect, the denominator is the population you meant, the control reproduces, and the claim you are relying on is still true rather than remembered. A whole session's conclusions were built on labels chosen with knowledge of the future, agreement quoted over a population that was 99.8% forced no-ops, a `--eval-episodes` flag silently ignored so every checkpoint was picked by a five-sample lottery, and a review lane declared unavailable from a three-week-old memory that was wrong. Each was one command away from being caught. An A/B comparison asks one more thing: that the tree HOLD STILL. Edits landing between the two arms make them differ by more than the variable under test, and the result reads as a finding — aoe2 read a boot-map regression off two arms it had edited between. A repo that ships a debugging instrument — a session replayer, a recorder and bundle differ, a capture script, a profiler, a debug probe — is asked FIRST, and the task's first probe names which of them answers the question or why none does. aoe2 skipped its engine's replay harness twice with the rule in prose (2026-06-13, 2026-09-05), the second time with a memory stating the rule loaded in the same session; what held was a hook that refuses to write or run a scratch probe without a `harness:` line naming the tool. A rule that must be remembered at the moment of writing a probe is enforced at that moment, not read at session start.

- A standing loop sources its next task by running the artifact the way its user does — the default entry point, the real configuration — never by reading code for something to improve. A repo with no runnable entry point has no standing loop.
- This harness compacts context mid-task: a compaction is a harness event, not a task boundary, and never a reason to wrap up or hand off to a fresh session.

- Before resuming interrupted work, inspect surviving worktrees, artifacts, and task status. Recover what exists and preserve unfinished work; do not assume that a worktree, transcript, or shared memory survived.

- Steering compounds: a direction that outlives the immediate task lands that same session — `../fleet/FLEET.md` if fleet-wide, else this repo's `docs/policies/local-rules.md` — and you say where it went.
- Reviewer model pins live only in `../fleet/docs/skills/multi-cli-review.md`; a model a product itself calls is pinned in the repo that calls it. Never hardcode a model ID anywhere else.
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
- Thread artifacts: `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/` holding `raw/` reviewer outputs (preserved verbatim as a live audit window while the theme is in flight), `diff.md`, and `REVIEW.md` (synthesis with severity, evidence, disposition); when moving or merging into `docs/threads/done/<theme>/` on completion, **strip `raw/` — archived threads keep synthesis only** (`REVIEW.md`/`diff.md`), since raw has zero downstream reuse and the `REVIEW.md` is the cited record. Never replace an existing done theme wholesale, and check both trees before picking the next iteration number; full-codebase themes use `full`.
- Do not create or reference documentation trees that don't exist here unless the user explicitly asks to introduce one.
- Multi-CLI review mechanics and pins live in the fleet runbook `../fleet/docs/skills/multi-cli-review.md`. Local delta: reviews here are driven from PowerShell, where a multi-line prompt splits into unexpected arguments — pass the prompt as a single quoted string (or via a file) rather than relying on line continuation.
