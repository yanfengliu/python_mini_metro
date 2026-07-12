# GM-01b implementation review

## Conclusion

APPROVED after fixes. Three independent in-process lanes reviewed visual geometry, RL/persisted compatibility, and spawn-cadence/documentation correctness against the live tree. No High or Medium defect was found; all Low findings were fixed and independently re-reviewed with no remaining concrete finding.

## Reviewer availability

- This high-risk presentation/configuration change normally also receives Codex and Claude multi-CLI review. The private-workspace transfer restriction recorded in GM-00 and GM-01a still applies, so no prohibited upload or bypass was attempted.
- The compensating review used three independent in-process lanes, each told to verify symbols, control flow, geometry, serialized fields, and tests against the live code rather than approving the prompt description.

## Findings and disposition

| Severity | Finding | Verified disposition |
| --- | --- | --- |
| Low | Compact overlay test checked vertical order but not horizontal bounds | Added left/right containment assertions for the title and both metric labels at 800x600; visual reviewer re-approved |
| Low | Documentation promised reset after a due full-station attempt without a direct regression | Added a real full-capacity branch test proving no passenger growth and counter reset to zero; cadence reviewer re-approved |
| Low | The divisible 900-step speed test could not prove the documented whole-tick quantization | Added a 1,170-step at 4x case proving first spawn on wall tick 293 at 1,172 steps and 19,536 simulated ms; cadence reviewer re-approved |
| Low | Touched terminology retained a private `travels` accumulator and called a censored delivery count a final score | Renamed the private accumulator and corrected README wording; compatibility and cadence reviewers re-approved |

## Verified contracts

- HUD and game-over text read canonical deliveries and line credits first and still accept legacy-only state objects.
- Prepared restart/exit hitboxes remain unchanged; rendered content fits 1920x1080 and 800x600 without overlap or clipping.
- Protocol v1, default task descriptor, action semantics, reward modes, manifest/checkpoint schemas, and terminal-metrics-v1 keys are unchanged.
- Only the intended environment-content fingerprint changes, so old artifacts remain fail-closed unless the existing explicit content-drift override is supplied.
- The documented spawn range, initial attempt, speed scaling, full-station reset, and quantization all match live mediator and fixed-clock behavior.

## Verification at review convergence

- Focused renderer/cadence suite: 19/19 passed after fixes.
- Preliminary full core suite: 350 tests passed with 8 expected optional-RL skips before the two added cadence cases; final full gates are recorded in the parent evidence ledger.
- Preliminary exact-RL suite: 350/350 passed before the two added cadence cases; final full gates are recorded in the parent evidence ledger.
- Full-repo Ruff check passed and all 100 Python files were formatted before final thread artifacts.
- Deterministic before/after screenshots were inspected directly.

## Residual limits

- Cross-platform golden raster hashes remain intentionally absent because bundled font rasterization can vary; same-runtime pixel sensitivity, deterministic render tests, geometry assertions, and checked-in visual evidence cover this change.
- `src/mediator.py` remains over the 1,000-line ceiling but was not enlarged; GM-03 owns its staged decomposition.
- Local full Node parity remains blocked by the known linked civ-engine 2.4.1 versus repository pin 2.2.0 mismatch. Pinned remote CI remains the authoritative full Node gate until GM-04.
