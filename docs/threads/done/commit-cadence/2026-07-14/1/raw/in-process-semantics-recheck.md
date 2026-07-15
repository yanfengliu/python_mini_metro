CLEAN.

`PROGRESS.md:122` accurately summarizes the `AGENTS.md:162` policy: required review/verification, scoped staging, prompt minimal-unit commits, and prohibition of failing, in-flight, or partial checkpoints. It introduces no broader claim such as completion, push, or CI status. The two-file diff also passes `git diff --check`; only Git's informational LF-to-CRLF warning remains.
