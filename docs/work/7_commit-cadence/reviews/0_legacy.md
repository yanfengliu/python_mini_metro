# Commit-cadence policy review

## Scope

The policy change expands the existing commit instruction so each minimal coherent unit becomes a delivery boundary only after the applicable verification and review pass. It requires scoped staging, prompt commits, and continued prohibition of failing, in-flight, or partial checkpoint commits. `PROGRESS.md` records the completed process-policy change without claiming push or CI completion.

## External review boundary

The required reviewer preflight attempted to upgrade Codex CLI; replacement was blocked because its active binary was in use, while installed `0.144.4` exactly matched the registry's current `0.144.4`. Pinned Codex `gpt-5.6-sol` and Claude `claude-fable-5[1m]` were then launched as read-only reviewers. Both returned HTTP 401 authentication failures and produced no review or approval. The first parallel Codex attempt ended during retries when Claude failed; the sequential Codex retry captured the complete WebSocket and HTTPS 401 boundary. Raw captures are preserved verbatim.

## In-process adversarial review

The semantics lane returned `CLEAN` against the full live `AGENTS.md`. The independent refuter found one `MEDIUM` process-completeness issue: this substantive high-risk policy change lacked the project-log entry required by the documentation rules. A concise `PROGRESS.md` bullet now closes that finding. Both independent rechecks returned `CLEAN`, confirmed the log accurately matches the policy, and found no conflict with continuous plan execution, direct-main commits, validation gates, adversarial review, scoped staging, or end-of-task pushing.

## Commit boundary

The intended 14-path unit contains `AGENTS.md`, `PROGRESS.md`, and this review thread. The pre-existing untracked `.agents/skills/multi-cli-review/SKILL.md` remains excluded. EOF, trailing-whitespace, Ruff check, and Ruff format hooks pass all 13 hook-safe paths without rewriting raw evidence. The UTF-16 Claude 401 capture is excluded only from the EOF fixer and remains byte-exact at SHA-256 `fccf9497458d6e0487324107b9fc41af93efd5ce47837c6c3abbe3761b59289b`. The complete cached boundary is 14 files with 53 insertions and one deletion; full cached diff inspection plus whitespace, credential, dependency, scope, and indexed-raw-byte audits are clean. Commit, push, and exact CI are the remaining gates.
