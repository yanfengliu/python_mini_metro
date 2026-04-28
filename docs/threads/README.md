# Threads

This directory stores work threads. A thread is the durable record for one coherent piece of work, named by theme.

Threads start under `current/` while work is active and move to `done/` when the work is complete. If a completed theme already exists under `done/`, merge the new date or iteration directories into that theme instead of replacing the whole theme directory.

Use short kebab-case theme names, such as `agents-repo-fit`, `thread-structure`, or `metro-dwell-fix`. Full-codebase review work always uses the theme name `full`.

Preserve `raw/` reviewer outputs verbatim. If a folder migration changes where a thread lives, document that migration in `REVIEW.md` or another non-raw note instead of rewriting the original reviewer text.

Use this layout for thread artifacts:

```text
docs/threads/current/<theme>/<YYYY-MM-DD>/<iteration>/
|- raw/
|  |- codex-1.md
|  |- opus.md
|  \- codex-2.md
|- diff.md
\- REVIEW.md
```

When the thread is complete, move or merge that date/iteration tree to:

```text
docs/threads/done/<theme>/<YYYY-MM-DD>/<iteration>/
```

Start iteration numbering at `1` and increment it only when a re-review or revised artifact set is needed after addressing findings. For recurring themes, inspect both `current/<theme>/` and `done/<theme>/` before choosing the next date or iteration number.
