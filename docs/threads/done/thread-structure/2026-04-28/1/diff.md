diff --git a/AGENTS.md b/AGENTS.md
index 05556a3..f240669 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -36,7 +36,7 @@
 - `ARCHITECTURE.md`: current file structure and architectural boundaries.
 - `GAME_RULES.md`: implementation-aligned game mechanics and controls.
 - `PROGRESS.md`: single running project log.
-- `docs/reviews/`: multi-CLI review artifacts for substantive changes and full-codebase audits.
+- `docs/threads/`: active and completed work threads, including multi-CLI review artifacts and full-codebase audits.

 ## Validation Gates

@@ -66,14 +66,17 @@
 - Review is required for changes to files such as `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs.
 - Review is also required for game-mechanic changes in `src/`, public API changes in `src/env.py` or `src/mediator.py`, balance/config changes in `src/config.py`, and new architectural boundaries.
 - Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
-- Store review artifacts under `docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
+- Store active thread artifacts under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/`:
   - `raw/codex.md`
   - `raw/opus.md`
   - optional extra independent reviewers as `raw/codex-2.md`, `raw/opus-2.md`, etc.
   - optional `raw/*.stdout.log` and `raw/*.stderr.log`
   - `diff.md`
   - `REVIEW.md`
-- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/reviews/README.md`.
+- Use short kebab-case theme names. Full-codebase review threads always use `full`.
+- When a thread is complete, move or merge it into `docs/threads/done/<theme>/`. If that theme already exists under `done/`, move only the new date or iteration directories into the existing theme; never replace the whole theme directory.
+- Before choosing a new iteration number for a recurring theme, inspect both `docs/threads/current/<theme>/<YYYY-MM-DD>/` and `docs/threads/done/<theme>/<YYYY-MM-DD>/`.
+- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
 - Reviewer prompt baseline:

 ```text
@@ -85,23 +88,23 @@ You are a senior code reviewer. Flag bugs, process regressions, stale documentat

 ## Full-Codebase Review

-- Full-codebase review iterations live under `docs/reviews/full/<YYYY-MM-DD>/<iteration>/`.
-- Before starting a new iteration, inspect existing numeric iteration folders for the same date and use the next number. If earlier iterations exist, give reviewers the previous `REVIEW.md` summaries and ask them to verify that earlier findings were resolved.
+- Full-codebase review iterations start under `docs/threads/current/full/<YYYY-MM-DD>/<iteration>/` and move or merge into `docs/threads/done/full/<YYYY-MM-DD>/<iteration>/` when complete.
+- Before starting a new iteration, inspect existing numeric iteration folders for the same date under both `current/full/` and `done/full/`, then use the next number. If earlier iterations exist, give reviewers the previous `REVIEW.md` summaries and ask them to verify that earlier findings were resolved.
 - Run three independent reviewers. Use both Codex and Claude when available; if one service is unavailable or out of quota, run additional independent instances of the available service until there are three raw reports.
 - Codex full-codebase reviewer command. Keep the prompt in a file and pipe it through stdin; this avoids PowerShell splitting multi-line prompts into unexpected positional arguments. Use `--ignore-user-config` so local plugin sync or user config does not interfere with a read-only review run:

 ```powershell
-Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/reviews/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
+Get-Content -Raw docs/threads/current/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/threads/current/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
 ```

 - Claude full-codebase reviewer command. Keep the prompt in a variable so PowerShell passes it as one argument:

 ```powershell
-$prompt = Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
+$prompt = Get-Content -Raw docs/threads/current/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
 claude -p $prompt --model best --effort max --permission-mode bypassPermissions --no-session-persistence --tools "Read,Glob,Grep,Bash" --allowedTools "Read,Glob,Grep,Bash(git *),Bash(python -m unittest *),Bash(C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest *)" --output-format text
 ```

-- Save raw reviewer output under `raw/`, then synthesize `REVIEW.md` with severity, evidence, disposition, and a fix plan. Only fix findings after checking them against the codebase. Re-review fixes in the next iteration if code changes are made.
+- Save raw reviewer output under `raw/`, then synthesize `REVIEW.md` with severity, evidence, disposition, and a fix plan. Only fix findings after checking them against the codebase. Re-review fixes in the next iteration if code changes are made. When the full review is complete, move or merge the thread into `docs/threads/done/full/`.

 ## Visual Changes

diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index 1a196c5..c90c9b3 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -5,10 +5,14 @@ python_mini_metro/
 |- .vscode/
 |  \- settings.json
 |- docs/
-|  \- reviews/
+|  \- threads/
 |     |- README.md
-|     |- agents-repo-fit/
-|     \- full/
+|     |- current/
+|     |  \- README.md
+|     \- done/
+|        |- README.md
+|        |- agents-repo-fit/
+|        \- full/
 |- src/
 |  |- agent_play.py
 |  |- config.py
diff --git a/PROGRESS.md b/PROGRESS.md
index 484a2fd..79586e4 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -81,5 +81,6 @@
 ## 2026-04-28

 - Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added an initial review artifact directory.
-- Moved review artifacts under `docs/reviews/` and documented robust full-codebase Codex/Claude review commands.
+- Moved review artifacts under the docs thread area and documented robust full-codebase Codex/Claude review commands.
 - Ran the first full-codebase review, fixed terminal-state API mutation, malformed action handling, loop routing closure, stale travel-plan cleanup, the graph node hash contract, and the stale Ruff pre-commit hook, then added focused regressions.
+- Renamed review artifacts into the broader `docs/threads/` lifecycle, with active work in `current/`, completed work in `done/`, and completed `full` and `agents-repo-fit` themes migrated under `done/`.
diff --git a/docs/threads/README.md b/docs/threads/README.md
index 531bdd2..00bed86 100644
--- a/docs/threads/README.md
+++ b/docs/threads/README.md
@@ -1,11 +1,15 @@
-# Reviews
+# Threads

-This directory stores multi-CLI review artifacts for substantive behavior, API, architecture, config, workflow, process-documentation changes, and full-codebase audits.
+This directory stores work threads. A thread is the durable record for one coherent piece of work, named by theme.

-Use this layout:
+Threads start under `current/` while work is active and move to `done/` when the work is complete. If a completed theme already exists under `done/`, merge the new date or iteration directories into that theme instead of replacing the whole theme directory.
+
+Use short kebab-case theme names, such as `agents-repo-fit`, `thread-structure`, or `metro-dwell-fix`. Full-codebase review work always uses the theme name `full`.
+
+Use this layout for thread artifacts:

 ```text
-docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/
+docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/
 |- raw/
 |  |- codex-1.md
 |  |- opus.md
@@ -14,4 +18,10 @@ docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/
 \- REVIEW.md
 ```

-Keep review scope names short and kebab-case, such as `agents-repo-fit`, `full`, or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
+When the thread is complete, move or merge that date/iteration tree to:
+
+```text
+docs/threads/done/<theme>/<YYYY-MM-DD>/<iteration>/
+```
+
+Start iteration numbering at `1` and increment it only when a re-review or revised artifact set is needed after addressing findings. For recurring themes, inspect both `current/<theme>/` and `done/<theme>/` before choosing the next date or iteration number.
diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
index 3ede47b..aa34e91 100644
--- a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
+++ b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
@@ -3,15 +3,15 @@
 ## Scope

 - Rewrote `AGENTS.md` from a copied workflow template into a Python/py313 workflow for this repo.
-- Added `docs/reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
-- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/reviews/`.
+- Added `docs/threads/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
+- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/threads/done/`.
 - Updated `PROGRESS.md` with a short entry for the process-documentation change.

 ## Validation

 - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`: passed, 167 tests.
-- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1/diff.md docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
-- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
+- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
+- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.

 ## Codex Findings

@@ -21,7 +21,7 @@
 ## Claude Findings

 - P2: `PROGRESS.md` and the review artifact path use `2026-04-28`, while the reviewer inferred April 27, 2026 from local session context. Disposition: not accepted for the same reason as the Codex date finding.
-- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/reviews/`.
+- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/threads/done/`.
 - P3: The review packet should include the `.cursor/rules` deletion and `CLAUDE.md` addition. Disposition: accepted. `diff.md` was regenerated with those paths included.

 ## Result
diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
index a79988d..40afce7 100644
--- a/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
+++ b/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
@@ -104,7 +104,7 @@ index 0000000..bf60f17
 +- `ARCHITECTURE.md`: current file structure and architectural boundaries.
 +- `GAME_RULES.md`: implementation-aligned game mechanics and controls.
 +- `PROGRESS.md`: single running project log.
-+- `reviews/`: multi-CLI review artifacts for substantive changes.
++- `docs/threads/done/`: multi-CLI review artifacts for substantive changes.
 +
 +## Validation Gates
 +
@@ -134,13 +134,13 @@ index 0000000..bf60f17
 +- Review is required for changes to files such as `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs.
 +- Review is also required for game-mechanic changes in `src/`, public API changes in `src/env.py` or `src/mediator.py`, balance/config changes in `src/config.py`, and new architectural boundaries.
 +- Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
-+- Store review artifacts under `reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
++- Store review artifacts under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/`:
 +  - `raw/codex.md`
 +  - `raw/opus.md`
 +  - optional `raw/*.stdout.log` and `raw/*.stderr.log`
 +  - `diff.md`
 +  - `REVIEW.md`
-+- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md reviews/README.md`.
++- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
 +- Reviewer prompt baseline:
 +
 +```text
@@ -186,7 +186,7 @@ index e678939..a6b66ef 100644
  |     \- test.yml
 +|- .vscode/
 +|  \- settings.json
-+|- reviews/
++|- docs/threads/done/
 +|  \- README.md
  |- src/
  |  |- agent_play.py
@@ -219,12 +219,12 @@ index d858993..b3879b3 100644
 +
 +## 2026-04-28
 +
-+- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `reviews/` artifact directory.
-diff --git a/reviews/README.md b/reviews/README.md
++- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `docs/threads/done/` artifact directory.
+diff --git a/docs/threads/README.md b/docs/threads/README.md
 new file mode 100644
 index 0000000..d5d2eef
 --- /dev/null
-+++ b/reviews/README.md
++++ b/docs/threads/README.md
 @@ -0,0 +1,16 @@
 +# Reviews
 +
@@ -233,7 +233,7 @@ index 0000000..d5d2eef
 +Use this layout:
 +
 +```text
-+reviews/<scope>/<YYYY-MM-DD>/<iteration>/
++docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/
 +|- raw/
 +|  |- codex.md
 +|  \- opus.md
diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
index 4bb76c0..19c399c 100644
--- a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
+++ b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
@@ -5,21 +5,21 @@ I verified the diff against the live repo. Here are my findings.
 ### Real issues

 **1. PROGRESS.md date is one day ahead of the current date.**
-The new section is dated `## 2026-04-28`, but the system clock for this session shows `2026-04-27` (and filesystem timestamps for `reviews/` are also `Apr 27`). AGENTS.md says "start a new dated section when the date changes," which means the date in the bullet should be today's date. If the user is logging from a UTC+8 timezone where it's already crossed midnight, that's a defensible choice, but it's worth confirming on purpose rather than letting the future-dated entry silently land. The same date is also baked into the on-disk `reviews/agents-repo-fit/2026-04-28/` directory, so if you change one you must change the other to keep them aligned.
+The new section is dated `## 2026-04-28`, but the system clock for this session shows `2026-04-27` (and filesystem timestamps for `docs/threads/done/` are also `Apr 27`). AGENTS.md says "start a new dated section when the date changes," which means the date in the bullet should be today's date. If the user is logging from a UTC+8 timezone where it's already crossed midnight, that's a defensible choice, but it's worth confirming on purpose rather than letting the future-dated entry silently land. The same date is also baked into the on-disk `docs/threads/done/agents-repo-fit/2026-04-28/` directory, so if you change one you must change the other to keep them aligned.

 **2. PROGRESS.md bullet is incomplete relative to the actual process change.**
-The bullet reads: *"Replaced the copied agent instructions with Python/py313 workflow guidance and added a `reviews/` artifact directory."* The change set is broader than that:
+The bullet reads: *"Replaced the copied agent instructions with Python/py313 workflow guidance and added a `docs/threads/done/` artifact directory."* The change set is broader than that:
 - `.cursor/rules/*.mdc` were removed (the source of "the copied agent instructions").
 - `CLAUDE.md` was added as a one-line `@AGENTS.md` shim.
 - `ARCHITECTURE.md` was updated.

-"The copied agent instructions" is opaque to anyone reading PROGRESS.md later — it doesn't make clear what was deleted (`.cursor/rules`) or that `CLAUDE.md` was added. A future reader running `git blame`/`git log` will recover the truth, but the project log itself is the only sanctioned changelog per AGENTS.md, so it should at least name the moved/added files. One tighter bullet, e.g. "Replaced `.cursor/rules/*.mdc` with `AGENTS.md` (+ `CLAUDE.md` shim) and added a `reviews/` artifact directory," would be both short and accurate.
+"The copied agent instructions" is opaque to anyone reading PROGRESS.md later — it doesn't make clear what was deleted (`.cursor/rules`) or that `CLAUDE.md` was added. A future reader running `git blame`/`git log` will recover the truth, but the project log itself is the only sanctioned changelog per AGENTS.md, so it should at least name the moved/added files. One tighter bullet, e.g. "Replaced `.cursor/rules/*.mdc` with `AGENTS.md` (+ `CLAUDE.md` shim) and added a `docs/threads/done/` artifact directory," would be both short and accurate.

 ### Things I checked and confirmed are fine

 - `requirements.txt` exists at repo root, so the `pip install -r requirements.txt` line in AGENTS.md is not stale (despite ARCHITECTURE.md previously listing only `environment.yml`; the new diff still doesn't list `requirements.txt` separately, but the existing root listing in ARCHITECTURE.md already includes `requirements.txt` further down — verified at `ARCHITECTURE.md:78`).
 - `.vscode/settings.json` exists, so the new ARCHITECTURE.md entry for `.vscode/` is accurate.
-- `reviews/README.md` matches the directory layout AGENTS.md prescribes (`raw/codex.md`, `raw/opus.md`, `diff.md`, `REVIEW.md`).
+- `docs/threads/README.md` matches the directory layout AGENTS.md prescribes (`raw/codex.md`, `raw/opus.md`, `diff.md`, `REVIEW.md`).
 - `CLAUDE.md` is a single `@AGENTS.md` line, matching AGENTS.md's "do not duplicate these instructions there" rule.
 - The Reviewer prompt baseline in AGENTS.md matches the prompt I was actually invoked with.
 - The `.cursor/rules/*.mdc` paths are correctly removed from ARCHITECTURE.md and not re-introduced anywhere.
@@ -27,8 +27,8 @@ The bullet reads: *"Replaced the copied agent instructions with Python/py313 wor

 ### Meta-observation about the review packet

-The diff handed to this reviewer omits two parts of the actual change set: the deletion of `.cursor/rules/*.mdc` and the addition of `CLAUDE.md`. They are visible in `git status` but not in the textual diff. For a process-doc review, a `git diff -- .cursor/ AGENTS.md CLAUDE.md ARCHITECTURE.md PROGRESS.md reviews/` style path-limited diff (which AGENTS.md itself recommends) would give the next reviewer a complete picture. Not a defect of the documentation change, but worth noting for the iteration's `diff.md`.
+The diff handed to this reviewer omits two parts of the actual change set: the deletion of `.cursor/rules/*.mdc` and the addition of `CLAUDE.md`. They are visible in `git status` but not in the textual diff. For a process-doc review, a `git diff -- .cursor/ AGENTS.md CLAUDE.md ARCHITECTURE.md PROGRESS.md docs/threads/done/` style path-limited diff (which AGENTS.md itself recommends) would give the next reviewer a complete picture. Not a defect of the documentation change, but worth noting for the iteration's `diff.md`.

 ## Bottom line

-The change is structurally sound: AGENTS.md is internally consistent, the new `reviews/` layout matches what AGENTS.md prescribes, and ARCHITECTURE.md is in sync with the live tree. The two concrete issues are the future-dated PROGRESS.md section and the under-described PROGRESS.md bullet. Both are easy fixes and neither blocks the intent of the change.
+The change is structurally sound: AGENTS.md is internally consistent, the new `docs/threads/done/` layout matches what AGENTS.md prescribes, and ARCHITECTURE.md is in sync with the live tree. The two concrete issues are the future-dated PROGRESS.md section and the under-described PROGRESS.md bullet. Both are easy fixes and neither blocks the intent of the change.
diff --git a/docs/threads/done/full/2026-04-28/1/REVIEW.md b/docs/threads/done/full/2026-04-28/1/REVIEW.md
index 0160cb6..693d96f 100644
--- a/docs/threads/done/full/2026-04-28/1/REVIEW.md
+++ b/docs/threads/done/full/2026-04-28/1/REVIEW.md
@@ -38,10 +38,10 @@
 - Evidence: `Node.__eq__` compares by station, while `Node.__hash__` hashes the node id. Nodes are stored in sets, so equal nodes must have equal hashes.
 - Disposition: accepted. Hash by the same station identity used for equality and cover set behavior.

-### Low: moved historical review artifact still mentions old `reviews/` path
+### Low: moved historical review artifact still mentions old `docs/threads/done/` path

 - Reported by: Codex 2.
-- Evidence: `docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `reviews/README.md` and validating `reviews/...` paths after the artifact was moved under `docs/reviews/`.
+- Evidence: `docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `docs/threads/README.md` and validating `docs/threads/done/...` paths after the artifact was moved under `docs/threads/done/`.
 - Disposition: accepted. Update the moved artifact so it remains accurate after the docs-path change.

 ### Low: two tests mutate `sys.path` after project imports
diff --git a/docs/threads/done/full/2026-04-28/1/diff.md b/docs/threads/done/full/2026-04-28/1/diff.md
index cbb222c..e45d712 100644
--- a/docs/threads/done/full/2026-04-28/1/diff.md
+++ b/docs/threads/done/full/2026-04-28/1/diff.md
@@ -1,5 +1,5 @@
 # Full-Codebase Review Diff Context

-This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `reviews/` to `docs/reviews/`.
+This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `docs/threads/done/` to `docs/threads/done/`.

 The active findings are synthesized in `REVIEW.md`; raw reviewer outputs are preserved in `raw/`.
diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
index a565f8a..6f831e9 100644
--- a/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
+++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
@@ -8,7 +8,7 @@ Extra attention areas:
 - Programmatic environment/API behavior in `src/env.py`, `src/mediator.py`, and `src/agent_play.py`.
 - Routing/boarding/game-over edge cases.
 - Test gaps where behavior is documented but not protected.
-- Review-process and docs-path consistency after the move to `docs/reviews/`.
+- Review-process and docs-path consistency after the move to `docs/threads/done/`.

 Constraints:
 - Do not modify files.
diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
index 8886b41..554ce1a 100644
--- a/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
+++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
@@ -8,7 +8,7 @@ Extra attention areas:
 - Domain logic in `src/graph/`, `src/line.py`, `src/metro.py`, and `src/station.py`.
 - Resource/path lifecycle cleanup when lines, trains, passengers, or travel plans are removed.
 - Python equality/hash contracts, mutable shared state, and any edge cases likely to corrupt routing.
-- Review-process and docs-path consistency after the move to `docs/reviews/`.
+- Review-process and docs-path consistency after the move to `docs/threads/done/`.

 Constraints:
 - Do not modify files.
diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-1.md b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
index d4c9407..6f10cb6 100644
--- a/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
+++ b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
@@ -12,7 +12,7 @@
 4. Medium - [src/graph/graph_algo.py](C:/Users/38909/Documents/github/python_mini_metro/src/graph/graph_algo.py:17):17-35, [src/entity/path.py](C:/Users/38909/Documents/github/python_mini_metro/src/entity/path.py:51):51-57
    Routing ignores the closing edge of looped lines. `Path` creates a last-to-first segment for loops, but `build_station_nodes_dict()` only connects adjacent stations in `path.stations`, so passengers cannot route across the loop closure. Direction: when `path.is_looped`, add neighbors between the last and first nodes and cover it with a BFS/travel-plan test.

-5. Low - [docs/reviews/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
+5. Low - [docs/threads/done/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
    The current full-review artifact directory is incomplete: it has prompts/logs, `raw/opus.md` contains only a quota message, and there is no `diff.md` or `REVIEW.md`. Direction: before committing those artifacts, either complete the iteration with valid reports and synthesis, or leave these transient failed-run files out of the change set.

 No issue found in the dependency/config basics I checked: `requirements.txt`, `environment.yml`, and CI are aligned on the project's current runtime dependencies.
diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-2.md b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
index 8078f32..8cba8cc 100644
--- a/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
+++ b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
@@ -9,12 +9,12 @@
 3. **Medium** - [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:449>)
    `remove_path()` removes passengers riding that line from `self.passengers` but leaves their entries in `self.travel_plans`. Repeated create/remove cycles can accumulate stale passenger references and make debugging/routing state misleading. Direction: delete travel-plan entries for every passenger removed with a metro, matching the cleanup already done on delivery.

-4. **Low** - [docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
-   The moved review artifact still describes and validates the old `reviews/` path at lines 6-14, while current process docs now require `docs/reviews/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
+4. **Low** - [docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
+   The moved review artifact still describes and validates the old `docs/threads/done/` path at lines 6-14, while current process docs now require `docs/threads/done/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.

 5. **Low** - [test/test_graph.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_graph.py:6>), [test/test_mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_mediator.py:6>)
    These modules import from `src` before appending `../src` to `sys.path`, so they depend on another test having already mutated `sys.path`. Direction: move the path setup before project imports, or package/import the project consistently.

 **Notes**

-I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/reviews/README.md` mostly consistent with the `docs/reviews/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
+I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/threads/README.md` mostly consistent with the `docs/threads/done/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-3.md b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
index 48c47ea..8c1764b 100644
--- a/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
+++ b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
@@ -20,8 +20,8 @@
    `Node.__eq__` compares by station, but `Node.__hash__` hashes a unique node id. Equal nodes can therefore have different hashes, which breaks Python's set/dict contract. This is risky because nodes are stored in sets (`neighbors`, `paths`) and tests compare fresh `Node(station)` instances as equal.
    Suggested direction: hash by `station` if equality is station-based, or make equality identity/id-based consistently.

-6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/reviews/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/README.md:8>)
-   `docs/reviews/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
+6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/threads/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/README.md:8>)
+   `docs/threads/done/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
    Suggested direction: complete the iteration before committing, or keep failed/transient run artifacts out of the change set.

 Tests were not run: the harness rejected `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`, `python -m unittest -v`, and the bytecode-disabled variant.
diff --git a/docs/threads/done/full/2026-04-28/2/diff.md b/docs/threads/done/full/2026-04-28/2/diff.md
index 1e9dbd3..f848190 100644
--- a/docs/threads/done/full/2026-04-28/2/diff.md
+++ b/docs/threads/done/full/2026-04-28/2/diff.md
@@ -1,4 +1,4 @@
-﻿diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
+diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
 index 9407181..a6514f4 100644
 --- a/.pre-commit-config.yaml
 +++ b/.pre-commit-config.yaml
@@ -19,8 +19,8 @@ index bf60f17..05556a3 100644
  - `ARCHITECTURE.md`: current file structure and architectural boundaries.
  - `GAME_RULES.md`: implementation-aligned game mechanics and controls.
  - `PROGRESS.md`: single running project log.
--- `reviews/`: multi-CLI review artifacts for substantive changes.
-+- `docs/reviews/`: multi-CLI review artifacts for substantive changes and full-codebase audits.
+-- `docs/threads/done/`: multi-CLI review artifacts for substantive changes.
++- `docs/threads/done/`: multi-CLI review artifacts for substantive changes and full-codebase audits.

  ## Validation Gates

@@ -28,16 +28,16 @@ index bf60f17..05556a3 100644
  - Review is required for changes to files such as `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs.
  - Review is also required for game-mechanic changes in `src/`, public API changes in `src/env.py` or `src/mediator.py`, balance/config changes in `src/config.py`, and new architectural boundaries.
  - Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
--- Store review artifacts under `reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
-+- Store review artifacts under `docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
+-- Store review artifacts under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/`:
++- Store review artifacts under `docs/threads/done/<scope>/<YYYY-MM-DD>/<iteration>/`:
    - `raw/codex.md`
    - `raw/opus.md`
 +  - optional extra independent reviewers as `raw/codex-2.md`, `raw/opus-2.md`, etc.
    - optional `raw/*.stdout.log` and `raw/*.stderr.log`
    - `diff.md`
    - `REVIEW.md`
--- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md reviews/README.md`.
-+- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/reviews/README.md`.
+-- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
++- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
  - Reviewer prompt baseline:

  ```text
@@ -47,19 +47,19 @@ index bf60f17..05556a3 100644

 +## Full-Codebase Review
 +
-+- Full-codebase review iterations live under `docs/reviews/full/<YYYY-MM-DD>/<iteration>/`.
++- Full-codebase review iterations live under `docs/threads/done/full/<YYYY-MM-DD>/<iteration>/`.
 +- Before starting a new iteration, inspect existing numeric iteration folders for the same date and use the next number. If earlier iterations exist, give reviewers the previous `REVIEW.md` summaries and ask them to verify that earlier findings were resolved.
 +- Run three independent reviewers. Use both Codex and Claude when available; if one service is unavailable or out of quota, run additional independent instances of the available service until there are three raw reports.
 +- Codex full-codebase reviewer command. Keep the prompt in a file and pipe it through stdin; this avoids PowerShell splitting multi-line prompts into unexpected positional arguments. Use `--ignore-user-config` so local plugin sync or user config does not interfere with a read-only review run:
 +
 +```powershell
-+Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/reviews/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
++Get-Content -Raw docs/threads/done/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/threads/done/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
 +```
 +
 +- Claude full-codebase reviewer command. Keep the prompt in a variable so PowerShell passes it as one argument:
 +
 +```powershell
-+$prompt = Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
++$prompt = Get-Content -Raw docs/threads/done/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
 +claude -p $prompt --model best --effort max --permission-mode bypassPermissions --no-session-persistence --tools "Read,Glob,Grep,Bash" --allowedTools "Read,Glob,Grep,Bash(git *),Bash(python -m unittest *),Bash(C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest *)" --output-format text
 +```
 +
@@ -76,10 +76,10 @@ index a6b66ef..1a196c5 100644
  |     \- test.yml
  |- .vscode/
  |  \- settings.json
--|- reviews/
+-|- docs/threads/done/
 -|  \- README.md
 +|- docs/
-+|  \- reviews/
++|  \- docs/threads/done/
 +|     |- README.md
 +|     |- agents-repo-fit/
 +|     \- full/
@@ -123,9 +123,9 @@ index b3879b3..484a2fd 100644

  ## 2026-04-28

--- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `reviews/` artifact directory.
+-- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `docs/threads/done/` artifact directory.
 +- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added an initial review artifact directory.
-+- Moved review artifacts under `docs/reviews/` and documented robust full-codebase Codex/Claude review commands.
++- Moved review artifacts under `docs/threads/done/` and documented robust full-codebase Codex/Claude review commands.
 +- Ran the first full-codebase review, fixed terminal-state API mutation, malformed action handling, loop routing closure, stale travel-plan cleanup, the graph node hash contract, and the stale Ruff pre-commit hook, then added focused regressions.
 diff --git a/README.md b/README.md
 index b1f450f..dbd1d90 100644
@@ -156,11 +156,11 @@ index b1f450f..dbd1d90 100644

  ### Observation shape
  `observation` is:
-diff --git a/docs/reviews/README.md b/docs/reviews/README.md
+diff --git a/docs/threads/README.md b/docs/threads/README.md
 new file mode 100644
 index 0000000..531bdd2
 --- /dev/null
-+++ b/docs/reviews/README.md
++++ b/docs/threads/README.md
 @@ -0,0 +1,17 @@
 +# Reviews
 +
@@ -169,7 +169,7 @@ index 0000000..531bdd2
 +Use this layout:
 +
 +```text
-+docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/
++docs/threads/done/<scope>/<YYYY-MM-DD>/<iteration>/
 +|- raw/
 +|  |- codex-1.md
 +|  |- opus.md
@@ -179,30 +179,30 @@ index 0000000..531bdd2
 +```
 +
 +Keep review scope names short and kebab-case, such as `agents-repo-fit`, `full`, or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 similarity index 70%
-rename from reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 index 6594514..3ede47b 100644
---- a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
-+++ b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
+--- a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
++++ b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 @@ -3,15 +3,15 @@
  ## Scope

  - Rewrote `AGENTS.md` from a copied workflow template into a Python/py313 workflow for this repo.
--- Added `reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
--- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `reviews/`.
-+- Added `docs/reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
-+- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/reviews/`.
+-- Added `docs/threads/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
+-- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/threads/done/`.
++- Added `docs/threads/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
++- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/threads/done/`.
  - Updated `PROGRESS.md` with a short entry for the process-documentation change.

  ## Validation

  - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`: passed, 167 tests.
--- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1/diff.md reviews/agents-repo-fit/2026-04-28/1/REVIEW.md reviews/agents-repo-fit/2026-04-28/1/raw/codex.md reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
--- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
-+- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1/diff.md docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
-+- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
+-- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
+-- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
++- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
++- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.

  ## Codex Findings

@@ -210,34 +210,34 @@ index 6594514..3ede47b 100644
  ## Claude Findings

  - P2: `PROGRESS.md` and the review artifact path use `2026-04-28`, while the reviewer inferred April 27, 2026 from local session context. Disposition: not accepted for the same reason as the Codex date finding.
--- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `reviews/`.
-+- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/reviews/`.
+-- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/threads/done/`.
++- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/threads/done/`.
  - P3: The review packet should include the `.cursor/rules` deletion and `CLAUDE.md` addition. Disposition: accepted. `diff.md` was regenerated with those paths included.

  ## Result
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/diff.md b/docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
 similarity index 100%
-rename from reviews/agents-repo-fit/2026-04-28/1/diff.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
 similarity index 100%
-rename from reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
 similarity index 100%
-rename from reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
-diff --git a/docs/reviews/full/2026-04-28/1/REVIEW.md b/docs/reviews/full/2026-04-28/1/REVIEW.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
+diff --git a/docs/threads/done/full/2026-04-28/1/REVIEW.md b/docs/threads/done/full/2026-04-28/1/REVIEW.md
 new file mode 100644
 index 0000000..0160cb6
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/REVIEW.md
++++ b/docs/threads/done/full/2026-04-28/1/REVIEW.md
 @@ -0,0 +1,65 @@
 +# Full-Codebase Review: Iteration 1
 +
 +## Reviewer Coverage
 +
-+- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit · resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
++- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit � resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
 +- Per the fallback rule, three independent Codex reviewers were run with `gpt-5.5` and `xhigh` reasoning. Raw outputs are preserved in `raw/codex-1.md`, `raw/codex-2.md`, and `raw/codex-3.md`.
 +- The Codex read-only sandbox blocked direct test execution inside the reviewer subprocesses, so reviewer validation was static. Local verification will run outside the reviewer sandbox before completion.
 +
@@ -273,10 +273,10 @@ index 0000000..0160cb6
 +- Evidence: `Node.__eq__` compares by station, while `Node.__hash__` hashes the node id. Nodes are stored in sets, so equal nodes must have equal hashes.
 +- Disposition: accepted. Hash by the same station identity used for equality and cover set behavior.
 +
-+### Low: moved historical review artifact still mentions old `reviews/` path
++### Low: moved historical review artifact still mentions old `docs/threads/done/` path
 +
 +- Reported by: Codex 2.
-+- Evidence: `docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `reviews/README.md` and validating `reviews/...` paths after the artifact was moved under `docs/reviews/`.
++- Evidence: `docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `docs/threads/README.md` and validating `docs/threads/done/...` paths after the artifact was moved under `docs/threads/done/`.
 +- Disposition: accepted. Update the moved artifact so it remains accurate after the docs-path change.
 +
 +### Low: two tests mutate `sys.path` after project imports
@@ -298,22 +298,22 @@ index 0000000..0160cb6
 +- Reported by: Codex 1 only.
 +- Evidence: metro movement consumes at most one segment endpoint per call and spawn counters are step-based.
 +- Disposition: deferred. This is a broader simulation-contract decision rather than a narrow defect fix. It should be handled in a separate task that decides whether `dt_ms` is a frame-sized tick contract or whether the engine should substep/carry remainders.
-diff --git a/docs/reviews/full/2026-04-28/1/diff.md b/docs/reviews/full/2026-04-28/1/diff.md
+diff --git a/docs/threads/done/full/2026-04-28/1/diff.md b/docs/threads/done/full/2026-04-28/1/diff.md
 new file mode 100644
 index 0000000..cbb222c
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/diff.md
++++ b/docs/threads/done/full/2026-04-28/1/diff.md
 @@ -0,0 +1,5 @@
 +# Full-Codebase Review Diff Context
 +
-+This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `reviews/` to `docs/reviews/`.
++This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `docs/threads/done/` to `docs/threads/done/`.
 +
 +The active findings are synthesized in `REVIEW.md`; raw reviewer outputs are preserved in `raw/`.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-claude.md b/docs/reviews/full/2026-04-28/1/prompt-claude.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-claude.md b/docs/threads/done/full/2026-04-28/1/prompt-claude.md
 new file mode 100644
 index 0000000..76c3d23
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-claude.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-claude.md
 @@ -0,0 +1,17 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
 +
@@ -332,11 +332,11 @@ index 0000000..76c3d23
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-1.md b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md
 new file mode 100644
 index 0000000..76c3d23
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md
 @@ -0,0 +1,17 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
 +
@@ -355,11 +355,11 @@ index 0000000..76c3d23
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-2.md b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
 new file mode 100644
 index 0000000..a565f8a
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
 @@ -0,0 +1,23 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a separate review from the other reviewers; do your own inspection and do not assume their conclusions.
 +
@@ -371,7 +371,7 @@ index 0000000..a565f8a
 +- Programmatic environment/API behavior in `src/env.py`, `src/mediator.py`, and `src/agent_play.py`.
 +- Routing/boarding/game-over edge cases.
 +- Test gaps where behavior is documented but not protected.
-+- Review-process and docs-path consistency after the move to `docs/reviews/`.
++- Review-process and docs-path consistency after the move to `docs/threads/done/`.
 +
 +Constraints:
 +- Do not modify files.
@@ -384,11 +384,11 @@ index 0000000..a565f8a
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-3.md b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
 new file mode 100644
 index 0000000..8886b41
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
 @@ -0,0 +1,23 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a fallback review because Claude is currently quota-limited; do your own inspection and do not assume the other reviewers' conclusions.
 +
@@ -400,7 +400,7 @@ index 0000000..8886b41
 +- Domain logic in `src/graph/`, `src/line.py`, `src/metro.py`, and `src/station.py`.
 +- Resource/path lifecycle cleanup when lines, trains, passengers, or travel plans are removed.
 +- Python equality/hash contracts, mutable shared state, and any edge cases likely to corrupt routing.
-+- Review-process and docs-path consistency after the move to `docs/reviews/`.
++- Review-process and docs-path consistency after the move to `docs/threads/done/`.
 +
 +Constraints:
 +- Do not modify files.
@@ -413,11 +413,11 @@ index 0000000..8886b41
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-1.md b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-1.md b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
 new file mode 100644
 index 0000000..d4c9407
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
 @@ -0,0 +1,20 @@
 +**Findings**
 +
@@ -433,17 +433,17 @@ index 0000000..d4c9407
 +4. Medium - [src/graph/graph_algo.py](C:/Users/38909/Documents/github/python_mini_metro/src/graph/graph_algo.py:17):17-35, [src/entity/path.py](C:/Users/38909/Documents/github/python_mini_metro/src/entity/path.py:51):51-57
 +   Routing ignores the closing edge of looped lines. `Path` creates a last-to-first segment for loops, but `build_station_nodes_dict()` only connects adjacent stations in `path.stations`, so passengers cannot route across the loop closure. Direction: when `path.is_looped`, add neighbors between the last and first nodes and cover it with a BFS/travel-plan test.
 +
-+5. Low - [docs/reviews/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
++5. Low - [docs/threads/done/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
 +   The current full-review artifact directory is incomplete: it has prompts/logs, `raw/opus.md` contains only a quota message, and there is no `diff.md` or `REVIEW.md`. Direction: before committing those artifacts, either complete the iteration with valid reports and synthesis, or leave these transient failed-run files out of the change set.
 +
 +No issue found in the dependency/config basics I checked: `requirements.txt`, `environment.yml`, and CI are aligned on the project's current runtime dependencies.
 +
 +Validation note: I attempted to run the full suite with the requested py313 interpreter and with `python -m unittest -v`, but the harness rejected both command forms before execution, so I could not record a fresh test result.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-2.md b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-2.md b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
 new file mode 100644
 index 0000000..8078f32
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
 @@ -0,0 +1,20 @@
 +**Findings**
 +
@@ -456,20 +456,20 @@ index 0000000..8078f32
 +3. **Medium** - [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:449>)
 +   `remove_path()` removes passengers riding that line from `self.passengers` but leaves their entries in `self.travel_plans`. Repeated create/remove cycles can accumulate stale passenger references and make debugging/routing state misleading. Direction: delete travel-plan entries for every passenger removed with a metro, matching the cleanup already done on delivery.
 +
-+4. **Low** - [docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
-+   The moved review artifact still describes and validates the old `reviews/` path at lines 6-14, while current process docs now require `docs/reviews/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
++4. **Low** - [docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
++   The moved review artifact still describes and validates the old `docs/threads/done/` path at lines 6-14, while current process docs now require `docs/threads/done/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
 +
 +5. **Low** - [test/test_graph.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_graph.py:6>), [test/test_mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_mediator.py:6>)
 +   These modules import from `src` before appending `../src` to `sys.path`, so they depend on another test having already mutated `sys.path`. Direction: move the path setup before project imports, or package/import the project consistently.
 +
 +**Notes**
 +
-+I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/reviews/README.md` mostly consistent with the `docs/reviews/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-3.md b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
++I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/threads/README.md` mostly consistent with the `docs/threads/done/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-3.md b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
 new file mode 100644
 index 0000000..48c47ea
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
 @@ -0,0 +1,27 @@
 +**Findings**
 +
@@ -493,22 +493,22 @@ index 0000000..48c47ea
 +   `Node.__eq__` compares by station, but `Node.__hash__` hashes a unique node id. Equal nodes can therefore have different hashes, which breaks Python's set/dict contract. This is risky because nodes are stored in sets (`neighbors`, `paths`) and tests compare fresh `Node(station)` instances as equal.
 +   Suggested direction: hash by `station` if equality is station-based, or make equality identity/id-based consistently.
 +
-+6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/reviews/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/README.md:8>)
-+   `docs/reviews/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
++6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/threads/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/README.md:8>)
++   `docs/threads/done/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
 +   Suggested direction: complete the iteration before committing, or keep failed/transient run artifacts out of the change set.
 +
 +Tests were not run: the harness rejected `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`, `python -m unittest -v`, and the bytecode-disabled variant.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/opus.md b/docs/reviews/full/2026-04-28/1/raw/opus.md
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/opus.md b/docs/threads/done/full/2026-04-28/1/raw/opus.md
 new file mode 100644
 index 0000000..0799432
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/opus.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/opus.md
 @@ -0,0 +1 @@
 +You've hit your limit - resets 7pm (America/Los_Angeles)
-diff --git a/reviews/README.md b/reviews/README.md
+diff --git a/docs/threads/README.md b/docs/threads/README.md
 deleted file mode 100644
 index d5d2eef..0000000
---- a/reviews/README.md
+--- a/docs/threads/README.md
 +++ /dev/null
 @@ -1,16 +0,0 @@
 -# Reviews
@@ -518,7 +518,7 @@ index d5d2eef..0000000
 -Use this layout:
 -
 -```text
--reviews/<scope>/<YYYY-MM-DD>/<iteration>/
+-docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/
 -|- raw/
 -|  |- codex.md
 -|  \- opus.md
diff --git a/docs/threads/done/full/2026-04-28/2/prompt-claude.md b/docs/threads/done/full/2026-04-28/2/prompt-claude.md
index b1bb2a0..65ac379 100644
--- a/docs/threads/done/full/2026-04-28/2/prompt-claude.md
+++ b/docs/threads/done/full/2026-04-28/2/prompt-claude.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project.

-Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
+Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.

 The prior accepted findings were: post-game-over mutation, malformed action payload crashes/false success, loop routing closure, stale travel-plan cleanup on path removal, `Node` equality/hash mismatch, test import-order dependency, stale moved review artifact text, and an old Ruff pre-commit hook that could not parse `py313`.

diff --git a/docs/threads/done/full/2026-04-28/2/prompt-codex-1.md b/docs/threads/done/full/2026-04-28/2/prompt-codex-1.md
index 0727446..a3e7404 100644
--- a/docs/threads/done/full/2026-04-28/2/prompt-codex-1.md
+++ b/docs/threads/done/full/2026-04-28/2/prompt-codex-1.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project.

-Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
+Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.

 The accepted iteration-1 findings to verify:
 - Programmatic `env.step()` must not mutate actions or simulation time after game over.
@@ -11,7 +11,7 @@ The accepted iteration-1 findings to verify:
 - `Node.__eq__` and `Node.__hash__` must obey Python's equality/hash contract.
 - `test/test_graph.py` and `test/test_mediator.py` should not rely on another test mutating `sys.path`.
 - The Ruff pre-commit hook pin should parse `target-version = "py313"`.
-- Docs should match the implemented behavior and the `docs/reviews/` layout.
+- Docs should match the implemented behavior and the `docs/threads/done/` layout.

 Validation already run locally:
 - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v` passed, 173 tests.
diff --git a/docs/threads/done/full/2026-04-28/2/prompt-codex-2.md b/docs/threads/done/full/2026-04-28/2/prompt-codex-2.md
index 9732deb..a7e1d94 100644
--- a/docs/threads/done/full/2026-04-28/2/prompt-codex-2.md
+++ b/docs/threads/done/full/2026-04-28/2/prompt-codex-2.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project. This is separate from the other reviewers; do your own inspection.

-Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
+Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.

 Pay extra attention to:
 - Whether terminal game-over behavior freezes both action application and time progression without breaking normal `noop`, `pause`, or reward behavior.
@@ -8,7 +8,7 @@ Pay extra attention to:
 - Whether travel-plan invalidation on `remove_path()` handles both onboard removed passengers and station passengers whose plan references the removed path.
 - Whether loop routing now matches loop metro movement.
 - Whether test changes remove order dependence rather than hiding it.
-- Whether docs and review artifacts are accurate after the move to `docs/reviews/`.
+- Whether docs and review artifacts are accurate after the move to `docs/threads/done/`.

 Validation already run locally:
 - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v` passed, 173 tests.
diff --git a/docs/threads/done/full/2026-04-28/2/prompt-codex-3.md b/docs/threads/done/full/2026-04-28/2/prompt-codex-3.md
index 71d40d1..ba1ef3b 100644
--- a/docs/threads/done/full/2026-04-28/2/prompt-codex-3.md
+++ b/docs/threads/done/full/2026-04-28/2/prompt-codex-3.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project. This is a fallback review because Claude is quota-limited; do your own inspection and do not assume the other Codex reviewers' conclusions.

-Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
+Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.

 Focus areas:
 - Correctness of terminal game-over no-op behavior in the programmatic environment.
@@ -9,7 +9,7 @@ Focus areas:
 - Cleanup/invalidation of `travel_plans` on line removal.
 - Python equality/hash contract for graph nodes.
 - Test reliability changes, especially use of real surfaces/mocked draw and deterministic route-compression setup.
-- Process/docs accuracy, including `docs/reviews/` and the Ruff pre-commit hook update.
+- Process/docs accuracy, including `docs/threads/done/` and the Ruff pre-commit hook update.

 Validation already run locally:
 - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v` passed, 173 tests.
diff --git a/docs/threads/done/full/2026-04-28/2/raw/codex-1.md b/docs/threads/done/full/2026-04-28/2/raw/codex-1.md
index 616a4aa..4965134 100644
--- a/docs/threads/done/full/2026-04-28/2/raw/codex-1.md
+++ b/docs/threads/done/full/2026-04-28/2/raw/codex-1.md
@@ -8,4 +8,4 @@ Findings:
    Malformed action schemas can still report success. `loop` is coerced with `bool(...)`, so payloads like `{"type": "create_path", "stations": [0, 1], "loop": "yes"}` mutate state instead of being rejected. Also, a dict with missing/`None` type is treated as a successful noop, even though the documented valid no-op inputs are `None` action or `{"type": "noop"}`.
    Suggested direction: validate `loop` as an actual `bool` when present, and reject dict actions whose `"type"` is absent or `None` unless the intended public contract is updated and documented.

-I did not find remaining important issues in the other accepted fixes during static inspection: game-over no-op handling, aborted path creation return value, loop closing edge routing, path-removal travel-plan cleanup, test import ordering, Ruff hook pin, and `docs/reviews/` path updates otherwise look addressed. I did not rerun tests because this was a read-only re-review and the provided validation already passed.
+I did not find remaining important issues in the other accepted fixes during static inspection: game-over no-op handling, aborted path creation return value, loop closing edge routing, path-removal travel-plan cleanup, test import ordering, Ruff hook pin, and `docs/threads/done/` path updates otherwise look addressed. I did not rerun tests because this was a read-only re-review and the provided validation already passed.
diff --git a/docs/threads/done/full/2026-04-28/3/REVIEW.md b/docs/threads/done/full/2026-04-28/3/REVIEW.md
index 5543bb9..2f99f75 100644
--- a/docs/threads/done/full/2026-04-28/3/REVIEW.md
+++ b/docs/threads/done/full/2026-04-28/3/REVIEW.md
@@ -35,7 +35,7 @@ Disposition: Accepted and fixed by updating `GAME_RULES.md` to distinguish waiti

 ### Low - Transient reviewer PID file in review artifacts

-Codex reviewer 2 found that `docs/reviews/full/2026-04-28/2/reviewer-pids.tsv` was a local process-tracking artifact, not review evidence.
+Codex reviewer 2 found that `docs/threads/done/full/2026-04-28/2/reviewer-pids.tsv` was a local process-tracking artifact, not review evidence.

 Disposition: Accepted and fixed by removing the transient PID file. The same transient file and optional stdout/stderr logs were also removed from iteration 3.

diff --git a/docs/threads/done/full/2026-04-28/3/diff.md b/docs/threads/done/full/2026-04-28/3/diff.md
index d5e1330..dad8aac 100644
--- a/docs/threads/done/full/2026-04-28/3/diff.md
+++ b/docs/threads/done/full/2026-04-28/3/diff.md
@@ -1,4 +1,4 @@
-﻿diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
+diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
 index 9407181..a6514f4 100644
 --- a/.pre-commit-config.yaml
 +++ b/.pre-commit-config.yaml
@@ -19,8 +19,8 @@ index bf60f17..05556a3 100644
  - `ARCHITECTURE.md`: current file structure and architectural boundaries.
  - `GAME_RULES.md`: implementation-aligned game mechanics and controls.
  - `PROGRESS.md`: single running project log.
--- `reviews/`: multi-CLI review artifacts for substantive changes.
-+- `docs/reviews/`: multi-CLI review artifacts for substantive changes and full-codebase audits.
+-- `docs/threads/done/`: multi-CLI review artifacts for substantive changes.
++- `docs/threads/done/`: multi-CLI review artifacts for substantive changes and full-codebase audits.

  ## Validation Gates

@@ -28,16 +28,16 @@ index bf60f17..05556a3 100644
  - Review is required for changes to files such as `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs.
  - Review is also required for game-mechanic changes in `src/`, public API changes in `src/env.py` or `src/mediator.py`, balance/config changes in `src/config.py`, and new architectural boundaries.
  - Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
--- Store review artifacts under `reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
-+- Store review artifacts under `docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
+-- Store review artifacts under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/`:
++- Store review artifacts under `docs/threads/done/<scope>/<YYYY-MM-DD>/<iteration>/`:
    - `raw/codex.md`
    - `raw/opus.md`
 +  - optional extra independent reviewers as `raw/codex-2.md`, `raw/opus-2.md`, etc.
    - optional `raw/*.stdout.log` and `raw/*.stderr.log`
    - `diff.md`
    - `REVIEW.md`
--- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md reviews/README.md`.
-+- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/reviews/README.md`.
+-- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
++- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
  - Reviewer prompt baseline:

  ```text
@@ -47,19 +47,19 @@ index bf60f17..05556a3 100644

 +## Full-Codebase Review
 +
-+- Full-codebase review iterations live under `docs/reviews/full/<YYYY-MM-DD>/<iteration>/`.
++- Full-codebase review iterations live under `docs/threads/done/full/<YYYY-MM-DD>/<iteration>/`.
 +- Before starting a new iteration, inspect existing numeric iteration folders for the same date and use the next number. If earlier iterations exist, give reviewers the previous `REVIEW.md` summaries and ask them to verify that earlier findings were resolved.
 +- Run three independent reviewers. Use both Codex and Claude when available; if one service is unavailable or out of quota, run additional independent instances of the available service until there are three raw reports.
 +- Codex full-codebase reviewer command. Keep the prompt in a file and pipe it through stdin; this avoids PowerShell splitting multi-line prompts into unexpected positional arguments. Use `--ignore-user-config` so local plugin sync or user config does not interfere with a read-only review run:
 +
 +```powershell
-+Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/reviews/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
++Get-Content -Raw docs/threads/done/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/threads/done/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
 +```
 +
 +- Claude full-codebase reviewer command. Keep the prompt in a variable so PowerShell passes it as one argument:
 +
 +```powershell
-+$prompt = Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
++$prompt = Get-Content -Raw docs/threads/done/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
 +claude -p $prompt --model best --effort max --permission-mode bypassPermissions --no-session-persistence --tools "Read,Glob,Grep,Bash" --allowedTools "Read,Glob,Grep,Bash(git *),Bash(python -m unittest *),Bash(C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest *)" --output-format text
 +```
 +
@@ -76,10 +76,10 @@ index a6b66ef..1a196c5 100644
  |     \- test.yml
  |- .vscode/
  |  \- settings.json
--|- reviews/
+-|- docs/threads/done/
 -|  \- README.md
 +|- docs/
-+|  \- reviews/
++|  \- docs/threads/done/
 +|     |- README.md
 +|     |- agents-repo-fit/
 +|     \- full/
@@ -123,9 +123,9 @@ index b3879b3..484a2fd 100644

  ## 2026-04-28

--- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `reviews/` artifact directory.
+-- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `docs/threads/done/` artifact directory.
 +- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added an initial review artifact directory.
-+- Moved review artifacts under `docs/reviews/` and documented robust full-codebase Codex/Claude review commands.
++- Moved review artifacts under `docs/threads/done/` and documented robust full-codebase Codex/Claude review commands.
 +- Ran the first full-codebase review, fixed terminal-state API mutation, malformed action handling, loop routing closure, stale travel-plan cleanup, the graph node hash contract, and the stale Ruff pre-commit hook, then added focused regressions.
 diff --git a/README.md b/README.md
 index b1f450f..808e23d 100644
@@ -164,11 +164,11 @@ index b1f450f..808e23d 100644

  ### Observation shape
  `observation` is:
-diff --git a/docs/reviews/README.md b/docs/reviews/README.md
+diff --git a/docs/threads/README.md b/docs/threads/README.md
 new file mode 100644
 index 0000000..531bdd2
 --- /dev/null
-+++ b/docs/reviews/README.md
++++ b/docs/threads/README.md
 @@ -0,0 +1,17 @@
 +# Reviews
 +
@@ -177,7 +177,7 @@ index 0000000..531bdd2
 +Use this layout:
 +
 +```text
-+docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/
++docs/threads/done/<scope>/<YYYY-MM-DD>/<iteration>/
 +|- raw/
 +|  |- codex-1.md
 +|  |- opus.md
@@ -187,30 +187,30 @@ index 0000000..531bdd2
 +```
 +
 +Keep review scope names short and kebab-case, such as `agents-repo-fit`, `full`, or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 similarity index 70%
-rename from reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 index 6594514..3ede47b 100644
---- a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
-+++ b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
+--- a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
++++ b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 @@ -3,15 +3,15 @@
  ## Scope

  - Rewrote `AGENTS.md` from a copied workflow template into a Python/py313 workflow for this repo.
--- Added `reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
--- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `reviews/`.
-+- Added `docs/reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
-+- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/reviews/`.
+-- Added `docs/threads/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
+-- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/threads/done/`.
++- Added `docs/threads/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
++- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/threads/done/`.
  - Updated `PROGRESS.md` with a short entry for the process-documentation change.

  ## Validation

  - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`: passed, 167 tests.
--- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1/diff.md reviews/agents-repo-fit/2026-04-28/1/REVIEW.md reviews/agents-repo-fit/2026-04-28/1/raw/codex.md reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
--- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
-+- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1/diff.md docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
-+- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
+-- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
+-- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
++- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
++- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.

  ## Codex Findings

@@ -218,34 +218,34 @@ index 6594514..3ede47b 100644
  ## Claude Findings

  - P2: `PROGRESS.md` and the review artifact path use `2026-04-28`, while the reviewer inferred April 27, 2026 from local session context. Disposition: not accepted for the same reason as the Codex date finding.
--- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `reviews/`.
-+- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/reviews/`.
+-- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/threads/done/`.
++- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/threads/done/`.
  - P3: The review packet should include the `.cursor/rules` deletion and `CLAUDE.md` addition. Disposition: accepted. `diff.md` was regenerated with those paths included.

  ## Result
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/diff.md b/docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
 similarity index 100%
-rename from reviews/agents-repo-fit/2026-04-28/1/diff.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
 similarity index 100%
-rename from reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
-diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
+diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
 similarity index 100%
-rename from reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
-rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
-diff --git a/docs/reviews/full/2026-04-28/1/REVIEW.md b/docs/reviews/full/2026-04-28/1/REVIEW.md
+rename from docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
+rename to docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
+diff --git a/docs/threads/done/full/2026-04-28/1/REVIEW.md b/docs/threads/done/full/2026-04-28/1/REVIEW.md
 new file mode 100644
 index 0000000..0160cb6
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/REVIEW.md
++++ b/docs/threads/done/full/2026-04-28/1/REVIEW.md
 @@ -0,0 +1,65 @@
 +# Full-Codebase Review: Iteration 1
 +
 +## Reviewer Coverage
 +
-+- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit · resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
++- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit � resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
 +- Per the fallback rule, three independent Codex reviewers were run with `gpt-5.5` and `xhigh` reasoning. Raw outputs are preserved in `raw/codex-1.md`, `raw/codex-2.md`, and `raw/codex-3.md`.
 +- The Codex read-only sandbox blocked direct test execution inside the reviewer subprocesses, so reviewer validation was static. Local verification will run outside the reviewer sandbox before completion.
 +
@@ -281,10 +281,10 @@ index 0000000..0160cb6
 +- Evidence: `Node.__eq__` compares by station, while `Node.__hash__` hashes the node id. Nodes are stored in sets, so equal nodes must have equal hashes.
 +- Disposition: accepted. Hash by the same station identity used for equality and cover set behavior.
 +
-+### Low: moved historical review artifact still mentions old `reviews/` path
++### Low: moved historical review artifact still mentions old `docs/threads/done/` path
 +
 +- Reported by: Codex 2.
-+- Evidence: `docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `reviews/README.md` and validating `reviews/...` paths after the artifact was moved under `docs/reviews/`.
++- Evidence: `docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `docs/threads/README.md` and validating `docs/threads/done/...` paths after the artifact was moved under `docs/threads/done/`.
 +- Disposition: accepted. Update the moved artifact so it remains accurate after the docs-path change.
 +
 +### Low: two tests mutate `sys.path` after project imports
@@ -306,22 +306,22 @@ index 0000000..0160cb6
 +- Reported by: Codex 1 only.
 +- Evidence: metro movement consumes at most one segment endpoint per call and spawn counters are step-based.
 +- Disposition: deferred. This is a broader simulation-contract decision rather than a narrow defect fix. It should be handled in a separate task that decides whether `dt_ms` is a frame-sized tick contract or whether the engine should substep/carry remainders.
-diff --git a/docs/reviews/full/2026-04-28/1/diff.md b/docs/reviews/full/2026-04-28/1/diff.md
+diff --git a/docs/threads/done/full/2026-04-28/1/diff.md b/docs/threads/done/full/2026-04-28/1/diff.md
 new file mode 100644
 index 0000000..cbb222c
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/diff.md
++++ b/docs/threads/done/full/2026-04-28/1/diff.md
 @@ -0,0 +1,5 @@
 +# Full-Codebase Review Diff Context
 +
-+This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `reviews/` to `docs/reviews/`.
++This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `docs/threads/done/` to `docs/threads/done/`.
 +
 +The active findings are synthesized in `REVIEW.md`; raw reviewer outputs are preserved in `raw/`.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-claude.md b/docs/reviews/full/2026-04-28/1/prompt-claude.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-claude.md b/docs/threads/done/full/2026-04-28/1/prompt-claude.md
 new file mode 100644
 index 0000000..76c3d23
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-claude.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-claude.md
 @@ -0,0 +1,17 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
 +
@@ -340,11 +340,11 @@ index 0000000..76c3d23
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-1.md b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md
 new file mode 100644
 index 0000000..76c3d23
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md
 @@ -0,0 +1,17 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
 +
@@ -363,11 +363,11 @@ index 0000000..76c3d23
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-2.md b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
 new file mode 100644
 index 0000000..a565f8a
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
 @@ -0,0 +1,23 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a separate review from the other reviewers; do your own inspection and do not assume their conclusions.
 +
@@ -379,7 +379,7 @@ index 0000000..a565f8a
 +- Programmatic environment/API behavior in `src/env.py`, `src/mediator.py`, and `src/agent_play.py`.
 +- Routing/boarding/game-over edge cases.
 +- Test gaps where behavior is documented but not protected.
-+- Review-process and docs-path consistency after the move to `docs/reviews/`.
++- Review-process and docs-path consistency after the move to `docs/threads/done/`.
 +
 +Constraints:
 +- Do not modify files.
@@ -392,11 +392,11 @@ index 0000000..a565f8a
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-3.md b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
+diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
 new file mode 100644
 index 0000000..8886b41
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
 @@ -0,0 +1,23 @@
 +You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a fallback review because Claude is currently quota-limited; do your own inspection and do not assume the other reviewers' conclusions.
 +
@@ -408,7 +408,7 @@ index 0000000..8886b41
 +- Domain logic in `src/graph/`, `src/line.py`, `src/metro.py`, and `src/station.py`.
 +- Resource/path lifecycle cleanup when lines, trains, passengers, or travel plans are removed.
 +- Python equality/hash contracts, mutable shared state, and any edge cases likely to corrupt routing.
-+- Review-process and docs-path consistency after the move to `docs/reviews/`.
++- Review-process and docs-path consistency after the move to `docs/threads/done/`.
 +
 +Constraints:
 +- Do not modify files.
@@ -421,11 +421,11 @@ index 0000000..8886b41
 +- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 +- Include a short "No issue" statement for areas you checked and found sound only if useful.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-1.md b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-1.md b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
 new file mode 100644
 index 0000000..d4c9407
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
 @@ -0,0 +1,20 @@
 +**Findings**
 +
@@ -441,17 +441,17 @@ index 0000000..d4c9407
 +4. Medium - [src/graph/graph_algo.py](C:/Users/38909/Documents/github/python_mini_metro/src/graph/graph_algo.py:17):17-35, [src/entity/path.py](C:/Users/38909/Documents/github/python_mini_metro/src/entity/path.py:51):51-57
 +   Routing ignores the closing edge of looped lines. `Path` creates a last-to-first segment for loops, but `build_station_nodes_dict()` only connects adjacent stations in `path.stations`, so passengers cannot route across the loop closure. Direction: when `path.is_looped`, add neighbors between the last and first nodes and cover it with a BFS/travel-plan test.
 +
-+5. Low - [docs/reviews/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
++5. Low - [docs/threads/done/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
 +   The current full-review artifact directory is incomplete: it has prompts/logs, `raw/opus.md` contains only a quota message, and there is no `diff.md` or `REVIEW.md`. Direction: before committing those artifacts, either complete the iteration with valid reports and synthesis, or leave these transient failed-run files out of the change set.
 +
 +No issue found in the dependency/config basics I checked: `requirements.txt`, `environment.yml`, and CI are aligned on the project's current runtime dependencies.
 +
 +Validation note: I attempted to run the full suite with the requested py313 interpreter and with `python -m unittest -v`, but the harness rejected both command forms before execution, so I could not record a fresh test result.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-2.md b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-2.md b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
 new file mode 100644
 index 0000000..8078f32
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
 @@ -0,0 +1,20 @@
 +**Findings**
 +
@@ -464,20 +464,20 @@ index 0000000..8078f32
 +3. **Medium** - [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:449>)
 +   `remove_path()` removes passengers riding that line from `self.passengers` but leaves their entries in `self.travel_plans`. Repeated create/remove cycles can accumulate stale passenger references and make debugging/routing state misleading. Direction: delete travel-plan entries for every passenger removed with a metro, matching the cleanup already done on delivery.
 +
-+4. **Low** - [docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
-+   The moved review artifact still describes and validates the old `reviews/` path at lines 6-14, while current process docs now require `docs/reviews/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
++4. **Low** - [docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
++   The moved review artifact still describes and validates the old `docs/threads/done/` path at lines 6-14, while current process docs now require `docs/threads/done/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
 +
 +5. **Low** - [test/test_graph.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_graph.py:6>), [test/test_mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_mediator.py:6>)
 +   These modules import from `src` before appending `../src` to `sys.path`, so they depend on another test having already mutated `sys.path`. Direction: move the path setup before project imports, or package/import the project consistently.
 +
 +**Notes**
 +
-+I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/reviews/README.md` mostly consistent with the `docs/reviews/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-3.md b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
++I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/threads/README.md` mostly consistent with the `docs/threads/done/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-3.md b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
 new file mode 100644
 index 0000000..48c47ea
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
 @@ -0,0 +1,27 @@
 +**Findings**
 +
@@ -501,23 +501,23 @@ index 0000000..48c47ea
 +   `Node.__eq__` compares by station, but `Node.__hash__` hashes a unique node id. Equal nodes can therefore have different hashes, which breaks Python's set/dict contract. This is risky because nodes are stored in sets (`neighbors`, `paths`) and tests compare fresh `Node(station)` instances as equal.
 +   Suggested direction: hash by `station` if equality is station-based, or make equality identity/id-based consistently.
 +
-+6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/reviews/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/README.md:8>)
-+   `docs/reviews/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
++6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/threads/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/README.md:8>)
++   `docs/threads/done/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
 +   Suggested direction: complete the iteration before committing, or keep failed/transient run artifacts out of the change set.
 +
 +Tests were not run: the harness rejected `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`, `python -m unittest -v`, and the bytecode-disabled variant.
-diff --git a/docs/reviews/full/2026-04-28/1/raw/opus.md b/docs/reviews/full/2026-04-28/1/raw/opus.md
+diff --git a/docs/threads/done/full/2026-04-28/1/raw/opus.md b/docs/threads/done/full/2026-04-28/1/raw/opus.md
 new file mode 100644
 index 0000000..0799432
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/1/raw/opus.md
++++ b/docs/threads/done/full/2026-04-28/1/raw/opus.md
 @@ -0,0 +1 @@
 +You've hit your limit - resets 7pm (America/Los_Angeles)
-diff --git a/docs/reviews/full/2026-04-28/2/REVIEW.md b/docs/reviews/full/2026-04-28/2/REVIEW.md
+diff --git a/docs/threads/done/full/2026-04-28/2/REVIEW.md b/docs/threads/done/full/2026-04-28/2/REVIEW.md
 new file mode 100644
 index 0000000..45e83a3
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/REVIEW.md
++++ b/docs/threads/done/full/2026-04-28/2/REVIEW.md
 @@ -0,0 +1,46 @@
 +# Full-Codebase Review: Iteration 2
 +
@@ -565,13 +565,13 @@ index 0000000..45e83a3
 +- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff check <changed Python files>`: passed.
 +- `C:\Users\38909\miniconda3\envs\py313\python.exe -m ruff format --check <changed Python files>`: passed.
 +- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files <changed files>`: passed.
-diff --git a/docs/reviews/full/2026-04-28/2/diff.md b/docs/reviews/full/2026-04-28/2/diff.md
+diff --git a/docs/threads/done/full/2026-04-28/2/diff.md b/docs/threads/done/full/2026-04-28/2/diff.md
 new file mode 100644
 index 0000000..1e9dbd3
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/diff.md
++++ b/docs/threads/done/full/2026-04-28/2/diff.md
 @@ -0,0 +1,1294 @@
-+﻿diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
++?diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
 +index 9407181..a6514f4 100644
 +--- a/.pre-commit-config.yaml
 ++++ b/.pre-commit-config.yaml
@@ -592,8 +592,8 @@ index 0000000..1e9dbd3
 + - `ARCHITECTURE.md`: current file structure and architectural boundaries.
 + - `GAME_RULES.md`: implementation-aligned game mechanics and controls.
 + - `PROGRESS.md`: single running project log.
-+-- `reviews/`: multi-CLI review artifacts for substantive changes.
-++- `docs/reviews/`: multi-CLI review artifacts for substantive changes and full-codebase audits.
++-- `docs/threads/done/`: multi-CLI review artifacts for substantive changes.
+++- `docs/threads/done/`: multi-CLI review artifacts for substantive changes and full-codebase audits.
 +
 + ## Validation Gates
 +
@@ -601,16 +601,16 @@ index 0000000..1e9dbd3
 + - Review is required for changes to files such as `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs.
 + - Review is also required for game-mechanic changes in `src/`, public API changes in `src/env.py` or `src/mediator.py`, balance/config changes in `src/config.py`, and new architectural boundaries.
 + - Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
-+-- Store review artifacts under `reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
-++- Store review artifacts under `docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
++-- Store review artifacts under `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/`:
+++- Store review artifacts under `docs/threads/done/<scope>/<YYYY-MM-DD>/<iteration>/`:
 +   - `raw/codex.md`
 +   - `raw/opus.md`
 ++  - optional extra independent reviewers as `raw/codex-2.md`, `raw/opus-2.md`, etc.
 +   - optional `raw/*.stdout.log` and `raw/*.stderr.log`
 +   - `diff.md`
 +   - `REVIEW.md`
-+-- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md reviews/README.md`.
-++- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/reviews/README.md`.
++-- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
+++- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/threads/README.md`.
 + - Reviewer prompt baseline:
 +
 + ```text
@@ -620,19 +620,19 @@ index 0000000..1e9dbd3
 +
 ++## Full-Codebase Review
 ++
-++- Full-codebase review iterations live under `docs/reviews/full/<YYYY-MM-DD>/<iteration>/`.
+++- Full-codebase review iterations live under `docs/threads/done/full/<YYYY-MM-DD>/<iteration>/`.
 ++- Before starting a new iteration, inspect existing numeric iteration folders for the same date and use the next number. If earlier iterations exist, give reviewers the previous `REVIEW.md` summaries and ask them to verify that earlier findings were resolved.
 ++- Run three independent reviewers. Use both Codex and Claude when available; if one service is unavailable or out of quota, run additional independent instances of the available service until there are three raw reports.
 ++- Codex full-codebase reviewer command. Keep the prompt in a file and pipe it through stdin; this avoids PowerShell splitting multi-line prompts into unexpected positional arguments. Use `--ignore-user-config` so local plugin sync or user config does not interfere with a read-only review run:
 ++
 ++```powershell
-++Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/reviews/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
+++Get-Content -Raw docs/threads/done/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/threads/done/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
 ++```
 ++
 ++- Claude full-codebase reviewer command. Keep the prompt in a variable so PowerShell passes it as one argument:
 ++
 ++```powershell
-++$prompt = Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
+++$prompt = Get-Content -Raw docs/threads/done/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
 ++claude -p $prompt --model best --effort max --permission-mode bypassPermissions --no-session-persistence --tools "Read,Glob,Grep,Bash" --allowedTools "Read,Glob,Grep,Bash(git *),Bash(python -m unittest *),Bash(C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest *)" --output-format text
 ++```
 ++
@@ -649,10 +649,10 @@ index 0000000..1e9dbd3
 + |     \- test.yml
 + |- .vscode/
 + |  \- settings.json
-+-|- reviews/
++-|- docs/threads/done/
 +-|  \- README.md
 ++|- docs/
-++|  \- reviews/
+++|  \- docs/threads/done/
 ++|     |- README.md
 ++|     |- agents-repo-fit/
 ++|     \- full/
@@ -696,9 +696,9 @@ index 0000000..1e9dbd3
 +
 + ## 2026-04-28
 +
-+-- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `reviews/` artifact directory.
++-- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `docs/threads/done/` artifact directory.
 ++- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added an initial review artifact directory.
-++- Moved review artifacts under `docs/reviews/` and documented robust full-codebase Codex/Claude review commands.
+++- Moved review artifacts under `docs/threads/done/` and documented robust full-codebase Codex/Claude review commands.
 ++- Ran the first full-codebase review, fixed terminal-state API mutation, malformed action handling, loop routing closure, stale travel-plan cleanup, the graph node hash contract, and the stale Ruff pre-commit hook, then added focused regressions.
 +diff --git a/README.md b/README.md
 +index b1f450f..dbd1d90 100644
@@ -729,11 +729,11 @@ index 0000000..1e9dbd3
 +
 + ### Observation shape
 + `observation` is:
-+diff --git a/docs/reviews/README.md b/docs/reviews/README.md
++diff --git a/docs/threads/README.md b/docs/threads/README.md
 +new file mode 100644
 +index 0000000..531bdd2
 +--- /dev/null
-++++ b/docs/reviews/README.md
+++++ b/docs/threads/README.md
 +@@ -0,0 +1,17 @@
 ++# Reviews
 ++
@@ -742,7 +742,7 @@ index 0000000..1e9dbd3
 ++Use this layout:
 ++
 ++```text
-++docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/
+++docs/threads/done/<scope>/<YYYY-MM-DD>/<iteration>/
 ++|- raw/
 ++|  |- codex-1.md
 ++|  |- opus.md
@@ -752,30 +752,30 @@ index 0000000..1e9dbd3
 ++```
 ++
 ++Keep review scope names short and kebab-case, such as `agents-repo-fit`, `full`, or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
-+diff --git a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
++diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 +similarity index 70%
-+rename from reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
-+rename to docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
++rename from docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
++rename to docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 +index 6594514..3ede47b 100644
-+--- a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
-++++ b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
++--- a/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
+++++ b/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md
 +@@ -3,15 +3,15 @@
 + ## Scope
 +
 + - Rewrote `AGENTS.md` from a copied workflow template into a Python/py313 workflow for this repo.
-+-- Added `reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
-+-- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `reviews/`.
-++- Added `docs/reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
-++- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/reviews/`.
++-- Added `docs/threads/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
++-- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/threads/done/`.
+++- Added `docs/threads/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
+++- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/threads/done/`.
 + - Updated `PROGRESS.md` with a short entry for the process-documentation change.
 +
 + ## Validation
 +
 + - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`: passed, 167 tests.
-+-- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1/diff.md reviews/agents-repo-fit/2026-04-28/1/REVIEW.md reviews/agents-repo-fit/2026-04-28/1/raw/codex.md reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
-+-- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
-++- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1/diff.md docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
-++- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
++-- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
++-- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
+++- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
+++- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/threads/README.md docs/threads/done/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
 +
 + ## Codex Findings
 +
@@ -783,34 +783,34 @@ index 0000000..1e9dbd3
 + ## Claude Findings
 +
 + - P2: `PROGRESS.md` and the review artifact path use `2026-04-28`, while the reviewer inferred April 27, 2026 from local session context. Disposition: not accepted for the same reason as the Codex date finding.
-+-- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `reviews/`.
-++- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/reviews/`.
++-- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/threads/done/`.
+++- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/threads/done/`.
 + - P3: The review packet should include the `.cursor/rules` deletion and `CLAUDE.md` addition. Disposition: accepted. `diff.md` was regenerated with those paths included.
 +
 + ## Result
-+diff --git a/reviews/agents-repo-fit/2026-04-28/1/diff.md b/docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
++diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
 +similarity index 100%
-+rename from reviews/agents-repo-fit/2026-04-28/1/diff.md
-+rename to docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
-+diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
++rename from docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
++rename to docs/threads/done/agents-repo-fit/2026-04-28/1/diff.md
++diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
 +similarity index 100%
-+rename from reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
-+rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
-+diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
++rename from docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
++rename to docs/threads/done/agents-repo-fit/2026-04-28/1/raw/codex.md
++diff --git a/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
 +similarity index 100%
-+rename from reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
-+rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
-+diff --git a/docs/reviews/full/2026-04-28/1/REVIEW.md b/docs/reviews/full/2026-04-28/1/REVIEW.md
++rename from docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
++rename to docs/threads/done/agents-repo-fit/2026-04-28/1/raw/opus.md
++diff --git a/docs/threads/done/full/2026-04-28/1/REVIEW.md b/docs/threads/done/full/2026-04-28/1/REVIEW.md
 +new file mode 100644
 +index 0000000..0160cb6
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/REVIEW.md
+++++ b/docs/threads/done/full/2026-04-28/1/REVIEW.md
 +@@ -0,0 +1,65 @@
 ++# Full-Codebase Review: Iteration 1
 ++
 ++## Reviewer Coverage
 ++
-++- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit · resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
+++- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit � resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
 ++- Per the fallback rule, three independent Codex reviewers were run with `gpt-5.5` and `xhigh` reasoning. Raw outputs are preserved in `raw/codex-1.md`, `raw/codex-2.md`, and `raw/codex-3.md`.
 ++- The Codex read-only sandbox blocked direct test execution inside the reviewer subprocesses, so reviewer validation was static. Local verification will run outside the reviewer sandbox before completion.
 ++
@@ -846,10 +846,10 @@ index 0000000..1e9dbd3
 ++- Evidence: `Node.__eq__` compares by station, while `Node.__hash__` hashes the node id. Nodes are stored in sets, so equal nodes must have equal hashes.
 ++- Disposition: accepted. Hash by the same station identity used for equality and cover set behavior.
 ++
-++### Low: moved historical review artifact still mentions old `reviews/` path
+++### Low: moved historical review artifact still mentions old `docs/threads/done/` path
 ++
 ++- Reported by: Codex 2.
-++- Evidence: `docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `reviews/README.md` and validating `reviews/...` paths after the artifact was moved under `docs/reviews/`.
+++- Evidence: `docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `docs/threads/README.md` and validating `docs/threads/done/...` paths after the artifact was moved under `docs/threads/done/`.
 ++- Disposition: accepted. Update the moved artifact so it remains accurate after the docs-path change.
 ++
 ++### Low: two tests mutate `sys.path` after project imports
@@ -871,22 +871,22 @@ index 0000000..1e9dbd3
 ++- Reported by: Codex 1 only.
 ++- Evidence: metro movement consumes at most one segment endpoint per call and spawn counters are step-based.
 ++- Disposition: deferred. This is a broader simulation-contract decision rather than a narrow defect fix. It should be handled in a separate task that decides whether `dt_ms` is a frame-sized tick contract or whether the engine should substep/carry remainders.
-+diff --git a/docs/reviews/full/2026-04-28/1/diff.md b/docs/reviews/full/2026-04-28/1/diff.md
++diff --git a/docs/threads/done/full/2026-04-28/1/diff.md b/docs/threads/done/full/2026-04-28/1/diff.md
 +new file mode 100644
 +index 0000000..cbb222c
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/diff.md
+++++ b/docs/threads/done/full/2026-04-28/1/diff.md
 +@@ -0,0 +1,5 @@
 ++# Full-Codebase Review Diff Context
 ++
-++This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `reviews/` to `docs/reviews/`.
+++This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `docs/threads/done/` to `docs/threads/done/`.
 ++
 ++The active findings are synthesized in `REVIEW.md`; raw reviewer outputs are preserved in `raw/`.
-+diff --git a/docs/reviews/full/2026-04-28/1/prompt-claude.md b/docs/reviews/full/2026-04-28/1/prompt-claude.md
++diff --git a/docs/threads/done/full/2026-04-28/1/prompt-claude.md b/docs/threads/done/full/2026-04-28/1/prompt-claude.md
 +new file mode 100644
 +index 0000000..76c3d23
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/prompt-claude.md
+++++ b/docs/threads/done/full/2026-04-28/1/prompt-claude.md
 +@@ -0,0 +1,17 @@
 ++You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
 ++
@@ -905,11 +905,11 @@ index 0000000..1e9dbd3
 ++- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 ++- Include a short "No issue" statement for areas you checked and found sound only if useful.
 ++- Do not provide patches.
-+diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-1.md b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
++diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md
 +new file mode 100644
 +index 0000000..76c3d23
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
+++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-1.md
 +@@ -0,0 +1,17 @@
 ++You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
 ++
@@ -928,11 +928,11 @@ index 0000000..1e9dbd3
 ++- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 ++- Include a short "No issue" statement for areas you checked and found sound only if useful.
 ++- Do not provide patches.
-+diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-2.md b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
++diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
 +new file mode 100644
 +index 0000000..a565f8a
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
+++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-2.md
 +@@ -0,0 +1,23 @@
 ++You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a separate review from the other reviewers; do your own inspection and do not assume their conclusions.
 ++
@@ -944,7 +944,7 @@ index 0000000..1e9dbd3
 ++- Programmatic environment/API behavior in `src/env.py`, `src/mediator.py`, and `src/agent_play.py`.
 ++- Routing/boarding/game-over edge cases.
 ++- Test gaps where behavior is documented but not protected.
-++- Review-process and docs-path consistency after the move to `docs/reviews/`.
+++- Review-process and docs-path consistency after the move to `docs/threads/done/`.
 ++
 ++Constraints:
 ++- Do not modify files.
@@ -957,11 +957,11 @@ index 0000000..1e9dbd3
 ++- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 ++- Include a short "No issue" statement for areas you checked and found sound only if useful.
 ++- Do not provide patches.
-+diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-3.md b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
++diff --git a/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
 +new file mode 100644
 +index 0000000..8886b41
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
+++++ b/docs/threads/done/full/2026-04-28/1/prompt-codex-3.md
 +@@ -0,0 +1,23 @@
 ++You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a fallback review because Claude is currently quota-limited; do your own inspection and do not assume the other reviewers' conclusions.
 ++
@@ -973,7 +973,7 @@ index 0000000..1e9dbd3
 ++- Domain logic in `src/graph/`, `src/line.py`, `src/metro.py`, and `src/station.py`.
 ++- Resource/path lifecycle cleanup when lines, trains, passengers, or travel plans are removed.
 ++- Python equality/hash contracts, mutable shared state, and any edge cases likely to corrupt routing.
-++- Review-process and docs-path consistency after the move to `docs/reviews/`.
+++- Review-process and docs-path consistency after the move to `docs/threads/done/`.
 ++
 ++Constraints:
 ++- Do not modify files.
@@ -986,11 +986,11 @@ index 0000000..1e9dbd3
 ++- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
 ++- Include a short "No issue" statement for areas you checked and found sound only if useful.
 ++- Do not provide patches.
-+diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-1.md b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
++diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-1.md b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
 +new file mode 100644
 +index 0000000..d4c9407
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
+++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-1.md
 +@@ -0,0 +1,20 @@
 ++**Findings**
 ++
@@ -1006,17 +1006,17 @@ index 0000000..1e9dbd3
 ++4. Medium - [src/graph/graph_algo.py](C:/Users/38909/Documents/github/python_mini_metro/src/graph/graph_algo.py:17):17-35, [src/entity/path.py](C:/Users/38909/Documents/github/python_mini_metro/src/entity/path.py:51):51-57
 ++   Routing ignores the closing edge of looped lines. `Path` creates a last-to-first segment for loops, but `build_station_nodes_dict()` only connects adjacent stations in `path.stations`, so passengers cannot route across the loop closure. Direction: when `path.is_looped`, add neighbors between the last and first nodes and cover it with a BFS/travel-plan test.
 ++
-++5. Low - [docs/reviews/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
+++5. Low - [docs/threads/done/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
 ++   The current full-review artifact directory is incomplete: it has prompts/logs, `raw/opus.md` contains only a quota message, and there is no `diff.md` or `REVIEW.md`. Direction: before committing those artifacts, either complete the iteration with valid reports and synthesis, or leave these transient failed-run files out of the change set.
 ++
 ++No issue found in the dependency/config basics I checked: `requirements.txt`, `environment.yml`, and CI are aligned on the project's current runtime dependencies.
 ++
 ++Validation note: I attempted to run the full suite with the requested py313 interpreter and with `python -m unittest -v`, but the harness rejected both command forms before execution, so I could not record a fresh test result.
-+diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-2.md b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
++diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-2.md b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
 +new file mode 100644
 +index 0000000..8078f32
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
+++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-2.md
 +@@ -0,0 +1,20 @@
 ++**Findings**
 ++
@@ -1029,20 +1029,20 @@ index 0000000..1e9dbd3
 ++3. **Medium** - [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:449>)
 ++   `remove_path()` removes passengers riding that line from `self.passengers` but leaves their entries in `self.travel_plans`. Repeated create/remove cycles can accumulate stale passenger references and make debugging/routing state misleading. Direction: delete travel-plan entries for every passenger removed with a metro, matching the cleanup already done on delivery.
 ++
-++4. **Low** - [docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
-++   The moved review artifact still describes and validates the old `reviews/` path at lines 6-14, while current process docs now require `docs/reviews/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
+++4. **Low** - [docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
+++   The moved review artifact still describes and validates the old `docs/threads/done/` path at lines 6-14, while current process docs now require `docs/threads/done/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
 ++
 ++5. **Low** - [test/test_graph.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_graph.py:6>), [test/test_mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_mediator.py:6>)
 ++   These modules import from `src` before appending `../src` to `sys.path`, so they depend on another test having already mutated `sys.path`. Direction: move the path setup before project imports, or package/import the project consistently.
 ++
 ++**Notes**
 ++
-++I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/reviews/README.md` mostly consistent with the `docs/reviews/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
-+diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-3.md b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
+++I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/threads/README.md` mostly consistent with the `docs/threads/done/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
++diff --git a/docs/threads/done/full/2026-04-28/1/raw/codex-3.md b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
 +new file mode 100644
 +index 0000000..48c47ea
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
+++++ b/docs/threads/done/full/2026-04-28/1/raw/codex-3.md
 +@@ -0,0 +1,27 @@
 ++**Findings**
 ++
@@ -1066,22 +1066,22 @@ index 0000000..1e9dbd3
 ++   `Node.__eq__` compares by station, but `Node.__hash__` hashes a unique node id. Equal nodes can therefore have different hashes, which breaks Python's set/dict contract. This is risky because nodes are stored in sets (`neighbors`, `paths`) and tests compare fresh `Node(station)` instances as equal.
 ++   Suggested direction: hash by `station` if equality is station-based, or make equality identity/id-based consistently.
 ++
-++6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/reviews/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/README.md:8>)
-++   `docs/reviews/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
+++6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/threads/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/threads/README.md:8>)
+++   `docs/threads/done/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
 ++   Suggested direction: complete the iteration before committing, or keep failed/transient run artifacts out of the change set.
 ++
 ++Tests were not run: the harness rejected `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`, `python -m unittest -v`, and the bytecode-disabled variant.
-+diff --git a/docs/reviews/full/2026-04-28/1/raw/opus.md b/docs/reviews/full/2026-04-28/1/raw/opus.md
++diff --git a/docs/threads/done/full/2026-04-28/1/raw/opus.md b/docs/threads/done/full/2026-04-28/1/raw/opus.md
 +new file mode 100644
 +index 0000000..0799432
 +--- /dev/null
-++++ b/docs/reviews/full/2026-04-28/1/raw/opus.md
+++++ b/docs/threads/done/full/2026-04-28/1/raw/opus.md
 +@@ -0,0 +1 @@
 ++You've hit your limit - resets 7pm (America/Los_Angeles)
-+diff --git a/reviews/README.md b/reviews/README.md
++diff --git a/docs/threads/README.md b/docs/threads/README.md
 +deleted file mode 100644
 +index d5d2eef..0000000
-+--- a/reviews/README.md
++--- a/docs/threads/README.md
 ++++ /dev/null
 +@@ -1,16 +0,0 @@
 +-# Reviews
@@ -1091,7 +1091,7 @@ index 0000000..1e9dbd3
 +-Use this layout:
 +-
 +-```text
-+-reviews/<scope>/<YYYY-MM-DD>/<iteration>/
++-docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/
 +-|- raw/
 +-|  |- codex.md
 +-|  \- opus.md
@@ -1865,15 +1865,15 @@ index 0000000..1e9dbd3
 +         mediator.stations = [
 +             start_station,
 +             intermediate_station,
-diff --git a/docs/reviews/full/2026-04-28/2/prompt-claude.md b/docs/reviews/full/2026-04-28/2/prompt-claude.md
+diff --git a/docs/threads/done/full/2026-04-28/2/prompt-claude.md b/docs/threads/done/full/2026-04-28/2/prompt-claude.md
 new file mode 100644
 index 0000000..b1bb2a0
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/prompt-claude.md
++++ b/docs/threads/done/full/2026-04-28/2/prompt-claude.md
 @@ -0,0 +1,22 @@
 +You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project.
 +
-+Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
++Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.
 +
 +The prior accepted findings were: post-game-over mutation, malformed action payload crashes/false success, loop routing closure, stale travel-plan cleanup on path removal, `Node` equality/hash mismatch, test import-order dependency, stale moved review artifact text, and an old Ruff pre-commit hook that could not parse `py313`.
 +
@@ -1893,15 +1893,15 @@ index 0000000..b1bb2a0
 +- For each finding, include severity, file path, tight line range, explanation, and concrete suggested direction.
 +- If no real issues remain, say that directly.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/2/prompt-codex-1.md b/docs/reviews/full/2026-04-28/2/prompt-codex-1.md
+diff --git a/docs/threads/done/full/2026-04-28/2/prompt-codex-1.md b/docs/threads/done/full/2026-04-28/2/prompt-codex-1.md
 new file mode 100644
 index 0000000..0727446
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/prompt-codex-1.md
++++ b/docs/threads/done/full/2026-04-28/2/prompt-codex-1.md
 @@ -0,0 +1,33 @@
 +You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project.
 +
-+Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
++Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.
 +
 +The accepted iteration-1 findings to verify:
 +- Programmatic `env.step()` must not mutate actions or simulation time after game over.
@@ -1912,7 +1912,7 @@ index 0000000..0727446
 +- `Node.__eq__` and `Node.__hash__` must obey Python's equality/hash contract.
 +- `test/test_graph.py` and `test/test_mediator.py` should not rely on another test mutating `sys.path`.
 +- The Ruff pre-commit hook pin should parse `target-version = "py313"`.
-+- Docs should match the implemented behavior and the `docs/reviews/` layout.
++- Docs should match the implemented behavior and the `docs/threads/done/` layout.
 +
 +Validation already run locally:
 +- `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v` passed, 173 tests.
@@ -1932,15 +1932,15 @@ index 0000000..0727446
 +- For each finding, include severity, file path, tight line range, explanation, and concrete suggested direction.
 +- If no real issues remain, say that directly.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/2/prompt-codex-2.md b/docs/reviews/full/2026-04-28/2/prompt-codex-2.md
+diff --git a/docs/threads/done/full/2026-04-28/2/prompt-codex-2.md b/docs/threads/done/full/2026-04-28/2/prompt-codex-2.md
 new file mode 100644
 index 0000000..9732deb
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/prompt-codex-2.md
++++ b/docs/threads/done/full/2026-04-28/2/prompt-codex-2.md
 @@ -0,0 +1,28 @@
 +You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project. This is separate from the other reviewers; do your own inspection.
 +
-+Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
++Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.
 +
 +Pay extra attention to:
 +- Whether terminal game-over behavior freezes both action application and time progression without breaking normal `noop`, `pause`, or reward behavior.
@@ -1948,7 +1948,7 @@ index 0000000..9732deb
 +- Whether travel-plan invalidation on `remove_path()` handles both onboard removed passengers and station passengers whose plan references the removed path.
 +- Whether loop routing now matches loop metro movement.
 +- Whether test changes remove order dependence rather than hiding it.
-+- Whether docs and review artifacts are accurate after the move to `docs/reviews/`.
++- Whether docs and review artifacts are accurate after the move to `docs/threads/done/`.
 +
 +Validation already run locally:
 +- `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v` passed, 173 tests.
@@ -1966,15 +1966,15 @@ index 0000000..9732deb
 +- For each finding, include severity, file path, tight line range, explanation, and concrete suggested direction.
 +- If no real issues remain, say that directly.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/2/prompt-codex-3.md b/docs/reviews/full/2026-04-28/2/prompt-codex-3.md
+diff --git a/docs/threads/done/full/2026-04-28/2/prompt-codex-3.md b/docs/threads/done/full/2026-04-28/2/prompt-codex-3.md
 new file mode 100644
 index 0000000..71d40d1
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/prompt-codex-3.md
++++ b/docs/threads/done/full/2026-04-28/2/prompt-codex-3.md
 @@ -0,0 +1,29 @@
 +You are an independent senior code reviewer re-reviewing fixes for a Python 3.13 pygame-ce project. This is a fallback review because Claude is quota-limited; do your own inspection and do not assume the other Codex reviewers' conclusions.
 +
-+Scope: verify the current working-tree diff in `docs/reviews/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/reviews/full/2026-04-28/1/REVIEW.md`.
++Scope: verify the current working-tree diff in `docs/threads/done/full/2026-04-28/2/diff.md` against the prior full-codebase review summary in `docs/threads/done/full/2026-04-28/1/REVIEW.md`.
 +
 +Focus areas:
 +- Correctness of terminal game-over no-op behavior in the programmatic environment.
@@ -1983,7 +1983,7 @@ index 0000000..71d40d1
 +- Cleanup/invalidation of `travel_plans` on line removal.
 +- Python equality/hash contract for graph nodes.
 +- Test reliability changes, especially use of real surfaces/mocked draw and deterministic route-compression setup.
-+- Process/docs accuracy, including `docs/reviews/` and the Ruff pre-commit hook update.
++- Process/docs accuracy, including `docs/threads/done/` and the Ruff pre-commit hook update.
 +
 +Validation already run locally:
 +- `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v` passed, 173 tests.
@@ -2001,11 +2001,11 @@ index 0000000..71d40d1
 +- For each finding, include severity, file path, tight line range, explanation, and concrete suggested direction.
 +- If no real issues remain, say that directly.
 +- Do not provide patches.
-diff --git a/docs/reviews/full/2026-04-28/2/raw/codex-1.md b/docs/reviews/full/2026-04-28/2/raw/codex-1.md
+diff --git a/docs/threads/done/full/2026-04-28/2/raw/codex-1.md b/docs/threads/done/full/2026-04-28/2/raw/codex-1.md
 new file mode 100644
 index 0000000..616a4aa
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/raw/codex-1.md
++++ b/docs/threads/done/full/2026-04-28/2/raw/codex-1.md
 @@ -0,0 +1,11 @@
 +Findings:
 +
@@ -2017,12 +2017,12 @@ index 0000000..616a4aa
 +   Malformed action schemas can still report success. `loop` is coerced with `bool(...)`, so payloads like `{"type": "create_path", "stations": [0, 1], "loop": "yes"}` mutate state instead of being rejected. Also, a dict with missing/`None` type is treated as a successful noop, even though the documented valid no-op inputs are `None` action or `{"type": "noop"}`.
 +   Suggested direction: validate `loop` as an actual `bool` when present, and reject dict actions whose `"type"` is absent or `None` unless the intended public contract is updated and documented.
 +
-+I did not find remaining important issues in the other accepted fixes during static inspection: game-over no-op handling, aborted path creation return value, loop closing edge routing, path-removal travel-plan cleanup, test import ordering, Ruff hook pin, and `docs/reviews/` path updates otherwise look addressed. I did not rerun tests because this was a read-only re-review and the provided validation already passed.
-diff --git a/docs/reviews/full/2026-04-28/2/raw/codex-2.md b/docs/reviews/full/2026-04-28/2/raw/codex-2.md
++I did not find remaining important issues in the other accepted fixes during static inspection: game-over no-op handling, aborted path creation return value, loop closing edge routing, path-removal travel-plan cleanup, test import ordering, Ruff hook pin, and `docs/threads/done/` path updates otherwise look addressed. I did not rerun tests because this was a read-only re-review and the provided validation already passed.
+diff --git a/docs/threads/done/full/2026-04-28/2/raw/codex-2.md b/docs/threads/done/full/2026-04-28/2/raw/codex-2.md
 new file mode 100644
 index 0000000..919dfe3
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/raw/codex-2.md
++++ b/docs/threads/done/full/2026-04-28/2/raw/codex-2.md
 @@ -0,0 +1,7 @@
 +**Findings**
 +
@@ -2031,11 +2031,11 @@ index 0000000..919dfe3
 +   Suggested direction: only normalize `None` to `noop` in `MiniMetroEnv.step()`, require `action["type"]` to be a known string in `Mediator.apply_action()`, and require `loop` to be absent or an actual `bool` before calling `create_path_from_station_indices()`.
 +
 +No other important issues stood out in the inspected fixes. Terminal game-over freezing, removed-path cleanup for deleted onboard passengers and waiting-passenger plans, loop graph closure, the node hash fix, docs path updates, and the deterministic test rewrite all look directionally correct. I did not modify files.
-diff --git a/docs/reviews/full/2026-04-28/2/raw/codex-3.md b/docs/reviews/full/2026-04-28/2/raw/codex-3.md
+diff --git a/docs/threads/done/full/2026-04-28/2/raw/codex-3.md b/docs/threads/done/full/2026-04-28/2/raw/codex-3.md
 new file mode 100644
 index 0000000..f0f2d60
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/raw/codex-3.md
++++ b/docs/threads/done/full/2026-04-28/2/raw/codex-3.md
 @@ -0,0 +1,19 @@
 +**Findings**
 +
@@ -2044,7 +2044,7 @@ index 0000000..f0f2d60
 +   Suggested direction: when `loop=True`, include every requested station after the first, then close to the first station; add an env-level regression for `[0, 1, 2]` producing a loop with all three stations.
 +
 +2. Medium: [src/mediator.py](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:604) lines 604-623, also lines 476-512
-+   Public action validation is still incomplete. `loop` is coerced with `bool(...)`, so non-bool payloads like `"False"` are accepted and can mutate state. `isinstance(value, int)` also accepts booleans, so `path_index=False` can remove path `0`, and boolean station indices can create paths. That violates the documented “malformed actions are rejected without mutating game state” contract.
++   Public action validation is still incomplete. `loop` is coerced with `bool(...)`, so non-bool payloads like `"False"` are accepted and can mutate state. `isinstance(value, int)` also accepts booleans, so `path_index=False` can remove path `0`, and boolean station indices can create paths. That violates the documented �malformed actions are rejected without mutating game state� contract.
 +   Suggested direction: validate with strict types before dispatch: `type(loop) is bool` when present, `type(idx) is int` for indices, and reject missing/`None` action types except the outer `env.step(None)` conversion to noop. Add no-mutation tests for those cases.
 +
 +3. Medium: [src/mediator.py](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:447) lines 447-460, and [src/mediator.py](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:1089) lines 1089-1093
@@ -2056,27 +2056,27 @@ index 0000000..f0f2d60
 +   Suggested direction: patch `pygame.draw` or specific draw functions with `addCleanup()`/context managers, and avoid leaking the mock outside each test.
 +
 +The terminal game-over no-op, direct graph loop closure, node hash/equality fix, docs path updates, and Ruff hook pin looked directionally sound in the inspected code. I did not rerun the full suite.
-diff --git a/docs/reviews/full/2026-04-28/2/raw/opus.md b/docs/reviews/full/2026-04-28/2/raw/opus.md
+diff --git a/docs/threads/done/full/2026-04-28/2/raw/opus.md b/docs/threads/done/full/2026-04-28/2/raw/opus.md
 new file mode 100644
 index 0000000..aeee3d0
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/raw/opus.md
++++ b/docs/threads/done/full/2026-04-28/2/raw/opus.md
 @@ -0,0 +1 @@
-+You've hit your limit · resets 7pm (America/Los_Angeles)
-diff --git a/docs/reviews/full/2026-04-28/2/reviewer-pids.tsv b/docs/reviews/full/2026-04-28/2/reviewer-pids.tsv
++You've hit your limit � resets 7pm (America/Los_Angeles)
+diff --git a/docs/threads/done/full/2026-04-28/2/reviewer-pids.tsv b/docs/threads/done/full/2026-04-28/2/reviewer-pids.tsv
 new file mode 100644
 index 0000000..9d4c849
 --- /dev/null
-+++ b/docs/reviews/full/2026-04-28/2/reviewer-pids.tsv
++++ b/docs/threads/done/full/2026-04-28/2/reviewer-pids.tsv
 @@ -0,0 +1,4 @@
 +codex-1	47676
 +codex-2	25016
 +opus	16876
 +codex-3	7492
-diff --git a/reviews/README.md b/reviews/README.md
+diff --git a/docs/threads/README.md b/docs/threads/README.md
 deleted file mode 100644
 index d5d2eef..0000000
---- a/reviews/README.md
+--- a/docs/threads/README.md
 +++ /dev/null
 @@ -1,16 +0,0 @@
 -# Reviews
@@ -2086,7 +2086,7 @@ index d5d2eef..0000000
 -Use this layout:
 -
 -```text
--reviews/<scope>/<YYYY-MM-DD>/<iteration>/
+-docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/
 -|- raw/
 -|  |- codex.md
 -|  \- opus.md
diff --git a/docs/threads/done/full/2026-04-28/3/prompt-claude.md b/docs/threads/done/full/2026-04-28/3/prompt-claude.md
index 3d2ab45..8be8a3c 100644
--- a/docs/threads/done/full/2026-04-28/3/prompt-claude.md
+++ b/docs/threads/done/full/2026-04-28/3/prompt-claude.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer verifying iteration-2 fixes for a Python 3.13 pygame-ce project.

-Scope: inspect the current working-tree diff in `docs/reviews/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/reviews/full/2026-04-28/2/REVIEW.md`.
+Scope: inspect the current working-tree diff in `docs/threads/done/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/threads/done/full/2026-04-28/2/REVIEW.md`.

 Verify strict malformed-action rejection/no mutation, complete programmatic loop station inclusion, onboard-passenger replan behavior after removing a downstream line, test mock cleanup, and docs/review artifact consistency.

diff --git a/docs/threads/done/full/2026-04-28/3/prompt-codex-1.md b/docs/threads/done/full/2026-04-28/3/prompt-codex-1.md
index 599ce5f..1c04289 100644
--- a/docs/threads/done/full/2026-04-28/3/prompt-codex-1.md
+++ b/docs/threads/done/full/2026-04-28/3/prompt-codex-1.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer verifying iteration-2 fixes for a Python 3.13 pygame-ce project.

-Scope: inspect the current working-tree diff in `docs/reviews/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/reviews/full/2026-04-28/2/REVIEW.md`.
+Scope: inspect the current working-tree diff in `docs/threads/done/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/threads/done/full/2026-04-28/2/REVIEW.md`.

 Verify that:
 - Rejected malformed actions do not advance time or mutate state.
diff --git a/docs/threads/done/full/2026-04-28/3/prompt-codex-2.md b/docs/threads/done/full/2026-04-28/3/prompt-codex-2.md
index 68d5a3c..efb7e07 100644
--- a/docs/threads/done/full/2026-04-28/3/prompt-codex-2.md
+++ b/docs/threads/done/full/2026-04-28/3/prompt-codex-2.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer verifying iteration-2 fixes for a Python 3.13 pygame-ce project. Do your own inspection rather than echoing other reviewers.

-Scope: inspect the current working-tree diff in `docs/reviews/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/reviews/full/2026-04-28/2/REVIEW.md`.
+Scope: inspect the current working-tree diff in `docs/threads/done/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/threads/done/full/2026-04-28/2/REVIEW.md`.

 Review checklist:
 - API contract: invalid actions return `action_ok=False` and do not tick time.
@@ -8,7 +8,7 @@ Review checklist:
 - Loop creation: programmatic loop paths preserve all requested stations.
 - Removal cleanup: waiting plans using removed paths are recomputed, removed passengers are cleaned up, onboard passengers on surviving lines can still transfer and then replan.
 - Tests: no global mock leakage or order dependence introduced by the test fixes.
-- Process docs: `docs/reviews/` layout, Ruff hook pin, and full-review artifacts are internally consistent.
+- Process docs: `docs/threads/done/` layout, Ruff hook pin, and full-review artifacts are internally consistent.

 Validation already run locally after the iteration-2 fixes:
 - Full unittest passed, 174 tests.
diff --git a/docs/threads/done/full/2026-04-28/3/prompt-codex-3.md b/docs/threads/done/full/2026-04-28/3/prompt-codex-3.md
index b9493f0..79210f8 100644
--- a/docs/threads/done/full/2026-04-28/3/prompt-codex-3.md
+++ b/docs/threads/done/full/2026-04-28/3/prompt-codex-3.md
@@ -1,6 +1,6 @@
 You are an independent senior code reviewer verifying iteration-2 fixes for a Python 3.13 pygame-ce project. This is a fallback review because Claude is quota-limited; do your own inspection.

-Scope: inspect the current working-tree diff in `docs/reviews/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/reviews/full/2026-04-28/2/REVIEW.md`.
+Scope: inspect the current working-tree diff in `docs/threads/done/full/2026-04-28/3/diff.md`, with emphasis on the iteration-2 findings summarized in `docs/threads/done/full/2026-04-28/2/REVIEW.md`.

 Check for real bugs only:
 - Rejected malformed actions must not advance time or mutate state.
@@ -8,7 +8,7 @@ Check for real bugs only:
 - Programmatic loops must include every requested station before closing.
 - Removed downstream lines must not strand onboard passengers on surviving metros.
 - Test mock cleanup must not leak global pygame draw/font state.
-- Docs and review artifacts must match the final behavior and `docs/reviews/` layout.
+- Docs and review artifacts must match the final behavior and `docs/threads/done/` layout.

 Validation already run locally after the iteration-2 fixes:
 - Full unittest passed, 174 tests.
diff --git a/docs/threads/done/full/2026-04-28/3/raw/codex-1.md b/docs/threads/done/full/2026-04-28/3/raw/codex-1.md
index 2a9fe77..0439d5f 100644
--- a/docs/threads/done/full/2026-04-28/3/raw/codex-1.md
+++ b/docs/threads/done/full/2026-04-28/3/raw/codex-1.md
@@ -1,6 +1,6 @@
 **Findings**

-- Low: `pygame.draw` mocks still leak in some tests. The path-button test at [test/test_coverage_utils.py](C:/Users/38909/Documents/github/python_mini_metro/test/test_coverage_utils.py:120) assigns `pygame.draw.circle = MagicMock()` directly with no cleanup, and similar direct assignments remain in geometry/path/station tests. That means the artifact claim in [docs/reviews/full/2026-04-28/2/REVIEW.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/2/REVIEW.md:39) that path-button font/draw tests use scoped patches is not fully accurate.
+- Low: `pygame.draw` mocks still leak in some tests. The path-button test at [test/test_coverage_utils.py](C:/Users/38909/Documents/github/python_mini_metro/test/test_coverage_utils.py:120) assigns `pygame.draw.circle = MagicMock()` directly with no cleanup, and similar direct assignments remain in geometry/path/station tests. That means the artifact claim in [docs/threads/done/full/2026-04-28/2/REVIEW.md](C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/full/2026-04-28/2/REVIEW.md:39) that path-button font/draw tests use scoped patches is not fully accurate.

 - Low: [GAME_RULES.md](C:/Users/38909/Documents/github/python_mini_metro/GAME_RULES.md:62) says removing a line invalidates any travel plan that used it. The final code intentionally preserves onboard passenger plans when `next_path` is a surviving line, then replans after transfer, so the doc overstates the behavior.

diff --git a/docs/threads/done/full/2026-04-28/3/raw/codex-2.md b/docs/threads/done/full/2026-04-28/3/raw/codex-2.md
index 5d33778..fcf0471 100644
--- a/docs/threads/done/full/2026-04-28/3/raw/codex-2.md
+++ b/docs/threads/done/full/2026-04-28/3/raw/codex-2.md
@@ -1,5 +1,5 @@
 **Finding**

-Low: [reviewer-pids.tsv](</C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/2/reviewer-pids.tsv:1>) is a transient local process file in the iteration-2 review artifact set. The documented review layout covers raw reviewer output/logs, prompts for full reviews, `diff.md`, and `REVIEW.md`; stale local PIDs are not review evidence and make the artifact directory less internally consistent.
+Low: [reviewer-pids.tsv](</C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/full/2026-04-28/2/reviewer-pids.tsv:1>) is a transient local process file in the iteration-2 review artifact set. The documented review layout covers raw reviewer output/logs, prompts for full reviews, `diff.md`, and `REVIEW.md`; stale local PIDs are not review evidence and make the artifact directory less internally consistent.

 I found no important remaining issues in the iteration-2 code fixes: rejected actions no longer tick time, schema checks are strict where required, loop creation preserves requested stations, removal cleanup handles waiting/onboard cases, and the new `pygame.draw` cleanup in the changed tests is scoped. I did not rerun validation; I reviewed statically against the provided passing validation.
diff --git a/docs/threads/done/full/2026-04-28/3/raw/codex-3.md b/docs/threads/done/full/2026-04-28/3/raw/codex-3.md
index cab2132..1647cfa 100644
--- a/docs/threads/done/full/2026-04-28/3/raw/codex-3.md
+++ b/docs/threads/done/full/2026-04-28/3/raw/codex-3.md
@@ -1,6 +1,6 @@
 **Findings**

-- Low: [test/test_coverage_utils.py](C:/Users/38909/Documents/github/python_mini_metro/test/test_coverage_utils.py:120) still assigns `pygame.draw.circle = MagicMock()` directly in `test_path_button_draws_cross_when_visible` with no cleanup. `TestCoverageUtils.setUp()` does not restore `pygame.draw.circle`, so this can leak global pygame draw state into later tests. This also makes [docs/reviews/full/2026-04-28/2/REVIEW.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/2/REVIEW.md:39) slightly inaccurate when it says the path-button font/draw tests use scoped patches.
+- Low: [test/test_coverage_utils.py](C:/Users/38909/Documents/github/python_mini_metro/test/test_coverage_utils.py:120) still assigns `pygame.draw.circle = MagicMock()` directly in `test_path_button_draws_cross_when_visible` with no cleanup. `TestCoverageUtils.setUp()` does not restore `pygame.draw.circle`, so this can leak global pygame draw state into later tests. This also makes [docs/threads/done/full/2026-04-28/2/REVIEW.md](C:/Users/38909/Documents/github/python_mini_metro/docs/threads/done/full/2026-04-28/2/REVIEW.md:39) slightly inaccurate when it says the path-button font/draw tests use scoped patches.

 I did not find remaining important issues in the runtime fixes: rejected actions no longer advance time, the listed schema checks are enforced, programmatic loops include requested stations before closing, and removed downstream lines no longer strand onboard passengers on surviving metros.
