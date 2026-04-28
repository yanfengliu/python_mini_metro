You are a senior process and documentation reviewer. Do NOT modify files. Only flag real, important issues.

Task intent: The repo is changing from the old review-artifact directory to `docs/threads`. All work threads should be organized as `docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/` while active and moved/merged into `docs/threads/done/<theme>/<YYYY-MM-DD>/<iteration>/` when complete. Completed full repo reviews keep the theme name `full`.

Review this thread's `diff.md` and the current files if needed. Focus on:
- Any remaining references to the outdated review-artifact folder structure in live process docs.
- Whether AGENTS.md clearly explains current vs done, recurring theme merge semantics, and full-review placement.
- Whether ARCHITECTURE.md and PROGRESS.md match the actual repo layout.
- Whether the new thread docs are understandable and maintainable.

Known context: Claude was unavailable due quota during the plan check. Codex plan review asked us to define merge semantics for recurring themes, make the lifecycle broader than review-only artifacts, and avoid clobbering existing `done/full`; those were incorporated.

If there are no important issues, say so.
