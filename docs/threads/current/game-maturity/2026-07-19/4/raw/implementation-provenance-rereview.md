# GM-04b implementation provenance re-review finding ledger

Record type: parent-recorded finding ledger reconstructed from the accepted reviewer findings because the exact reviewer response was not available to this implementation lane; this is not represented as verbatim reviewer output.

Verdict at receipt: BLOCKED

## [HIGH] Git status metadata could conceal changed source bytes

Evidence: with `core.trustCtime=false` and `core.checkStat=minimal`, a relevant source file could be replaced with different same-length content and have its original atime and mtime restored; Git status stayed clean, `captureSourceState` accepted the changed inventory SHA, and `assertSourceStateAllowed` did not reject it.

Required disposition: reject status-cache weakening keys and independently reconcile every relevant working-tree byte snapshot against the authenticated `HEAD` tree, including deterministic added, deleted, and renamed evidence plus the repository's safe LF/CRLF equivalence.

## [HIGH] Root Git failure diagnostics reflected repository-controlled config values

Evidence: an otherwise allowed local config containing `repositoryFormatVersion=1` and `extensions.objectFormat=ROOT_CONFIG_SECRET` reached Git, whose failure output was copied into `processFailure` and exposed the secret through the thrown diagnostic.

Required disposition: make all read-only Git failures categorical while preserving only a safe phase and numeric exit status; never include child stdout, stderr, or spawn error text.

## [HIGH] Engine attributes could activate a configured filter and leak its name

Evidence: a pin-root `.gitattributes` entry `* filter=PIN_ATTRIBUTE_SECRET` combined with the previously allowed `filter.<name>.required` setting reached engine Git and reflected the attacker-controlled filter name in the unavailable-state error.

Required disposition: before every engine Git call, authenticate the only accepted root attributes policy (`* text=auto`) or fixture absence, reject any other behavior-changing worktree or local-info attributes, and expose only a categorical unsafe-metadata result.

## [HIGH] Engine unavailable-state summaries copied arbitrary exception messages

Evidence: `captureCivEngineState` copied `error.message` into its public unavailable summary, so runner failures and filesystem diagnostics could disclose attacker-controlled config values or paths even when the initiating command itself failed closed.

Required disposition: map capture phases and known error codes to fixed public categories, retaining a numeric Git status when present but never the original exception message.

## Related supply-chain re-review finding

The separate supply-chain re-review found that the read-only runner's default repository-owned `.git-read-home` let the repository supply both `gitconfig` and `$HOME/.config/git/attributes`; those inputs could activate a clean filter before provenance completed. Its accepted correction belongs to the same read-only Git boundary: default HOME, USERPROFILE, global config, and hooks use the OS null device, system attributes are disabled, inherited HOME/XDG/config variables are dropped, and setup-only Git receives an explicitly owned transaction home.

## Fresh final re-review finding ledger

Record type: parent-recorded finding ledger reconstructed from the accepted final-review findings because the exact reviewer response was not available to this implementation lane; this section is not represented as verbatim reviewer output.

Verdict at receipt: BLOCKED

### [HIGH] Engine info excludes could conceal untracked files

Evidence: `auditEngineGitMetadata` authenticated `.git/info/attributes` but only checked that `.git/info/exclude` was physical. An active exclude pattern could therefore hide an untracked engine file from status while the capture remained clean.

Accepted disposition: reject every non-comment `.git/info/exclude` pattern categorically before each engine Git call; the TDD sentinel adds the pattern after the first audit, proves the first status can conceal the file, and proves the second Git is stopped by re-audit without reflecting the pattern.

### [MEDIUM] A stable state could be paired with a transient diff

Evidence: one capture could record state A, generate its patch while the filesystem transiently held state B, then confirm state A and return the B patch because only the two state summaries were compared.

Accepted disposition: require two consecutive identical stable state-plus-diff candidates within the existing three-attempt bound; a one-time A/B transient is discarded and the returned diff agrees with A.

### [MEDIUM] Outer source state lacked fresh-capture integrity

Evidence: the nested engine state had WeakMap snapshot protection, but the enclosing source object could be shallow-forged or mutated while retaining the original fresh engine object and still reach policy checks.

Accepted disposition: register every direct and diff-decorated source capture against a structured-clone WeakMap snapshot, reject parsed, cloned, forged, or mutated outer objects at policy, artifact-write, and recapture boundaries, and retain summary parsing for persisted evidence.

### [MEDIUM] Filesystem Git config rejection reflected identifiers

Evidence: the filesystem audit removed config values but still included classified section/key names and syntax line details in its error, allowing a repository-controlled section identifier to reach diagnostics.

Accepted disposition: every unsafe or unsupported local Git config now returns one fixed `source Git metadata rejected: unsafe local Git config` category; the TDD matrix verifies the injected section identifier and command value are both absent.

### File-size remediation

`scripts/source-provenance-engine.mjs` exceeded the preferred 500-line boundary. The fixed unavailable-reason mapping now lives beside the engine Git safety audit in `scripts/source-provenance-engine-safety.mjs`, reducing the engine module to 482 lines without changing its exported behavior.
