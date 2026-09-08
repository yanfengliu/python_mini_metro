# Tests and documentation plan review

## Initial verdict

BLOCKED — plan findings:

HIGH — npm lifecycle pre-hooks are bypassable under the plan’s own untrusted ambient-npm threat model. PLAN 13 treats ambient npm config as untrusted, but 51-53/73 rely on `pretest`/`preplaytest:*` to stop bodies. npm 11 explicitly still runs `npm test`/`npm run <script>` with `ignore-scripts=true` while suppressing pre/post hooks. Thus `npm test --ignore-scripts` or `npm_config_ignore_scripts=true npm run playtest:verify` executes engine-importing bodies without the verifier. Fix: keep lifecycle hooks only as defense-in-depth and make each requested public body a dependency-light Node guard/dispatcher that verifies before spawning the real test/verify/recursive body with argv + shell:false; recursive guard derives strict vs allow-dirty from actual forwarded args. Add sentinel tests for CLI/env ignore-scripts bypass.

MEDIUM — canary integration TDD is under-specified. Lines 52/60 prove identity-failure sentinels but do not explicitly prove: dirty engine + normal recursive command is rejected by the existing in-body gate before engine import; dirty engine + actual `--allow-dirty` proceeds; physical/root/runtime mismatch fails both; strict test/verifier reject attributed content mismatches. Freeze all four, including through the new body guard.

MEDIUM — cross-platform acceptance has no real Windows execution. CI replacement at 53 exercises setup only in Ubuntu `build`; Windows `rl-smoke` runs no Node/setup/tests. This leaves the custom ComSpec/npm.cmd path entirely unit/mock tested despite known direct npm.cmd EINVAL. Add a Windows missing-pin setup + verify smoke (new job or steps after setup-node in rl-smoke), while GM-04c retains the repeated-live proof.

MEDIUM — transactional artifacts are not frozen into ignore/parity or crash behavior. Lines 32-39 promise an ignored unique stage and lock, but current ignore covers only `/.civ-engine-pin/`; the plan does not name/validate ignore patterns for stage/lock or define recovery/remediation for an owner that dies and leaves the lock. A crash can leave visible untracked worktree state and permanently block setup. Freeze descriptor-derived root lock/stage names, exact `.gitignore` parity tests, and either token/PID dead-owner recovery or documented exact manual recovery; nonowners must never delete a live owner/winner.

MEDIUM — npm child config sanitization is narrower than the threat model. Line 45 strips token/auth/secret variables but other inherited `npm_config_*` values such as `script_shell`, `ignore_scripts`, `prefix`, `userconfig`, and `globalconfig` can alter the reviewed build/install command. Specify an allowlisted child environment (or remove all case-insensitive npm config/lifecycle vars and pass validated controlled configs explicitly) and test hostile `script_shell`/`ignore_scripts`; note the outer public `npm run` still needs the body guard above.

GM-04b/c partition otherwise looks coherent; docs updates are correctly scoped but should explain ignored lock/stage recovery and that hooks are defense-in-depth, not the sole guard.

## Final verdict

CLEAN. Revised PLAN and D-017 close every prior finding: public package-script bodies now unconditionally enter a dependency-light guard even when npm suppresses pre-hooks; pre-hooks are explicitly defense-in-depth; the recursive guard derives policy from forwarded args and the strict/canary/identity four-way matrix is frozen; real missing-pin setup plus strict verification runs in Windows CI; lock/stage names gain exact ignore parity plus token/physical ownership cleanup and documented crash-left manual recovery; and child Git/npm/build processes use a minimal allowlisted environment excluding all behavior-changing npm lifecycle/config variables. The Windows design now avoids cmd/npm.cmd entirely by validating npm-cli.js beside real process.execPath and invoking it through that Node executable. D-017 truthfully records both ignore-scripts and Windows rationale. GM-04b mechanism/CI work and GM-04c live repeated/mismatch/final reconciliation remain cleanly separated. No remaining concrete blocker.
