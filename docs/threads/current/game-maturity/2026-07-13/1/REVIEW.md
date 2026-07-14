# GM-02e research-plan review

## Scope

Review the research-only decision to keep ten-frame RecurrentPPO as the pixel baseline while scheduling compact semantic, direct hybrid, and pixel-only privileged-transfer candidates for GM-12. No runtime, dependency, reward, observation, model, or manifest code changes are in scope.

## Reviewer availability

- External Codex: preflight confirmed `codex-cli 0.144.3`, but the platform rejected exporting repository plan/code context before the pinned read-only reviewer launched. The exact boundary is recorded in `raw/codex-plan.md`.
- External Claude: not launched because rerouting the prohibited same repository export through another external service was disallowed. The exact boundary is recorded in `raw/claude-plan.md`.
- In-process live-contract reviewer: completed initial review, one focused re-review, and final clean re-review against the live repository.
- In-process adversarial refuter: completed two finding rounds and final clean re-review against the live repository.

## Findings and disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | A hybrid Dict observation contradicted the pixels-only protocol/task identity | Fixed: preserve exact pixel protocol-v1; give assisted tiers distinct protocol/task identities; add manifest v3 while retaining genuine v1/v2 bytes |
| High | “Player-observable” overstated exact semantic tensors and permitted privileged precision | Fixed: label direct semantics as perception assist; separate pixel, semantic, and oracle tiers; exclude hidden dynamics and require leakage tests |
| High | `MultiInputLstmPolicy` support did not solve the Box-only history/training lifecycle | Fixed: require a Dict-aware pixel-only history wrapper with terminal/autoreset, prehistory, ordering, and slot-isolation contracts |
| High | The proposed current-state inventory omitted GM-05 through GM-10 mechanics | Fixed: GM-12a inventories the final renderer/control/action surface before drafting candidates |
| Medium | Observation identity was duplicated across persistence layers | Fixed: manifest is the semantic authority; manifest authenticates index, index authenticates models, and durable evidence separately authenticates manifest bytes |
| Medium | The roadmap froze schemas before implementation proof and dropped the action-head lane | Fixed: GM-12a drafts rules; GM-12b implements/tests before version/matrix freeze; conditional pointer head remains a separate ablation |
| Medium | The persistent cursor still described completed review work as pending | Fixed: STATE now marks review/hooks complete, makes final diff/staging the first resume action, and records GM-02e as local-ready |
| High | Public guidance incorrectly said the current pixel actor receives explicit action/reward history | Fixed: current actor input is pixels plus learned recurrent state; explicit action/reward inputs are reserved for a separately versioned future ablation |

## Convergence

Both independent in-process reviewers returned `CLEAN` after the final fixes. The research decision is approved within its declared scope. Runtime implementation remains deferred until the stable post-balance GM-12 contract, and every direct semantic result must remain labeled as assisted rather than player-equivalent.

## Validation

- `pre-commit run --files ...` passed all fourteen changed/new Markdown artifacts after the end-of-file hook made and revalidated four mechanical newline-only fixes.
- `git diff --check` passed the tracked diff; pre-commit independently checked trailing whitespace and terminal newlines in the new thread files.
- Local SB3 introspection confirmed both installed packages are 2.9.0 and `MultiInputLstmPolicy` is the expected recurrent multi-input policy alias.
- No Python, Node, dependency, runtime, reward, observation, model, protocol, or manifest implementation file changed. GM-02d2 Commit B's full remote `build`/`rl-smoke` run is the exact clean code baseline; the GM-02e A/B remote transaction remains pending.
