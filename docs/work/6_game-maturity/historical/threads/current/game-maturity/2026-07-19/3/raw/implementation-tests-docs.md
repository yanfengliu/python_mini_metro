# Tests and documentation implementation review

## Initial review

BLOCKED for Commit A.

- High: `.civ-engine-pin` can be a junction to `../civ-engine`; realpath comparison then reports `locationMatches=true`, making sibling use overridable.
- High: a top-level `dist/` junction can escape the pin root because it is followed before link/type validation. Require a physical `dist` directory and runtime containment.
- High: README's PowerShell commands can continue after a failed clone and mutate an existing alias/sibling. Add explicit existence and `$LASTEXITCODE` guards or defer setup to GM-04b.
- Medium: workflow/ignore parity tests hardcode today's commit/path instead of deriving them from the descriptor, so future drift can pass.
- Medium: no negative runtime-entry mismatch test exists despite the frozen plan requiring non-overridable coverage.
- Medium: `resolveCivEnginePinRoot` accepts relative roots, contradicting its cwd-independent contract.
- Medium: Commit-A evidence is incomplete: actual TDD red, final gates, source-inventory delta, both dependency audits, implementation-review disposition, and scoped staging audit are not recorded.
- Low: `PROGRESS.md` needs the substantive GM-04a entry.
- Low: semantic-version validation accepts invalid numeric prereleases such as `2.2.0-01`.

Verified: HEAD baseline is exactly 44 unique Node tests; all 44 names remain; current suite is 53/53; new descriptor and loader participate in source inventory; `.agents/`, `.civ-engine-pin/`, and `output/` are outside transaction scope; nothing is staged; root audit does not cover the pin build lock; `.npmrc` EOL and architecture-tree placement were corrected. Reviewer made no edits.

## Final re-review

Clean verdict: no remaining implementation, test, or documentation findings.

Final live `npm test`: 56/56 passed, including all 44 frozen pre-GM04 test names. Mechanism-level provenance and portability coverage are complete, source files remain focused, and the updated architecture/docs are truthful. Final gate/evidence fields were intentionally excluded as requested.
