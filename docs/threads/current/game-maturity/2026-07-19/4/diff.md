# GM-04b intended diff

- Add a dependency-light safe setup/verifier, hardened Git/process/filesystem boundaries, and an unconditional public-command guard.
- Add exact setup, trust-order, cleanup, credential-isolation, strict/canary, hook-bypass, workflow, and Windows command tests.
- Rewire package scripts and CI to dogfood the setup from a missing pin on Ubuntu and Windows while retaining defense-in-depth pre-hooks.
- Replace the manual PowerShell bootstrap with the public command and document fail-closed/crash-recovery behavior.
- Update architecture, agent guidance, progress, parent state/evidence/decision, and this iteration's plan/review artifacts.
- Preserve `.agents/`, unrelated ignored output, the retained pin except for explicit live validation, and `../civ-engine`; never stage generated pin/setup/lock content or credentials.
