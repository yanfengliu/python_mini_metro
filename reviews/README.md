# Reviews

This directory stores multi-CLI review artifacts for substantive behavior, API, architecture, config, workflow, and process-documentation changes.

Use this layout:

```text
reviews/<scope>/<YYYY-MM-DD>/<iteration>/
|- raw/
|  |- codex.md
|  \- opus.md
|- diff.md
\- REVIEW.md
```

Keep review scope names short and kebab-case, such as `agents-repo-fit` or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
