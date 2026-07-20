# Supply-chain plan review

## Initial verdict

NOT CLEAN — two high-severity and four medium-severity plan defects remain.

1. **HIGH — Windows `cmd.exe` boundary reintroduces command parsing.**

Evidence: `PLAN.md:46` invokes `ComSpec /d /s /c call <npm.cmd> ...`. Outer `shell: false` does not prevent `cmd.exe` from reparsing the command; `call` adds a second expansion pass. Repository, staging, and config paths can contain `%`, `!`, `&`, `|`, `^`, parentheses, or whitespace even though CLI arguments are fixed.

Fix: either invoke a validated npm CLI JS entrypoint through `process.execPath`, or specify a dedicated tested `cmd.exe` encoder using `/d /s /v:off /c`, avoid `call` for the sole final batch command, reject CR/LF/NUL, validate absolute `cmd.exe` and `npm.cmd` identities independently of caller `ComSpec`/`PATH`, and prove hostile-path argument round trips.

2. **HIGH — credential sanitization is an incomplete denylist.**

Evidence: `PLAN.md:45` strips variables containing token/auth/secret names. This misses credential-bearing inputs such as `AWS_ACCESS_KEY_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, `SSH_AUTH_SOCK`, credentialed proxy URLs, `.netrc` through `HOME`, certificate overrides, and `NODE_OPTIONS`.

Fix: give every Git/npm/build child a minimal allowlisted environment with controlled empty `HOME`/`USERPROFILE`, npm configs, and temp paths. Explicitly exclude cloud credentials, auth sockets, proxy userinfo, Node preload options, Git/npm injection variables, and CI secrets. Add sentinel-secret tests proving none reach the reviewed build or failure output.

3. **MEDIUM — the exclusive lock is scoped only by the missing-pin state machine.**

Evidence: locking appears at `PLAN.md:32`, beneath “Transactional missing-pin state machine,” while `PLAN.md:25` permits existing-pin rebuild and root reinstall. Two setup calls can therefore concurrently run `npm ci`, rebuild `dist`, or replace root `node_modules`.

Fix: acquire the tokenized lock at the start of every mutating setup invocation, before classifying the pin, and hold it through fast-path validation, rebuild/install, final provenance, and cleanup. Verification-only remains lock-free and may fail safely during active setup.

4. **MEDIUM — staging ownership and cleanup need a realizable two-level design.**

Evidence: `PLAN.md:33-39` describes one staging directory plus ownership token and then cloning into it. A token file makes a clone destination nonempty; an in-memory token alone is insufficient cleanup proof.

Fix: atomically create an ignored owned parent, store the token/sentinel and physical identity there, clone into an empty child, promote only the child, then remove the empty parent. Cleanup must compare token plus physical identity/containment; the lock needs equivalent anti-swap checks.

5. **MEDIUM — verify-only’s no-write promise is not fully pinned.**

Evidence: `PLAN.md:21` promises no filesystem or Git mutation, while `PLAN.md:47` only generally says to harden provenance Git reads. Current `source-provenance-engine.mjs::runGit` invokes Git with ambient behavior apart from `safe.directory`; `git status` can refresh/write the index.

Fix: require `GIT_OPTIONAL_LOCKS=0`/`--no-optional-locks`, controlled config/environment, disabled fsmonitor/hooks, and tests comparing `.git/index` plus repository filesystem state before and after verification.

6. **MEDIUM — “wrong default resolution” is too broad a repair condition.**

Evidence: `PLAN.md:25` permits root reinstall whenever default resolution is absent or wrong. A nested `scripts/node_modules/civ-engine` shadow is wrong resolution but root `npm ci` cannot repair it; setup would mutate root dependencies before eventually failing provenance.

Fix: permit reinstall only for an absent/stale root `node_modules/civ-engine` under a validated physical root container. Any nested or external resolution shadow must fail with zero npm mutation.

The descriptor authority, lifecycle order (`npm ci --ignore-scripts` followed by the intentional build), CI missing-pin dogfooding, and removal of duplicated CI setup are otherwise sound. No files were changed.

## Final verdict

CLEAN. The revised PLAN and D-017 close all six prior findings. CI now dogfoods missing-pin setup on real Ubuntu and Windows runners, and the lifecycle/guard design prevents `ignore-scripts` from bypassing identity checks. No remaining concrete plan blocker. No files changed.
