# GM-00 persistent plan review

## Conclusion

APPROVED after revisions. The available external Codex review found three High and seven Medium plan defects. Every claim was checked against live code, the plan was revised, and three independent in-process re-review lanes converged with no remaining High or Medium finding.

This approval covers the execution plan and persistence contract only. Runtime behavior remains at the baseline described in `EVIDENCE.md`; every later work unit still requires its own TDD, gates, and risk-proportional review.

## Reviewer availability

- Codex CLI 0.144.1 with `gpt-5.6-sol`/ultra completed the initial read-only review; its final output is preserved verbatim in `raw/codex.md`.
- The runbook-mandated Codex self-update was attempted first but Windows returned `EBUSY` because the active process held the binary. The installed 0.144.1 version meets the model's documented minimum and its pinned-model smoke passed.
- Preferred Claude Fable was unavailable because its usage limit was reached. The approved `opus[1m]` fallback smoke passed, but the environment then rejected sending private workspace plan content to the external Claude service. No workaround was attempted.
- A targeted external Codex re-review was also rejected by the environment's external-data-transfer policy. The safe compensation was three independent in-process live-code re-review lanes covering semantics/persistence, product architecture, and RL/validation; all returned APPROVED after their findings were fixed.

## Initial Codex findings and disposition

| Severity | Finding | Disposition |
| --- | --- | --- |
| High | Cursor could not be durably advanced after remote CI | Resolved with identifiable Commit A/Commit B transactions, live Commit-B CI lookup, reopen rules, and archival recovery |
| High | State cursor lacked substep and experiment granularity | Resolved with a complete work-unit/phase ledger plus mandatory per-training-seed and per-evaluation-seed transaction rows |
| High | Selectable maps were absent from RL task identity | Resolved with versioned task descriptors/fingerprints, map ID/version in all reconstruction surfaces, and genuine legacy descriptor tests |
| Medium | Fleet acceptance required save data before saves existed | Resolved by limiting GM-06 to runtime/observation/checkpoint state and making GM-07 include completed fleet state in the first save schema |
| Medium | Save equality ignored public IDs | Resolved with exact public-ID roundtrip and post-load action acceptance requirements |
| Medium | Deliveries migration lacked persisted-schema compatibility | Resolved with checkpoint v2/v1 normalization, recursive-input reward contracts, versioned agent-play records, and terminal-metrics reconstruction |
| Medium | Writable aliases and agent-play semantics were not pinned | Resolved with writable setter coverage and explicit legacy/canonical record APIs |
| Medium | Threshold evidence was not durably reproducible | Resolved with `THRESHOLD_BASELINE.md` containing exact command, route, seeds, horizon, output, and limitations |
| Medium | History layout lacked independent identity | Resolved with a separately validated `historyFingerprint`, manifest v2, and training-source hash coverage |
| Medium | Legacy history and vector-reset coverage was too narrow | Resolved with arbitrary contiguous N coverage, genuine old bytes, and staggered multi-slot reset/terminal tests |

## In-process adversarial findings and disposition

- The semantics lane found that failing TDD tests could not be a remotely green substep and that checkpoint normalization alone would not preserve v1 recursive transcript rewards. The plan now distinguishes design/TDD phases from independently shippable work units and reconstructs legacy score-delta replay for v1 recursive inputs, including a genuine purchase regression.
- The product lane found underspecified legacy map hashes, pause reasons introduced too late, oversized map/upgrade units, and ambiguous Commit-B identity. The plan now reconstructs exact legacy descriptors, moves pause reasons to GM-07, splits every map and upgrade family, and locates transaction commits by marker and `STATE.md` history even after archival.
- The RL/validation lane found that GM-12 rows were locally granular but not remotely durable. Every training and evaluation row is now its own two-commit transaction with artifact locator, model/manifest/index digests, presence/rehash checks, CI result, and next-row cursor.
- After these revisions, all three lanes returned APPROVED with no remaining High or Medium defect.

## Residual limits

- Threshold two is only a bounded initial correction supported by one deterministic fixed-route baseline; it is not final human or learned-policy balance evidence.
- The twelve-frame multiscale layout is an implementation candidate, not yet the promoted default. GM-02 must profile it against the declared controls before promotion.
- Large trained artifacts remain local under ignored `output/` until the user explicitly authorizes an external artifact store. Missing or hash-mismatched artifacts reopen their experiment row.
