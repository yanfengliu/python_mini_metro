diff --git a/.pre-commit-config.yaml b/.pre-commit-config.yaml
index 9407181..a6514f4 100644
--- a/.pre-commit-config.yaml
+++ b/.pre-commit-config.yaml
@@ -6,7 +6,7 @@ repos:
       - id: end-of-file-fixer
       - id: trailing-whitespace
   - repo: https://github.com/astral-sh/ruff-pre-commit
-    rev: v0.4.2
+    rev: v0.15.12
     hooks:
       - id: ruff
         args: [--fix, --exit-non-zero-on-fix]
diff --git a/AGENTS.md b/AGENTS.md
index bf60f17..05556a3 100644
--- a/AGENTS.md
+++ b/AGENTS.md
@@ -36,7 +36,7 @@
 - `ARCHITECTURE.md`: current file structure and architectural boundaries.
 - `GAME_RULES.md`: implementation-aligned game mechanics and controls.
 - `PROGRESS.md`: single running project log.
-- `reviews/`: multi-CLI review artifacts for substantive changes.
+- `docs/reviews/`: multi-CLI review artifacts for substantive changes and full-codebase audits.

 ## Validation Gates

@@ -66,13 +66,14 @@
 - Review is required for changes to files such as `AGENTS.md`, `CLAUDE.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `.github/workflows/*`, `.pre-commit-config.yaml`, `pyproject.toml`, `environment.yml`, and any new review-process docs.
 - Review is also required for game-mechanic changes in `src/`, public API changes in `src/env.py` or `src/mediator.py`, balance/config changes in `src/config.py`, and new architectural boundaries.
 - Trivial typo fixes, status summaries, dependency inspection, simple setup commands, and README wording polish can skip review if they do not change behavior or process.
-- Store review artifacts under `reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
+- Store review artifacts under `docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/`:
   - `raw/codex.md`
   - `raw/opus.md`
+  - optional extra independent reviewers as `raw/codex-2.md`, `raw/opus-2.md`, etc.
   - optional `raw/*.stdout.log` and `raw/*.stderr.log`
   - `diff.md`
   - `REVIEW.md`
-- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md reviews/README.md`.
+- Use path-limited diffs from `main`, for example `git diff -- AGENTS.md ARCHITECTURE.md docs/reviews/README.md`.
 - Reviewer prompt baseline:

 ```text
@@ -82,6 +83,26 @@ You are a senior code reviewer. Flag bugs, process regressions, stale documentat
 - Enrich the prompt with task intent, files changed, validation performed, known baseline failures, and prior-review findings when iterating.
 - If one CLI is unavailable because of quota, model rejection, or harness failure, proceed with the available reviewer and record the unavailable CLI in `REVIEW.md`.

+## Full-Codebase Review
+
+- Full-codebase review iterations live under `docs/reviews/full/<YYYY-MM-DD>/<iteration>/`.
+- Before starting a new iteration, inspect existing numeric iteration folders for the same date and use the next number. If earlier iterations exist, give reviewers the previous `REVIEW.md` summaries and ask them to verify that earlier findings were resolved.
+- Run three independent reviewers. Use both Codex and Claude when available; if one service is unavailable or out of quota, run additional independent instances of the available service until there are three raw reports.
+- Codex full-codebase reviewer command. Keep the prompt in a file and pipe it through stdin; this avoids PowerShell splitting multi-line prompts into unexpected positional arguments. Use `--ignore-user-config` so local plugin sync or user config does not interfere with a read-only review run:
+
+```powershell
+Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-codex-1.md | codex -m gpt-5.5 -c model_reasoning_effort='xhigh' -a never -s read-only exec --ignore-user-config --cd . --ephemeral -o docs/reviews/full/<YYYY-MM-DD>/<iteration>/raw/codex-1.md -
+```
+
+- Claude full-codebase reviewer command. Keep the prompt in a variable so PowerShell passes it as one argument:
+
+```powershell
+$prompt = Get-Content -Raw docs/reviews/full/<YYYY-MM-DD>/<iteration>/prompt-claude.md
+claude -p $prompt --model best --effort max --permission-mode bypassPermissions --no-session-persistence --tools "Read,Glob,Grep,Bash" --allowedTools "Read,Glob,Grep,Bash(git *),Bash(python -m unittest *),Bash(C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest *)" --output-format text
+```
+
+- Save raw reviewer output under `raw/`, then synthesize `REVIEW.md` with severity, evidence, disposition, and a fix plan. Only fix findings after checking them against the codebase. Re-review fixes in the next iteration if code changes are made.
+
 ## Visual Changes

 - For visual changes, capture before/after evidence when feasible.
diff --git a/ARCHITECTURE.md b/ARCHITECTURE.md
index a6b66ef..1a196c5 100644
--- a/ARCHITECTURE.md
+++ b/ARCHITECTURE.md
@@ -4,8 +4,11 @@ python_mini_metro/
 |     \- test.yml
 |- .vscode/
 |  \- settings.json
-|- reviews/
-|  \- README.md
+|- docs/
+|  \- reviews/
+|     |- README.md
+|     |- agents-repo-fit/
+|     \- full/
 |- src/
 |  |- agent_play.py
 |  |- config.py
diff --git a/GAME_RULES.md b/GAME_RULES.md
index a536617..e5bdb87 100644
--- a/GAME_RULES.md
+++ b/GAME_RULES.md
@@ -56,9 +56,10 @@ This document summarizes the game rules currently implemented in code.

 - Passengers compute travel plans based on currently available, completed lines.
 - Routing is shortest-hop style (BFS over the station graph).
+- Looped lines include the closing segment between their last and first stations in routing, matching metro movement.
 - If multiple stations match a destination shape, the game uses one with a valid route.
 - Passengers can transfer between lines at stations according to their travel plan.
-- If no route exists, passengers wait until the network changes.
+- If no route exists, passengers wait until the network changes. Removing a line invalidates any travel plans that used it.

 ## Timing and Spawning

@@ -74,6 +75,7 @@ This document summarizes the game rules currently implemented in code.
 - Game over occurs when 1 or more passengers are over-waiting.
 - On game over:
   - Simulation time and gameplay updates stop.
+  - Programmatic `step(...)` calls become stable no-ops until reset.
   - A game-over overlay appears with final score.

 ## Controls
@@ -97,3 +99,4 @@ This document summarizes the game rules currently implemented in code.
 - `pause`: pause simulation.
 - `resume`: resume simulation.
 - `noop` (or `None`): do nothing this step.
+- Malformed actions are rejected without mutating game state.
diff --git a/PROGRESS.md b/PROGRESS.md
index b3879b3..484a2fd 100644
--- a/PROGRESS.md
+++ b/PROGRESS.md
@@ -80,4 +80,6 @@

 ## 2026-04-28

-- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added a `reviews/` artifact directory.
+- Added Python/py313 workflow guidance in `AGENTS.md` with a `CLAUDE.md` shim, reflected the removed `.cursor/rules`, and added an initial review artifact directory.
+- Moved review artifacts under `docs/reviews/` and documented robust full-codebase Codex/Claude review commands.
+- Ran the first full-codebase review, fixed terminal-state API mutation, malformed action handling, loop routing closure, stale travel-plan cleanup, the graph node hash contract, and the stale Ruff pre-commit hook, then added focused regressions.
diff --git a/README.md b/README.md
index b1f450f..dbd1d90 100644
--- a/README.md
+++ b/README.md
@@ -46,6 +46,7 @@ obs, reward, done, info = env.step({"type": "remove_path", "path_index": 0})
     - `reward` (`int`): score delta since previous step
     - `done` (`bool`): `True` when game is over
     - `info` (`dict`): currently contains `{"action_ok": bool}`
+  - Once `done` is `True`, later `step(...)` calls are stable no-ops: actions are rejected, time does not advance, and `info["action_ok"]` is `False` until `reset(...)`.

 ### Valid `action` inputs
 - `None`
@@ -62,7 +63,7 @@ obs, reward, done, info = env.step({"type": "remove_path", "path_index": 0})
 - `{"type": "remove_path", "path_index": k}`
   - Removes an existing path by index.
   - Valid only when `0 <= k < len(observation["structured"]["paths"])`.
-- `{"type": "remove_path", "path_id": "..."}`
+- `{"type": "remove_path", "path_id": "..."}`
   - Removes an existing path by path id string from `observation["structured"]["paths"][*]["id"]`.
 - `{"type": "buy_line"}`
   - Buys the next locked line if affordable.
@@ -82,6 +83,7 @@ Any unknown `type`, or malformed action payload, returns `info["action_ok"] == F
 - `dt_ms` argument to `step(...)` overrides constructor `dt_ms` for that call.
 - If effective `dt_ms` is an integer, simulation advances by that many milliseconds.
 - If effective `dt_ms` is `None`, action is applied but time is not advanced.
+- If the environment is already game-over, no simulation time advances regardless of `dt_ms`.

 ### Observation shape
 `observation` is:
diff --git a/docs/reviews/README.md b/docs/reviews/README.md
new file mode 100644
index 0000000..531bdd2
--- /dev/null
+++ b/docs/reviews/README.md
@@ -0,0 +1,17 @@
+# Reviews
+
+This directory stores multi-CLI review artifacts for substantive behavior, API, architecture, config, workflow, process-documentation changes, and full-codebase audits.
+
+Use this layout:
+
+```text
+docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/
+|- raw/
+|  |- codex-1.md
+|  |- opus.md
+|  \- codex-2.md
+|- diff.md
+\- REVIEW.md
+```
+
+Keep review scope names short and kebab-case, such as `agents-repo-fit`, `full`, or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
diff --git a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
similarity index 70%
rename from reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
rename to docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
index 6594514..3ede47b 100644
--- a/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
+++ b/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md
@@ -3,15 +3,15 @@
 ## Scope

 - Rewrote `AGENTS.md` from a copied workflow template into a Python/py313 workflow for this repo.
-- Added `reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
-- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `reviews/`.
+- Added `docs/reviews/README.md` so the review artifact directory referenced by `AGENTS.md` exists in the repo.
+- Updated `ARCHITECTURE.md` after the user removed `.cursor/rules` and this change added `docs/reviews/`.
 - Updated `PROGRESS.md` with a short entry for the process-documentation change.

 ## Validation

 - `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`: passed, 167 tests.
-- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1/diff.md reviews/agents-repo-fit/2026-04-28/1/REVIEW.md reviews/agents-repo-fit/2026-04-28/1/raw/codex.md reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
-- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md reviews/README.md reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.
+- `C:\Users\38909\miniconda3\envs\py313\python.exe -m pre_commit run --files AGENTS.md ARCHITECTURE.md CLAUDE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1/diff.md docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md`: passed after adding a final newline to `CLAUDE.md`.
+- `git diff --check -- AGENTS.md ARCHITECTURE.md PROGRESS.md docs/reviews/README.md docs/reviews/agents-repo-fit/2026-04-28/1`: passed, with expected CRLF warnings only.

 ## Codex Findings

@@ -21,7 +21,7 @@
 ## Claude Findings

 - P2: `PROGRESS.md` and the review artifact path use `2026-04-28`, while the reviewer inferred April 27, 2026 from local session context. Disposition: not accepted for the same reason as the Codex date finding.
-- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `reviews/`.
+- P2: The `PROGRESS.md` bullet under-described the actual process change. Disposition: accepted. The bullet now names `AGENTS.md`, `CLAUDE.md`, the removed `.cursor/rules`, and `docs/reviews/`.
 - P3: The review packet should include the `.cursor/rules` deletion and `CLAUDE.md` addition. Disposition: accepted. `diff.md` was regenerated with those paths included.

 ## Result
diff --git a/reviews/agents-repo-fit/2026-04-28/1/diff.md b/docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
similarity index 100%
rename from reviews/agents-repo-fit/2026-04-28/1/diff.md
rename to docs/reviews/agents-repo-fit/2026-04-28/1/diff.md
diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
similarity index 100%
rename from reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/codex.md
diff --git a/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md b/docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
similarity index 100%
rename from reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
rename to docs/reviews/agents-repo-fit/2026-04-28/1/raw/opus.md
diff --git a/docs/reviews/full/2026-04-28/1/REVIEW.md b/docs/reviews/full/2026-04-28/1/REVIEW.md
new file mode 100644
index 0000000..0160cb6
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/REVIEW.md
@@ -0,0 +1,65 @@
+# Full-Codebase Review: Iteration 1
+
+## Reviewer Coverage
+
+- Claude Opus was attempted with highest effort, but the CLI returned a quota-limit message: `You've hit your limit · resets 7pm (America/Los_Angeles)`. The raw failure is preserved in `raw/opus.md`.
+- Per the fallback rule, three independent Codex reviewers were run with `gpt-5.5` and `xhigh` reasoning. Raw outputs are preserved in `raw/codex-1.md`, `raw/codex-2.md`, and `raw/codex-3.md`.
+- The Codex read-only sandbox blocked direct test execution inside the reviewer subprocesses, so reviewer validation was static. Local verification will run outside the reviewer sandbox before completion.
+
+## Confirmed Findings
+
+### High: programmatic steps mutate state after game over
+
+- Reported by: Codex 1, Codex 2, Codex 3.
+- Evidence: `MiniMetroEnv.step()` always calls `mediator.apply_action()` and `mediator.step_time()`; `Mediator.increment_time()` only checks pause state. `GAME_RULES.md` says simulation time and gameplay updates stop on game over.
+- Disposition: accepted. Freeze programmatic time progression after `is_game_over`, and cover repeated `step()` calls after `done=True`.
+
+### Medium: malformed public actions can raise or report false success
+
+- Reported by: Codex 1, Codex 2, Codex 3.
+- Evidence: `Mediator.apply_action()` assumes `action` is a dict; `create_path_from_station_indices()` assumes a list of ints; `remove_path_by_index()` compares unvalidated values; aborted programmatic path creation returns `self.paths[-1]`, which can be an existing path.
+- Disposition: accepted. Validate action schemas before dispatch and return a newly completed path only when creation actually succeeds.
+
+### Medium: looped-line routing omits the closing edge
+
+- Reported by: Codex 1, Codex 3.
+- Evidence: `Path.update_segments()` creates a last-to-first segment when looped, but `build_station_nodes_dict()` only connects adjacent entries in `path.stations`.
+- Disposition: accepted. Add the last-to-first neighbor relationship for completed looped paths and cover it in graph tests.
+
+### Medium: path removal leaves stale travel plans
+
+- Reported by: Codex 2, Codex 3.
+- Evidence: `remove_path()` removes metros and onboard passengers from global lists, but leaves removed passengers in `travel_plans` and does not clear waiting-passenger plans that reference the removed path.
+- Disposition: accepted. Remove plans for deleted passengers and invalidate/recompute plans that reference the removed path.
+
+### Medium: `Node` equality and hash disagree
+
+- Reported by: Codex 3.
+- Evidence: `Node.__eq__` compares by station, while `Node.__hash__` hashes the node id. Nodes are stored in sets, so equal nodes must have equal hashes.
+- Disposition: accepted. Hash by the same station identity used for equality and cover set behavior.
+
+### Low: moved historical review artifact still mentions old `reviews/` path
+
+- Reported by: Codex 2.
+- Evidence: `docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md` describes adding `reviews/README.md` and validating `reviews/...` paths after the artifact was moved under `docs/reviews/`.
+- Disposition: accepted. Update the moved artifact so it remains accurate after the docs-path change.
+
+### Low: two tests mutate `sys.path` after project imports
+
+- Reported by: Codex 2.
+- Evidence: `test/test_graph.py` and `test/test_mediator.py` import project modules before appending `../src`.
+- Disposition: accepted. Move the path setup before project imports.
+
+### Low: pinned Ruff pre-commit hook cannot parse `py313`
+
+- Reported by: local validation after applying fixes.
+- Evidence: `pre-commit run --files ...` failed because `astral-sh/ruff-pre-commit` at `v0.4.2` does not recognize `target-version = "py313"` in `pyproject.toml`, while the active local Ruff is `0.15.12`.
+- Disposition: accepted. Update the Ruff pre-commit hook pin to `v0.15.12`, matching the local Ruff version and current upstream tag.
+
+## Deferred Finding
+
+### Medium: coarse `dt_ms` is not equivalent to repeated small ticks
+
+- Reported by: Codex 1 only.
+- Evidence: metro movement consumes at most one segment endpoint per call and spawn counters are step-based.
+- Disposition: deferred. This is a broader simulation-contract decision rather than a narrow defect fix. It should be handled in a separate task that decides whether `dt_ms` is a frame-sized tick contract or whether the engine should substep/carry remainders.
diff --git a/docs/reviews/full/2026-04-28/1/diff.md b/docs/reviews/full/2026-04-28/1/diff.md
new file mode 100644
index 0000000..cbb222c
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/diff.md
@@ -0,0 +1,5 @@
+# Full-Codebase Review Diff Context
+
+This was a full-codebase review, not a focused diff review. Reviewers inspected the repository as a whole, including the uncommitted process-documentation changes that moved review artifacts from `reviews/` to `docs/reviews/`.
+
+The active findings are synthesized in `REVIEW.md`; raw reviewer outputs are preserved in `raw/`.
diff --git a/docs/reviews/full/2026-04-28/1/prompt-claude.md b/docs/reviews/full/2026-04-28/1/prompt-claude.md
new file mode 100644
index 0000000..76c3d23
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/prompt-claude.md
@@ -0,0 +1,17 @@
+You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
+
+Scope: inspect the entire repository, including source, tests, docs, configuration, and current uncommitted process-doc changes. There are no prior full-codebase review iterations for this date.
+
+Focus on real, important issues only: design flaws, correctness bugs, gameplay edge cases, public API problems, unclean code, efficiency problems, memory/resource leaks, missing tests, stale docs, and maintainability risks. Do not invent issues and do not nit-pick. If there are no real issues, say so.
+
+Constraints:
+- Do not modify files.
+- Prefer read-only inspection. You may run read-only commands and the test suite if useful.
+- If running tests, prefer `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
+- Consider `AGENTS.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `README.md`, and `PROGRESS.md` as repo context, but verify claims against source.
+
+Output:
+- Findings first, sorted by severity.
+- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
+- Include a short "No issue" statement for areas you checked and found sound only if useful.
+- Do not provide patches.
diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-1.md b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
new file mode 100644
index 0000000..76c3d23
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-1.md
@@ -0,0 +1,17 @@
+You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project.
+
+Scope: inspect the entire repository, including source, tests, docs, configuration, and current uncommitted process-doc changes. There are no prior full-codebase review iterations for this date.
+
+Focus on real, important issues only: design flaws, correctness bugs, gameplay edge cases, public API problems, unclean code, efficiency problems, memory/resource leaks, missing tests, stale docs, and maintainability risks. Do not invent issues and do not nit-pick. If there are no real issues, say so.
+
+Constraints:
+- Do not modify files.
+- Prefer read-only inspection. You may run read-only commands and the test suite if useful.
+- If running tests, prefer `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
+- Consider `AGENTS.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `README.md`, and `PROGRESS.md` as repo context, but verify claims against source.
+
+Output:
+- Findings first, sorted by severity.
+- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
+- Include a short "No issue" statement for areas you checked and found sound only if useful.
+- Do not provide patches.
diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-2.md b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
new file mode 100644
index 0000000..a565f8a
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-2.md
@@ -0,0 +1,23 @@
+You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a separate review from the other reviewers; do your own inspection and do not assume their conclusions.
+
+Scope: inspect the entire repository, including source, tests, docs, configuration, and current uncommitted process-doc changes. There are no prior full-codebase review iterations for this date.
+
+Focus on real, important issues only: design flaws, correctness bugs, gameplay edge cases, public API problems, unclean code, efficiency problems, memory/resource leaks, missing tests, stale docs, and maintainability risks. Do not invent issues and do not nit-pick. If there are no real issues, say so.
+
+Extra attention areas:
+- Programmatic environment/API behavior in `src/env.py`, `src/mediator.py`, and `src/agent_play.py`.
+- Routing/boarding/game-over edge cases.
+- Test gaps where behavior is documented but not protected.
+- Review-process and docs-path consistency after the move to `docs/reviews/`.
+
+Constraints:
+- Do not modify files.
+- Prefer read-only inspection. You may run read-only commands and the test suite if useful.
+- If running tests, prefer `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
+- Consider `AGENTS.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `README.md`, and `PROGRESS.md` as repo context, but verify claims against source.
+
+Output:
+- Findings first, sorted by severity.
+- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
+- Include a short "No issue" statement for areas you checked and found sound only if useful.
+- Do not provide patches.
diff --git a/docs/reviews/full/2026-04-28/1/prompt-codex-3.md b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
new file mode 100644
index 0000000..8886b41
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/prompt-codex-3.md
@@ -0,0 +1,23 @@
+You are an independent senior code reviewer performing a full-codebase review of this Python 3.13 pygame-ce project. This is a fallback review because Claude is currently quota-limited; do your own inspection and do not assume the other reviewers' conclusions.
+
+Scope: inspect the entire repository, including source, tests, docs, configuration, and current uncommitted process-doc changes. There are no prior full-codebase review iterations for this date.
+
+Focus on real, important issues only: design flaws, correctness bugs, gameplay edge cases, public API problems, unclean code, efficiency problems, memory/resource leaks, missing tests, stale docs, and maintainability risks. Do not invent issues and do not nit-pick. If there are no real issues, say so.
+
+Extra attention areas:
+- Domain logic in `src/graph/`, `src/line.py`, `src/metro.py`, and `src/station.py`.
+- Resource/path lifecycle cleanup when lines, trains, passengers, or travel plans are removed.
+- Python equality/hash contracts, mutable shared state, and any edge cases likely to corrupt routing.
+- Review-process and docs-path consistency after the move to `docs/reviews/`.
+
+Constraints:
+- Do not modify files.
+- Prefer read-only inspection. You may run read-only commands and the test suite if useful.
+- If running tests, prefer `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`.
+- Consider `AGENTS.md`, `ARCHITECTURE.md`, `GAME_RULES.md`, `README.md`, and `PROGRESS.md` as repo context, but verify claims against source.
+
+Output:
+- Findings first, sorted by severity.
+- For each finding, include severity, file path, line or tight line range, explanation, and concrete suggested direction.
+- Include a short "No issue" statement for areas you checked and found sound only if useful.
+- Do not provide patches.
diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-1.md b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
new file mode 100644
index 0000000..d4c9407
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/raw/codex-1.md
@@ -0,0 +1,20 @@
+**Findings**
+
+1. High - [src/env.py](C:/Users/38909/Documents/github/python_mini_metro/src/env.py:23):23-38, [src/mediator.py](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:687):687-732
+   Programmatic `env.step()` keeps applying actions and advancing time after `done=True`. `GAME_RULES.md:75-76` says simulation time and gameplay stop on game over, and `main.py` enforces that for manual play, but `MiniMetroEnv.step()` still calls `apply_action()` and `step_time()`. Direction: make post-game-over steps stable, likely no-op except observation/reward bookkeeping, and add an env test for repeated `step()` after `done`.
+
+2. Medium - [README.md](C:/Users/38909/Documents/github/python_mini_metro/README.md:81):81-84, [src/mediator.py](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:691):691-699, [src/entity/path.py](C:/Users/38909/Documents/github/python_mini_metro/src/entity/path.py:161):161-197
+   `dt_ms` is documented as advancing simulation by that many milliseconds, but coarse `dt_ms` is not equivalent to repeated small ticks. Spawn counters advance by one step per call regardless of elapsed milliseconds, and metro movement drops leftover travel after reaching one segment endpoint. Direction: either document `dt_ms` as a frame-sized tick contract, or substep/carry remainders so elapsed-time behavior is consistent.
+
+3. Medium - [README.md](C:/Users/38909/Documents/github/python_mini_metro/README.md:79):79, [src/mediator.py](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:491):491-513, [src/mediator.py](C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:587):587-602
+   The public action contract says malformed payloads return `action_ok=False`, but several malformed inputs can raise instead: non-dict actions, non-list `stations`, non-int station indices, and non-int `remove_path.path_index`. Also, an aborted programmatic path creation can return an existing `self.paths[-1]`, incorrectly reporting success when no new path was created. Direction: validate action schemas before dispatch and have path creation return the newly finished path only if it actually survived.
+
+4. Medium - [src/graph/graph_algo.py](C:/Users/38909/Documents/github/python_mini_metro/src/graph/graph_algo.py:17):17-35, [src/entity/path.py](C:/Users/38909/Documents/github/python_mini_metro/src/entity/path.py:51):51-57
+   Routing ignores the closing edge of looped lines. `Path` creates a last-to-first segment for loops, but `build_station_nodes_dict()` only connects adjacent stations in `path.stations`, so passengers cannot route across the loop closure. Direction: when `path.is_looped`, add neighbors between the last and first nodes and cover it with a BFS/travel-plan test.
+
+5. Low - [docs/reviews/full/2026-04-28/1/raw/opus.md](C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/full/2026-04-28/1/raw/opus.md:1):1, [AGENTS.md](C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88):88-103
+   The current full-review artifact directory is incomplete: it has prompts/logs, `raw/opus.md` contains only a quota message, and there is no `diff.md` or `REVIEW.md`. Direction: before committing those artifacts, either complete the iteration with valid reports and synthesis, or leave these transient failed-run files out of the change set.
+
+No issue found in the dependency/config basics I checked: `requirements.txt`, `environment.yml`, and CI are aligned on the project's current runtime dependencies.
+
+Validation note: I attempted to run the full suite with the requested py313 interpreter and with `python -m unittest -v`, but the harness rejected both command forms before execution, so I could not record a fresh test result.
diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-2.md b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
new file mode 100644
index 0000000..8078f32
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/raw/codex-2.md
@@ -0,0 +1,20 @@
+**Findings**
+
+1. **High** - [src/env.py](<C:/Users/38909/Documents/github/python_mini_metro/src/env.py:23>), [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:687>)
+   Programmatic `env.step()` still advances time/gameplay after `is_game_over` is already true. `GAME_RULES.md:75-76` says simulation time and gameplay updates stop on game over, and `main.py` enforces that for manual play, but `Mediator.increment_time()` only checks pause state. Direction: add a game-over guard to the programmatic time path and cover `step()` after `done=True`.
+
+2. **Medium** - [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:491>), [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:587>)
+   The public action API does not reliably return `action_ok=False` for malformed inputs as documented in `README.md:79`. Examples: non-int `remove_path.path_index` reaches numeric comparison in `remove_path_by_index`; malformed `create_path.stations` can raise during `len()`/index comparisons; and an aborted duplicate-station create can return `self.paths[-1]`, falsely reporting success when another path already exists. Direction: validate action shape/types before dispatch and return the newly created path explicitly, not "last path in list".
+
+3. **Medium** - [src/mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:449>)
+   `remove_path()` removes passengers riding that line from `self.passengers` but leaves their entries in `self.travel_plans`. Repeated create/remove cycles can accumulate stale passenger references and make debugging/routing state misleading. Direction: delete travel-plan entries for every passenger removed with a metro, matching the cleanup already done on delivery.
+
+4. **Low** - [docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/agents-repo-fit/2026-04-28/1/REVIEW.md:6>)
+   The moved review artifact still describes and validates the old `reviews/` path at lines 6-14, while current process docs now require `docs/reviews/`. Direction: either preserve it as explicitly historical or update/regenerate the artifact so review records for the move do not contradict the active process.
+
+5. **Low** - [test/test_graph.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_graph.py:6>), [test/test_mediator.py](<C:/Users/38909/Documents/github/python_mini_metro/test/test_mediator.py:6>)
+   These modules import from `src` before appending `../src` to `sys.path`, so they depend on another test having already mutated `sys.path`. Direction: move the path setup before project imports, or package/import the project consistently.
+
+**Notes**
+
+I found the current top-level `AGENTS.md`, `ARCHITECTURE.md`, `PROGRESS.md`, and `docs/reviews/README.md` mostly consistent with the `docs/reviews/` move aside from the stale moved artifact above. I could not run the unit suite because this read-only harness rejected Python execution, including the requested `python.exe -m unittest -v`, so this review is static.
diff --git a/docs/reviews/full/2026-04-28/1/raw/codex-3.md b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
new file mode 100644
index 0000000..48c47ea
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/raw/codex-3.md
@@ -0,0 +1,27 @@
+**Findings**
+
+1. **High** - [src/mediator.py:687](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:687>), [src/env.py:28](<C:/Users/38909/Documents/github/python_mini_metro/src/env.py:28>)
+   Programmatic play keeps advancing after `is_game_over` is set. `main.py` skips `increment_time()` on game over, but `MiniMetroEnv.step()` always calls `mediator.step_time()`, and `Mediator.increment_time()` only checks pause. This violates `GAME_RULES.md`'s terminal-state rule and can mutate time, trains, spawns, and passenger state after `done=True`.
+   Suggested direction: make `Mediator.increment_time()` return immediately when `is_game_over`, or have `MiniMetroEnv.step()` freeze time/actions once done.
+
+2. **Medium** - [src/graph/graph_algo.py:17](<C:/Users/38909/Documents/github/python_mini_metro/src/graph/graph_algo.py:17>), [src/entity/path.py:51](<C:/Users/38909/Documents/github/python_mini_metro/src/entity/path.py:51>)
+   Looped paths render and move metros over the closing segment, but the routing graph only connects adjacent `path.stations` entries and never adds the last-to-first edge for `path.is_looped`. Routing can overcount loop trips and prefer worse alternatives even though the train can travel directly over the closure.
+   Suggested direction: when building graph connections for completed looped paths, include the closing neighbor relationship.
+
+3. **Medium** - [src/mediator.py:449](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:449>), [src/mediator.py:983](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:983>)
+   `remove_path()` removes metros and onboard passengers but does not clear `travel_plans` for removed passengers or invalidate waiting passengers whose `next_path` points at the removed path. `find_travel_plan_for_passengers()` skips any passenger with a non-`None` `next_path`, so stale removed-path references can persist.
+   Suggested direction: on path removal, delete plans for removed passengers and clear/recompute any plan referencing the removed path.
+
+4. **Medium** - [src/mediator.py:491](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:491>), [src/mediator.py:587](<C:/Users/38909/Documents/github/python_mini_metro/src/mediator.py:587>), [README.md:79](<C:/Users/38909/Documents/github/python_mini_metro/README.md:79>)
+   The public action API promises malformed payloads return `action_ok=False`, but `apply_action()` assumes a dict and `create_path_from_station_indices()` assumes integer indices. Bad payloads can raise `AttributeError`/`TypeError`. Also, if an invalid duplicate path aborts while another path already exists, `return self.paths[-1]` reports success for the previous path.
+   Suggested direction: validate action type, station list type, every index type/range, and return the newly created path object only if creation actually finished.
+
+5. **Medium** - [src/graph/node.py:17](<C:/Users/38909/Documents/github/python_mini_metro/src/graph/node.py:17>)
+   `Node.__eq__` compares by station, but `Node.__hash__` hashes a unique node id. Equal nodes can therefore have different hashes, which breaks Python's set/dict contract. This is risky because nodes are stored in sets (`neighbors`, `paths`) and tests compare fresh `Node(station)` instances as equal.
+   Suggested direction: hash by `station` if equality is station-based, or make equality identity/id-based consistently.
+
+6. **Low** - [AGENTS.md:88](<C:/Users/38909/Documents/github/python_mini_metro/AGENTS.md:88>), [docs/reviews/README.md:8](<C:/Users/38909/Documents/github/python_mini_metro/docs/reviews/README.md:8>)
+   `docs/reviews/full/2026-04-28/1/` currently contains prompts/raw/log files but no required `diff.md` or synthesized `REVIEW.md`. If committed as-is, it conflicts with the documented full-review artifact contract.
+   Suggested direction: complete the iteration before committing, or keep failed/transient run artifacts out of the change set.
+
+Tests were not run: the harness rejected `C:\Users\38909\miniconda3\envs\py313\python.exe -m unittest -v`, `python -m unittest -v`, and the bytecode-disabled variant.
diff --git a/docs/reviews/full/2026-04-28/1/raw/opus.md b/docs/reviews/full/2026-04-28/1/raw/opus.md
new file mode 100644
index 0000000..0799432
--- /dev/null
+++ b/docs/reviews/full/2026-04-28/1/raw/opus.md
@@ -0,0 +1 @@
+You've hit your limit - resets 7pm (America/Los_Angeles)
diff --git a/reviews/README.md b/reviews/README.md
deleted file mode 100644
index d5d2eef..0000000
--- a/reviews/README.md
+++ /dev/null
@@ -1,16 +0,0 @@
-# Reviews
-
-This directory stores multi-CLI review artifacts for substantive behavior, API, architecture, config, workflow, and process-documentation changes.
-
-Use this layout:
-
-```text
-reviews/<scope>/<YYYY-MM-DD>/<iteration>/
-|- raw/
-|  |- codex.md
-|  \- opus.md
-|- diff.md
-\- REVIEW.md
-```
-
-Keep review scope names short and kebab-case, such as `agents-repo-fit` or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
diff --git a/src/env.py b/src/env.py
index 0502fe0..193f88d 100644
--- a/src/env.py
+++ b/src/env.py
@@ -1,5 +1,5 @@
 import random
-from typing import Any, Dict, List, Tuple
+from typing import Any, Dict, Tuple

 import numpy as np

@@ -23,6 +23,12 @@ class MiniMetroEnv:
     def step(
         self, action: Dict[str, Any] | None = None, dt_ms: int | None = None
     ) -> Tuple[Dict[str, Any], int, bool, Dict[str, Any]]:
+        if self.mediator.is_game_over:
+            obs = self.observe()
+            reward = self.mediator.score - self.last_score
+            self.last_score = self.mediator.score
+            return obs, reward, True, {"action_ok": False}
+
         if action is None:
             action = {"type": "noop"}
         action_ok = self.mediator.apply_action(action)
@@ -153,9 +159,7 @@ class MiniMetroEnv:
             dtype=np.int64,
         )
         path_station_indices = [
-            np.array(
-                [station_id_to_index[s.id] for s in path.stations], dtype=np.int64
-            )
+            np.array([station_id_to_index[s.id] for s in path.stations], dtype=np.int64)
             for path in self.mediator.paths
         ]
         path_is_looped = np.array(
@@ -173,10 +177,7 @@ class MiniMetroEnv:
         else:
             metro_positions = np.zeros((0, 2), dtype=np.float32)
         metro_path_indices = np.array(
-            [
-                path_id_to_index.get(metro.path_id, -1)
-                for metro in self.mediator.metros
-            ],
+            [path_id_to_index.get(metro.path_id, -1) for metro in self.mediator.metros],
             dtype=np.int64,
         )

diff --git a/src/graph/graph_algo.py b/src/graph/graph_algo.py
index b68346f..4f6a87c 100644
--- a/src/graph/graph_algo.py
+++ b/src/graph/graph_algo.py
@@ -21,6 +21,8 @@ def build_station_nodes_dict(stations: List[Station], paths: List[Path]):
         for station in path.stations:
             station_nodes_dict[station].paths.add(path)
             connection.append(station_nodes_dict[station])
+        if path.is_looped and len(connection) > 1:
+            connection.append(connection[0])
         connections.append(connection)

     while len(station_nodes) > 0:
diff --git a/src/graph/node.py b/src/graph/node.py
index e1b32a7..5084575 100644
--- a/src/graph/node.py
+++ b/src/graph/node.py
@@ -2,9 +2,10 @@ from __future__ import annotations

 from typing import Set

+from shortuuid import uuid  # type: ignore
+
 from entity.path import Path
 from entity.station import Station
-from shortuuid import uuid  # type: ignore


 class Node:
@@ -18,7 +19,7 @@ class Node:
         return self.station == other.station

     def __hash__(self) -> int:
-        return hash(self.id)
+        return hash(self.station)

     def __repr__(self) -> str:
         return f"Node-{self.station.__repr__()}"
diff --git a/src/mediator.py b/src/mediator.py
index 32c64d6..0f66ff9 100644
--- a/src/mediator.py
+++ b/src/mediator.py
@@ -4,34 +4,35 @@ import random
 from typing import Dict, List

 import pygame
+
 from config import (
     font_name,
-    max_waiting_passengers,
+    game_over_button_border_color,
+    game_over_button_border_width,
+    game_over_button_color,
+    game_over_button_padding_x,
+    game_over_button_padding_y,
+    game_over_button_spacing,
+    game_over_font_size,
+    game_over_hint_font_size,
+    game_over_overlay_color,
+    game_over_text_color,
     initial_num_stations,
+    max_waiting_passengers,
     num_metros,
     num_paths,
-    path_unlock_milestones,
-    station_unlock_milestones,
     num_stations,
     passenger_color,
     passenger_max_wait_time_ms,
     passenger_size,
     passenger_spawning_interval_step,
     passenger_spawning_start_step,
-    game_over_font_size,
-    game_over_hint_font_size,
-    game_over_button_border_color,
-    game_over_button_border_width,
-    game_over_button_color,
-    game_over_button_padding_x,
-    game_over_button_padding_y,
-    game_over_button_spacing,
-    game_over_overlay_color,
-    game_over_text_color,
+    path_unlock_milestones,
     score_display_coords,
     score_font_size,
     screen_height,
     screen_width,
+    station_unlock_milestones,
 )
 from entity.get_entity import get_random_stations
 from entity.metro import Metro
@@ -59,6 +60,8 @@ from ui.speed_button import (
 from utils import get_shape_from_type, hue_to_rgb, pick_distinct_hue

 TravelPlans = Dict[Passenger, TravelPlan]
+
+
 class Mediator:
     def __init__(self) -> None:
         pygame.font.init()
@@ -147,8 +150,7 @@ class Mediator:
         while True:
             stations = get_random_stations(self.num_stations)
             initial_shapes = {
-                station.shape.type
-                for station in stations[: self.initial_num_stations]
+                station.shape.type for station in stations[: self.initial_num_stations]
             }
             if len(initial_shapes) >= 2:
                 return stations
@@ -224,9 +226,7 @@ class Mediator:
         self.update_unlocked_num_paths()
         return True

-    def try_purchase_path_button_by_index(
-        self, button_idx: int | None = None
-    ) -> bool:
+    def try_purchase_path_button_by_index(self, button_idx: int | None = None) -> bool:
         if button_idx is None:
             button_idx = self.get_next_path_button_idx_to_purchase()
         if button_idx is None:
@@ -369,14 +369,12 @@ class Mediator:
     def handle_game_over_click(self, position: Point) -> str | None:
         if not self.is_game_over:
             return None
-        if (
-            self.game_over_restart_rect
-            and self.game_over_restart_rect.collidepoint(position.to_tuple())
+        if self.game_over_restart_rect and self.game_over_restart_rect.collidepoint(
+            position.to_tuple()
         ):
             return "restart"
-        if (
-            self.game_over_exit_rect
-            and self.game_over_exit_rect.collidepoint(position.to_tuple())
+        if self.game_over_exit_rect and self.game_over_exit_rect.collidepoint(
+            position.to_tuple()
         ):
             return "exit"
         return None
@@ -448,15 +446,26 @@ class Mediator:

     def remove_path(self, path: Path) -> None:
         self.path_to_button[path].remove_path()
-        for metro in path.metros:
-            for passenger in metro.passengers:
-                self.passengers.remove(passenger)
-            self.metros.remove(metro)
+        for metro in list(path.metros):
+            for passenger in list(metro.passengers):
+                if passenger in self.passengers:
+                    self.passengers.remove(passenger)
+                self.travel_plans.pop(passenger, None)
+            if metro in self.metros:
+                self.metros.remove(metro)
+        self.invalidate_travel_plans_for_path(path)
         self.release_color_for_path(path)
         self.paths.remove(path)
         self.assign_paths_to_buttons()
         self.find_travel_plan_for_passengers()

+    def invalidate_travel_plans_for_path(self, path: Path) -> None:
+        for passenger, travel_plan in list(self.travel_plans.items()):
+            if travel_plan.next_path == path or any(
+                path in node.paths for node in travel_plan.node_path
+            ):
+                del self.travel_plans[passenger]
+
     def remove_path_by_id(self, path_id: str) -> bool:
         for path in self.paths:
             if path.id == path_id:
@@ -465,6 +474,8 @@ class Mediator:
         return False

     def remove_path_by_index(self, path_index: int) -> bool:
+        if not isinstance(path_index, int):
+            return False
         if 0 <= path_index < len(self.paths):
             self.remove_path(self.paths[path_index])
             return True
@@ -491,15 +502,19 @@ class Mediator:
     def create_path_from_station_indices(
         self, station_indices: List[int], loop: bool = False
     ) -> Path | None:
+        if not isinstance(station_indices, list):
+            return None
         if len(station_indices) < 2 or len(self.paths) >= self.unlocked_num_paths:
             return None
         if any(
-            idx < 0 or idx >= len(self.stations) for idx in station_indices
+            not isinstance(idx, int) or idx < 0 or idx >= len(self.stations)
+            for idx in station_indices
         ):
             return None

         self.start_path_on_station(self.stations[station_indices[0]])
-        if not self.path_being_created:
+        created_path = self.path_being_created
+        if not created_path:
             return None

         for idx in station_indices[1:-1]:
@@ -510,7 +525,9 @@ class Mediator:
         else:
             self.end_path_on_station(self.stations[station_indices[-1]])

-        return self.paths[-1] if self.paths else None
+        if created_path in self.paths and not created_path.is_being_created:
+            return created_path
+        return None

     def add_station_to_path(self, station: Station) -> None:
         assert self.path_being_created is not None
@@ -584,7 +601,11 @@ class Mediator:
             return self.game_speed_multiplier == 4
         return False

-    def apply_action(self, action: Dict) -> bool:
+    def apply_action(self, action: object) -> bool:
+        if self.is_game_over:
+            return False
+        if not isinstance(action, dict):
+            return False
         action_type = action.get("type")
         if action_type == "create_path":
             stations = action.get("stations", [])
@@ -638,7 +659,9 @@ class Mediator:
         return list(dict.fromkeys(station.shape.type for station in self.stations))

     def is_passenger_spawn_time(self) -> bool:
-        return any(self.should_spawn_passenger_at_station(station) for station in self.stations)
+        return any(
+            self.should_spawn_passenger_at_station(station) for station in self.stations
+        )

     def initialize_station_spawning_state(self, stations: List[Station]) -> None:
         for station in stations:
@@ -653,7 +676,9 @@ class Mediator:

     def get_station_spawn_interval_step(self) -> int:
         min_interval = max(1, int(self.passenger_spawning_interval_step * 0.7))
-        max_interval = max(min_interval, int(self.passenger_spawning_interval_step * 1.3))
+        max_interval = max(
+            min_interval, int(self.passenger_spawning_interval_step * 1.3)
+        )
         return random.randint(min_interval, max_interval)

     def should_spawn_passenger_at_station(self, station: Station) -> bool:
@@ -685,7 +710,7 @@ class Mediator:
             self.station_steps_since_last_spawn[station] = 0

     def increment_time(self, dt_ms: int) -> None:
-        if self.is_paused:
+        if self.is_paused or self.is_game_over:
             return

         speed_multiplier = self.game_speed_multiplier
@@ -702,7 +727,10 @@ class Mediator:
         station_nodes_dict = build_station_nodes_dict(self.stations, self.paths)
         for path in self.paths:
             for metro in path.metros:
-                if metro.current_station is not None and metro.stop_time_remaining_ms <= 0:
+                if (
+                    metro.current_station is not None
+                    and metro.stop_time_remaining_ms <= 0
+                ):
                     self.start_station_stop_if_needed(
                         metro,
                         metro.current_station,
@@ -816,8 +844,8 @@ class Mediator:
     ) -> None:
         if metro.stop_time_remaining_ms > 0:
             return
-        unload_to_destination, unload_to_transfer = self.get_unloading_candidates_for_metro(
-            metro, station
+        unload_to_destination, unload_to_transfer = (
+            self.get_unloading_candidates_for_metro(metro, station)
         )
         num_unload_actions = len(unload_to_destination) + len(unload_to_transfer)
         boarding_candidates = self.get_boarding_candidates_for_metro(
@@ -844,10 +872,7 @@ class Mediator:
             if station.shape.type == passenger.destination_shape.type:
                 return True
             travel_plan = self.travel_plans.get(passenger)
-            if (
-                travel_plan is not None
-                and travel_plan.get_next_station() == station
-            ):
+            if travel_plan is not None and travel_plan.get_next_station() == station:
                 return True
         return False

@@ -873,13 +898,10 @@ class Mediator:
                     metro.boarding_progress_ms += active_boarding_dt
                 elif unload_to_destination or unload_to_transfer or boarding_candidates:
                     metro.stop_time_remaining_ms = (
-                        (
-                            len(unload_to_destination)
-                            + len(unload_to_transfer)
-                            + len(boarding_candidates)
-                        )
-                        * metro.boarding_time_per_passenger_ms
-                    )
+                        len(unload_to_destination)
+                        + len(unload_to_transfer)
+                        + len(boarding_candidates)
+                    ) * metro.boarding_time_per_passenger_ms
                     metro.boarding_progress_ms = 0
                     metro.speed = 0
                     active_boarding_dt = min(dt_ms, metro.stop_time_remaining_ms)
@@ -1024,10 +1046,7 @@ class Mediator:
             first_hop_path = self.find_shared_path(
                 station, reduced_node_path[1].station
             )
-            if (
-                first_hop_path is None
-                or first_hop_path.id != required_first_path.id
-            ):
+            if first_hop_path is None or first_hop_path.id != required_first_path.id:
                 continue
             candidate_cost = (len(node_path), len(reduced_node_path))
             if best_path_cost is None or candidate_cost < best_path_cost:
@@ -1107,6 +1126,7 @@ class Mediator:
                         self.travel_plans[passenger] = TravelPlan(best_node_path[1:])
                         self.find_next_path_for_passenger_at_station(passenger, station)
                     elif (
-                        not passenger.is_at_destination and passenger not in self.travel_plans
+                        not passenger.is_at_destination
+                        and passenger not in self.travel_plans
                     ):
                         self.travel_plans[passenger] = TravelPlan([])
diff --git a/test/test_env.py b/test/test_env.py
index 624485d..e7576f3 100644
--- a/test/test_env.py
+++ b/test/test_env.py
@@ -5,11 +5,11 @@ import unittest
 sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

 from config import station_color, station_size
-from env import MiniMetroEnv
 from entity.metro import Metro
 from entity.passenger import Passenger
 from entity.path import Path
 from entity.station import Station
+from env import MiniMetroEnv
 from geometry.circle import Circle
 from geometry.point import Point
 from geometry.rect import Rect
@@ -53,9 +53,7 @@ class TestEnv(unittest.TestCase):
         env.step({"type": "create_path", "stations": [0, 1, 2], "loop": False})

         self.assertEqual(len(env.mediator.paths), 1)
-        obs, reward, done, info = env.step(
-            {"type": "remove_path", "path_index": 0}
-        )
+        obs, reward, done, info = env.step({"type": "remove_path", "path_index": 0})

         self.assertTrue(info["action_ok"])
         self.assertFalse(done)
@@ -68,9 +66,7 @@ class TestEnv(unittest.TestCase):
         env.step({"type": "create_path", "stations": [0, 1], "loop": False})

         path_id = env.mediator.paths[0].id
-        obs, reward, done, info = env.step(
-            {"type": "remove_path", "path_id": path_id}
-        )
+        obs, reward, done, info = env.step({"type": "remove_path", "path_id": path_id})

         self.assertTrue(info["action_ok"])
         self.assertFalse(done)
@@ -111,6 +107,61 @@ class TestEnv(unittest.TestCase):

         self.assertFalse(info["action_ok"])

+    def test_malformed_actions_return_false_without_mutating(self):
+        env = MiniMetroEnv()
+        env.reset(seed=20)
+        initial_path_count = len(env.mediator.paths)
+
+        malformed_actions = [
+            "not-a-dict",
+            {"type": "create_path", "stations": "01", "loop": False},
+            {"type": "create_path", "stations": [0, "1"], "loop": False},
+            {"type": "remove_path", "path_index": "0"},
+        ]
+
+        for action in malformed_actions:
+            with self.subTest(action=action):
+                _, _, _, info = env.step(action)  # type: ignore[arg-type]
+                self.assertFalse(info["action_ok"])
+                self.assertEqual(len(env.mediator.paths), initial_path_count)
+
+    def test_aborted_create_path_does_not_report_existing_path_success(self):
+        env = MiniMetroEnv()
+        env.reset(seed=21)
+        _, _, _, info = env.step(
+            {"type": "create_path", "stations": [0, 1], "loop": False}
+        )
+        self.assertTrue(info["action_ok"])
+        self.assertEqual(len(env.mediator.paths), 1)
+
+        env.mediator.purchased_num_paths = 2
+        env.mediator.update_unlocked_num_paths()
+        _, _, _, info = env.step(
+            {"type": "create_path", "stations": [0, 0], "loop": False}
+        )
+
+        self.assertFalse(info["action_ok"])
+        self.assertEqual(len(env.mediator.paths), 1)
+
+    def test_step_after_game_over_is_stable_noop(self):
+        env = MiniMetroEnv(dt_ms=10)
+        env.reset(seed=22)
+        env.mediator.is_game_over = True
+        time_before = env.mediator.time_ms
+        steps_before = env.mediator.steps
+        paths_before = len(env.mediator.paths)
+
+        _, reward, done, info = env.step(
+            {"type": "create_path", "stations": [0, 1], "loop": False}
+        )
+
+        self.assertFalse(info["action_ok"])
+        self.assertEqual(reward, 0)
+        self.assertTrue(done)
+        self.assertEqual(env.mediator.time_ms, time_before)
+        self.assertEqual(env.mediator.steps, steps_before)
+        self.assertEqual(len(env.mediator.paths), paths_before)
+
     def test_observation_arrays_shapes(self):
         env = MiniMetroEnv()
         obs = env.reset(seed=7)
@@ -398,5 +449,7 @@ class TestEnv(unittest.TestCase):

         self.assertTrue(done)
         self.assertTrue(env.mediator.is_game_over)
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/test/test_graph.py b/test/test_graph.py
index fb326f0..29efb99 100644
--- a/test/test_graph.py
+++ b/test/test_graph.py
@@ -1,14 +1,13 @@
 import os
 import sys
 import unittest
-from unittest.mock import create_autospec
-
-from entity.get_entity import get_random_stations

 sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

 import pygame
+
 from config import screen_height, screen_width, station_color, station_size
+from entity.get_entity import get_random_stations
 from entity.path import Path
 from entity.station import Station
 from event.mouse import MouseEvent
@@ -25,7 +24,7 @@ from utils import get_random_color, get_random_position
 class TestGraph(unittest.TestCase):
     def setUp(self):
         self.width, self.height = screen_width, screen_height
-        self.screen = create_autospec(pygame.surface.Surface)
+        self.screen = pygame.Surface((self.width, self.height))
         self.position = get_random_position(self.width, self.height)
         self.color = get_random_color()
         self.mediator = Mediator()
@@ -166,6 +165,38 @@ class TestGraph(unittest.TestCase):
         for node in station_nodes.values():
             self.assertEqual(node.paths, set())

+    def test_build_station_nodes_dict_connects_loop_closure(self):
+        station_a = Station(
+            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
+        )
+        station_b = Station(Circle(station_color, station_size), Point(10, 0))
+        station_c = Station(
+            Rect(station_color, 2 * station_size, 2 * station_size), Point(20, 0)
+        )
+        path = Path((0, 0, 0))
+        path.add_station(station_a)
+        path.add_station(station_b)
+        path.add_station(station_c)
+        path.set_loop()
+
+        station_nodes = build_station_nodes_dict(
+            [station_a, station_b, station_c], [path]
+        )
+
+        self.assertIn(station_nodes[station_c], station_nodes[station_a].neighbors)
+        self.assertIn(station_nodes[station_a], station_nodes[station_c].neighbors)
+        self.assertSequenceEqual(
+            bfs(station_nodes[station_a], station_nodes[station_c]),
+            [station_nodes[station_a], station_nodes[station_c]],
+        )
+
+    def test_equal_nodes_have_same_hash(self):
+        station = Station(
+            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
+        )
+
+        self.assertEqual(len({Node(station), Node(station)}), 1)
+

 if __name__ == "__main__":
     unittest.main()
diff --git a/test/test_mediator.py b/test/test_mediator.py
index f3904c1..f8b767b 100644
--- a/test/test_mediator.py
+++ b/test/test_mediator.py
@@ -1,41 +1,40 @@
 import os
 import sys
 import unittest
-from unittest.mock import MagicMock, create_autospec, patch
-
-from entity.get_entity import get_random_stations
-from event.mouse import MouseEvent
-from event.type import MouseEventType
-from geometry.triangle import Triangle
-from geometry.type import ShapeType
+from unittest.mock import MagicMock, patch

 sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

 from math import ceil

 import pygame
+
 from config import (
     button_color,
     framerate,
     initial_num_stations,
     num_stations,
-    path_unlock_milestones,
     passenger_spawning_interval_step,
     passenger_spawning_start_step,
+    path_unlock_milestones,
     screen_height,
     screen_width,
-    station_unlock_milestones,
     station_color,
     station_size,
+    station_unlock_milestones,
     unlock_blink_duration_ms,
 )
 from entity.metro import Metro
 from entity.passenger import Passenger
 from entity.path import Path
 from entity.station import Station
+from event.mouse import MouseEvent
+from event.type import MouseEventType
 from geometry.circle import Circle
 from geometry.point import Point
 from geometry.rect import Rect
+from geometry.triangle import Triangle
+from geometry.type import ShapeType
 from graph.node import Node
 from mediator import Mediator
 from travel_plan import TravelPlan
@@ -46,10 +45,13 @@ from utils import get_random_color, get_random_position
 class TestMediator(unittest.TestCase):
     def setUp(self):
         self.width, self.height = screen_width, screen_height
-        self.screen = create_autospec(pygame.surface.Surface)
+        self.screen = MagicMock()
+        self.screen.get_width.return_value = self.width
+        self.screen.get_height.return_value = self.height
         self.position = get_random_position(self.width, self.height)
         self.color = get_random_color()
         self.mediator = Mediator()
+        pygame.draw = MagicMock()
         self.mediator.render(self.screen)

     def connect_stations(self, station_idx):
@@ -110,7 +112,9 @@ class TestMediator(unittest.TestCase):
             return (idx, idx, idx)

         with patch("mediator.hue_to_rgb", side_effect=fake_hue_to_rgb):
-            colors = self.mediator.generate_distinct_path_colors(self.mediator.num_paths)
+            colors = self.mediator.generate_distinct_path_colors(
+                self.mediator.num_paths
+            )

         self.assertEqual(len(colors), self.mediator.num_paths)

@@ -300,11 +304,24 @@ class TestMediator(unittest.TestCase):
         self.assertCountEqual(triangle_stations, self.mediator.stations[3:])

     def test_skip_stations_on_same_path(self):
-        self.mediator.stations = get_random_stations(5)
+        station_a = Station(
+            Rect(station_color, 2 * station_size, 2 * station_size), Point(0, 0)
+        )
+        station_b = Station(Circle(station_color, station_size), Point(100, 0))
+        station_c = Station(Triangle(station_color, station_size), Point(200, 0))
+        self.mediator.stations = [station_a, station_b, station_c]
         for station in self.mediator.stations:
             station.draw(self.screen)
-        self.connect_stations([i for i in range(5)])
-        self.mediator.spawn_passengers()
+        self.connect_stations([0, 1, 2])
+
+        passenger_a = Passenger(station_c.shape)
+        passenger_b = Passenger(station_a.shape)
+        passenger_c = Passenger(station_b.shape)
+        station_a.add_passenger(passenger_a)
+        station_b.add_passenger(passenger_b)
+        station_c.add_passenger(passenger_c)
+        self.mediator.passengers = [passenger_a, passenger_b, passenger_c]
+
         self.mediator.find_travel_plan_for_passengers()
         for station in self.mediator.stations:
             for passenger in station.passengers:
@@ -376,7 +393,9 @@ class TestMediator(unittest.TestCase):
             mediator.game_over_hint_font.render = MagicMock(return_value=hint_surface)
             mediator.render(screen)

-        surface_mock.assert_called_once_with((screen_width, screen_height), pygame.SRCALPHA)
+        surface_mock.assert_called_once_with(
+            (screen_width, screen_height), pygame.SRCALPHA
+        )
         overlay.fill.assert_called_once()
         screen.blit.assert_any_call(overlay, (0, 0))
         self.assertGreaterEqual(mediator.font.render.call_count, 1)
@@ -389,12 +408,8 @@ class TestMediator(unittest.TestCase):
         mediator.game_over_restart_rect = pygame.Rect(0, 0, 10, 10)
         mediator.game_over_exit_rect = pygame.Rect(20, 0, 10, 10)

-        self.assertEqual(
-            mediator.handle_game_over_click(Point(5, 5)), "restart"
-        )
-        self.assertEqual(
-            mediator.handle_game_over_click(Point(25, 5)), "exit"
-        )
+        self.assertEqual(mediator.handle_game_over_click(Point(5, 5)), "restart")
+        self.assertEqual(mediator.handle_game_over_click(Point(25, 5)), "exit")
         self.assertIsNone(mediator.handle_game_over_click(Point(50, 50)))

     def test_mouse_motion_no_entity_triggers_exit(self):
@@ -432,9 +447,7 @@ class TestMediator(unittest.TestCase):

         button = HoverButton()
         mediator.buttons = [button]
-        mediator.react_mouse_event(
-            MouseEvent(MouseEventType.MOUSE_MOTION, Point(0, 0))
-        )
+        mediator.react_mouse_event(MouseEvent(MouseEventType.MOUSE_MOTION, Point(0, 0)))
         self.assertTrue(button.hovered)

     def test_speed_buttons_pause_and_resume_with_multiplier(self):
@@ -459,13 +472,33 @@ class TestMediator(unittest.TestCase):
         passenger = Passenger(station_b.shape)
         metro.add_passenger(passenger)
         mediator.passengers.append(passenger)
+        mediator.travel_plans[passenger] = TravelPlan([Node(station_b)])
         mediator.path_buttons[0].assign_path(path)
         mediator.path_to_button[path] = mediator.path_buttons[0]
         mediator.path_to_color[path] = path.color
         mediator.remove_path(path)
         self.assertNotIn(passenger, mediator.passengers)
+        self.assertNotIn(passenger, mediator.travel_plans)
         self.assertNotIn(path, mediator.paths)

+    def test_remove_path_recomputes_waiting_passenger_plan(self):
+        mediator, station_a, station_b, path, _ = self._build_two_station_mediator()
+        passenger = Passenger(station_b.shape)
+        station_a.add_passenger(passenger)
+        mediator.passengers.append(passenger)
+        mediator.travel_plans[passenger] = TravelPlan([Node(station_b)])
+        mediator.travel_plans[passenger].next_path = path
+        mediator.path_buttons[0].assign_path(path)
+        mediator.path_to_button[path] = mediator.path_buttons[0]
+        mediator.path_to_color[path] = path.color
+
+        mediator.remove_path(path)
+
+        self.assertIn(passenger, mediator.passengers)
+        self.assertIn(passenger, mediator.travel_plans)
+        self.assertIsNone(mediator.travel_plans[passenger].next_path)
+        self.assertIsNone(mediator.travel_plans[passenger].next_station)
+
     def test_add_station_to_path_returns_on_duplicate(self):
         mediator = Mediator()
         station = mediator.stations[0]
@@ -830,12 +863,8 @@ class TestMediator(unittest.TestCase):
         intermediate_station = Station(
             Circle(station_color, station_size), Point(10, 0)
         )
-        short_destination = Station(
-            Triangle(station_color, station_size), Point(20, 0)
-        )
-        long_destination = Station(
-            Triangle(station_color, station_size), Point(30, 0)
-        )
+        short_destination = Station(Triangle(station_color, station_size), Point(20, 0))
+        long_destination = Station(Triangle(station_color, station_size), Point(30, 0))
         mediator.stations = [
             start_station,
             intermediate_station,
@@ -880,12 +909,8 @@ class TestMediator(unittest.TestCase):
         intermediate_station = Station(
             Circle(station_color, station_size), Point(10, 0)
         )
-        short_destination = Station(
-            Triangle(station_color, station_size), Point(20, 0)
-        )
-        long_destination = Station(
-            Triangle(station_color, station_size), Point(30, 0)
-        )
+        short_destination = Station(Triangle(station_color, station_size), Point(20, 0))
+        long_destination = Station(Triangle(station_color, station_size), Point(30, 0))
         mediator.stations = [
             start_station,
             intermediate_station,
