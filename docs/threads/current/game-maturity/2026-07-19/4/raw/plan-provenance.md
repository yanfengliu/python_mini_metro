# Provenance plan review

## Initial verdict

Verdict: NOT CLEAN — two P1 blockers and two P2 gaps.

1. **[P1] Git is consulted before its metadata is proven safe.**

Evidence: PLAN lines 21, 25–28, 35, and 44–47 promise read-only verification and hardened Git reads, but current provenance invokes `git status` and `rev-parse` with inherited configuration/environment in `source-provenance-engine.mjs:401-449` and `source-provenance.mjs:277-381`. A physical `.git` directory can still contain an executable `core.fsmonitor`/filter, external config include, redirected object alternates, or linked nested metadata. `git status` can also refresh the index unless optional locks are disabled.

Fix: require a filesystem-only audit before any repository-aware Git command. Recursively reject reparse points under `.git`; require physical contained config/HEAD/object storage; reject includes, worktree redirection, executable filters/fsmonitor/hooks, alternates, and external common/object directories. Run both provenance modules through one sanitized Git runner with `GIT_OPTIONAL_LOCKS=0`. Add marker tests proving hostile local config and ambient `GIT_*` values neither execute nor mutate metadata.

2. **[P1] The recursive strict-versus-canary invariant is not frozen by acceptance tests.**

Evidence: PLAN line 52 makes `preplaytest:recursive` unconditionally permissive with `--allow-dirty`, relying on the existing strict gate at `playtest-recursive.mjs:23-35` remaining before dynamic imports at lines 44–45. TDD line 60 and Acceptance line 73 cover only identity failure. A later import-order or policy regression could therefore execute a wrong-commit/version/digest engine during a nominally strict recursive run while all stated tests pass.

Fix: add a sentinel matrix proving strict recursive runs reject dirty status and wrong commit/version/digest before any engine import or body effect; explicit recursive `--allow-dirty` permits only those attributed content differences; both modes reject unavailable, nonphysical, aliased, wrong-root, and wrong-runtime identity; and strict package identity remains non-overridable.

3. **[P2] Windows npm executable identity is underspecified.**

Evidence: PLAN line 46 requires an absolute `npm.cmd`, but does not define its trusted derivation. Resolving it from caller-controlled `PATH` or `npm_execpath` permits executable substitution despite the absolute command passed to `cmd.exe`.

Fix: derive and physically validate `npm.cmd` from the real `process.execPath` installation, validate system `ComSpec`, reject linked/reparse executables, and test exact quoting with spaces and command metacharacters.

4. **[P2] Generated-directory containment tests must be explicitly recursive.**

Evidence: PLAN lines 28 and 59 can be implemented as top-level checks. The live engine’s `prebuild` recursively removes `dist`, while `npm ci` replaces `node_modules`; a physical top-level directory can still contain a nested junction into a sibling.

Fix: recursively `lstat` generated trees before either lifecycle, reject every nested symlink/junction/escape, revalidate immediately before execution, and assert the linked target remains byte-for-byte unchanged.

No files were edited.

## Final verdict

CLEAN. The supersession language is explicit and consistent with D-017 and the revised GM-04b plan. All prior findings are closed.
