# GM-06c exact hook blocker

The intended payload contains 129 paths after excluding `.agents/` and the three task-cache roots. The first exact pre-commit attempt failed before hooks because pre-commit's Git subprocess did not receive a safe-directory exception and its default cache log was not writable. The corrected command supplied a command-local `safe.directory` entry and reused the repository-local isolated cache; hook-environment installation then produced no result for two bounded minutes and was terminated, along with only the exact Git children created during that attempt.

The required unsandboxed retry was requested so the isolated hook environment could finish installing. Approval review rejected it because the approval account had reached its usage limit and supplied a next-availability date of July 26, 2026. No workaround or exact-hook pass is claimed.

Direct evidence remains green: the definitive py313 suite passes 998 tests with 12 skips, the adjacent Node replay command passes 8/8, Ruff check and Ruff format-check pass all 84 changed Python files, and working-tree diff-check passes. Exact pre-commit remains a delivery blocker unless it later succeeds or the owner explicitly accepts this documented substitute.

The final intended payload contains 130 paths after this blocker record. A normal exact `git add` failed because the sandbox cannot create `.git/index.lock`; the required scoped `git add` escalation was then rejected at the same approval-usage boundary. No path is staged, no cached audit is claimed, and no commit or push was attempted.

A read-only intended-payload audit reports zero forbidden paths, zero dependency/workflow paths, zero missing final newlines, zero trailing-whitespace findings, and zero high-confidence credential signatures. This is not a cached-stage audit and does not substitute for the blocked exact hook without owner acceptance.
