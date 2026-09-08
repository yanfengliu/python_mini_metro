# Recursive loop review

## Plan review availability

The required external Codex and Claude plan reviews were attempted separately after the mandated Codex CLI upgrade. The security layer denied both repository-context exports before either command ran or sent content. They remain unavailable unless the user explicitly approves that export after being informed of the risk. Three independent in-process reviewers therefore performed the plan adversarial pass; their verbatim reports are preserved under `raw/`.

## Plan findings and dispositions

- **Exact claim verification (high/P1): accepted.** Same-run verification now requires exact one-to-one equality of complete authored finding payloads and constructs verified findings from replay-side oracle output. Stable class comparison is reserved for cross-run prove-fixed.
- **Manifest completeness/read-back (medium): accepted.** A repo-level validator now requires seed/commit/cost/timing/outcome/artifacts/gates metadata beyond the permissive engine schema and validates files plus appended rows after reading them back.
- **Crash-ledger black-box coverage (high/P1): accepted.** The plan now tests nonexistent-executable spawn rejection, child nonzero exit, and unparseable scenarios through the real orchestrator, including exactly-one-row and truthful-artifact assertions.
- **Acceptance TDD order (P1): accepted.** The promoted regression is added and demonstrated red while the injected defect is still present, then the implementation is restored and proven green.
- **Checkpoint latent-state observability (P2): accepted.** The test plan now perturbs every identified determinism-critical state family and requires checkpoint/digest changes.
- **CI sibling pin and layout (high): accepted.** CI checks both repositories out as workspace siblings and sets Node 22. The initially reviewed civ-engine 2.1.0 pin advanced during implementation; compatibility was rechecked against the clean 2.2.0 release, so the final pin is commit `e0cb614a516c449159a4562c2ac45bd40bffd3df` with an asserted engine version of 2.2.0.
- **Node setup/TDD order (medium): accepted.** The minimal manifest/install precedes failing Node imports; fixture creation follows its failing end-to-end test.
- **Thread artifacts (medium): accepted.** The plan now explicitly preserves raw reports, a path-limited diff, and the synthesized review.

## Plan re-review

All three independent in-process reviewers re-read the revised design and plan against the live repository and fleet contracts and returned `APPROVE`. The plan is converged; implementation may begin.
