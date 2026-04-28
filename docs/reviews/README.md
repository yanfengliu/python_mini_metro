# Reviews

This directory stores multi-CLI review artifacts for substantive behavior, API, architecture, config, workflow, process-documentation changes, and full-codebase audits.

Use this layout:

```text
docs/reviews/<scope>/<YYYY-MM-DD>/<iteration>/
|- raw/
|  |- codex-1.md
|  |- opus.md
|  \- codex-2.md
|- diff.md
\- REVIEW.md
```

Keep review scope names short and kebab-case, such as `agents-repo-fit`, `full`, or `metro-dwell-fix`. Start iteration numbering at `1` and increment it only when a re-review is needed after addressing findings.
