CLEAN.

The change at `AGENTS.md:162` correctly requires minimal coherent units, completed validation/review, scoped staging, and forbids failing or partial checkpoint commits. It is consistent with the validation gates (`:84-94`), review policy (`:47-48`, `:111`), and staged-diff safeguards (`:160-165`). `git diff --check -- AGENTS.md` also passes. No edits made.
