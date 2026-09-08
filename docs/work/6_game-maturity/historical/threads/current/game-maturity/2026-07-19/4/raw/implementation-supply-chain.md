# GM-04b adversarial implementation review - supply-chain lane

- **[HIGH] Existing checkout “cleanliness” is not content authentication.**
  - **Evidence:** `scripts/civ-engine-setup-safety.mjs:162-230` trusts metadata plus `git status`; `scripts/civ-engine-setup-operations.mjs:150-206` subsequently runs npm and the build.
  - **Failure path:** Ignored files such as a pin-local `.npmrc` can remain invisible through `.git/info/exclude`; index `assume-unchanged`/`skip-worktree` flags can conceal modified tracked build or lock files. The audit passes, then npm consumes attacker-controlled config/content before the final digest check.
  - **Smallest fix:** Before every npm phase, independently authenticate the complete non-generated checkout against the pinned tree, reject index concealment flags and unexpected ignored files, and explicitly prohibit a pin-local `.npmrc`.

- **[HIGH] Git still consumes unaudited repository-local configuration before trust is established.**
  - **Evidence:** `scripts/civ-engine-setup-process.mjs:40-88` sanitizes environment variables but does not prevent local config discovery; `scripts/civ-engine-setup-operations.mjs:88-126` runs clone from the root repository and performs checkout before auditing the clone; `scripts/source-provenance.mjs:277-365` executes root Git commands without auditing root `.git/config`, and its diff lacks `--no-textconv`.
  - **Failure path:** Root config can inject `url.*.insteadOf`, HTTP headers/proxies, or `init.templateDir`; template-provided attributes/config can reach checkout filters before the destination audit. Root provenance can also invoke configured textconv/filter programs.
  - **Smallest fix:** Clone from a controlled non-repository directory with parent config discovery blocked and a controlled empty template; audit destination metadata before checkout. Audit root config for executable/filter/textconv/redirect sinks and add `--no-textconv`.

- **[HIGH] Root package validation does not authenticate the npm install graph.**
  - **Evidence:** `scripts/civ-engine-setup-operations.mjs:62-85` checks only `dependencies` and a few lock fields, while `:254-275` performs `npm ci`; unexpected installed entries are detected only afterward at `:367-409`.
  - **Failure path:** Dirty root files can add matching `optionalDependencies`, workspaces, overrides, or extra lock graph nodes while preserving the checked fields. npm may fetch and extract those packages before the post-install audit rejects them.
  - **Smallest fix:** Strictly allowlist every dependency- and install-affecting package field and the complete lockfile package graph, or authenticate the exact package/lock bytes and replace root npm installation with an atomic exact link.

- **[HIGH] The trusted build is cross-platform fragile and reintroduces PATH-based executable selection.**
  - **Evidence:** `scripts/civ-engine-setup-operations.mjs:181-206` uses `npm run build`; `:331-349` gives npm an initial PATH containing only the Node directory; `scripts/civ-engine-setup-process.mjs:33-36` retains caller-controlled Windows `PATHEXT`.
  - **Failure path:** On Ubuntu, npm lifecycle execution resolves bare `sh`, but the sanitized PATH lacks `/bin` and `/usr/bin`, so a missing-pin CI build can fail even though the already-built local fast path passes. npm lifecycle PATH construction also prepends project and ancestor `node_modules/.bin` directories, allowing an ancestor executable to intercept bare commands such as `node`; Windows adds current-directory/PATHEXT search risk.
  - **Smallest fix:** Avoid npm lifecycle execution for the reviewed build. Resolve and validate the exact pin-local TypeScript CLI, invoke it with exact `process.execPath`, fixed arguments, `shell: false`, and a non-searching environment.

- **[MEDIUM] Verification’s lock check is a TOCTOU race.**
  - **Evidence:** `scripts/civ-engine-setup.mjs:34-40` checks absence of the setup lock and then verifies separately; setup may acquire it at `:48-54`. `scripts/civ-engine-guard.mjs:51-60` releases this verification boundary before spawning the guarded command.
  - **Failure path:** A concurrent setup can acquire the lock and mutate generated/runtime paths after guard verification but while the guarded command imports or tests them.
  - **Smallest fix:** Hold a shared verification lease through guarded child completion and require setup to hold an exclusive lease, or redesign all observable replacement as immutable and atomic.

- **[MEDIUM] Canary detection is lexical rather than parser-aware.**
  - **Evidence:** `scripts/civ-engine-guard.mjs:51-53` uses `forwardedArgs.includes("--allow-dirty")`; `scripts/playtest-recursive.mjs:360-376` has options that consume their following token as a value.
  - **Failure path:** `--scenario --allow-dirty` causes the guard to treat a scenario value as the canary and launch the body without strict guard verification. The current body independently rechecks provenance and aborts, limiting present impact, but the public guard contract already fails open and depends on that duplicated defense remaining intact.
  - **Smallest fix:** Share the body’s argument parser with the guard or scan option positions while skipping consumed values.
