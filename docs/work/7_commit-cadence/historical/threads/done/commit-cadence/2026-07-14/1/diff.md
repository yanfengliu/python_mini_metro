# Commit-cadence policy diff

Baseline: `b1e419e21080fd5bd43e1ac6a4eef7e264f732ec`

Status: policy wording and project log complete; adversarial review re-converged; changed-path hooks and exact staged audit clean; commit, push, and remote CI pending.

## Policy boundary

- Minimal coherent units are reviewed and verified before becoming prompt delivery boundaries.
- Each unit is staged narrowly and committed before unrelated completed work accumulates.
- Trivial changes remain self-reviewed; behavior, public-contract, and other non-trivial changes remain adversarially reviewed.
- Failing, in-flight, and partial checkpoint commits remain prohibited.

## Review boundary

Pinned Codex and Claude review attempts both failed authentication with HTTP 401 and yielded no approval. Two independent in-process lanes reviewed the live file; one required the missing `PROGRESS.md` entry, that finding was fixed, and both final rechecks are `CLEAN`. The unrelated `.agents/` tree remains outside scope.
