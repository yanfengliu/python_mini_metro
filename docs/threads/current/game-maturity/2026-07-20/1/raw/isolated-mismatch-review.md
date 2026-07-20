# Isolated mismatch drill review

Review type: static live-harness review performed before the task-owned isolated execution; this is not an external review and does not approve the tracked GM-04c documentation payload.

Result: `CLEAN` for the declared harness scope.

The harness copied the complete physical `scripts/` tree plus the physical package, lock, and `.npmrc` surfaces into a fresh task-owned `C:\tmp` fixture, changed only that fixture's root dependency junction, and used the production repository, retained pin, and sibling as read-only provenance inputs.

The Windows junction transition used rename plus junction creation inside the fixture, checked targets, restored attributable state, and removed only after physical identity and contained-reparse checks. The child invocation used exact `process.execPath`, `shell: false`, bounded output, and explicit error/signal/status handling.

The proof required exit status 1, presence of categorical diagnostic `[civ-engine-guard] root civ-engine dependency needs repair`, and absence of canonical TAP and frozen-test-name body sentinels. Expected and actual path, version, commit, and runtime digests were independently captured rather than inferred from or reflected through that diagnostic.

Expected descriptor: captured path `.civ-engine-pin`, civ-engine 2.2.0, commit `e0cb614a516c449159a4562c2ac45bd40bffd3df`, runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`.

Actual isolated target: captured path `../civ-engine`, clean sibling civ-engine 2.4.1, commit `2632daca2ea1d1330cf1270962941005354f775b`, runtime digest `8da72fd76e9f513773bb5f63c899321ffd7a9ef6dbb0cf82d2aec3dbba481971`; independent comparison reported `matches.path: false` and false version, commit, and runtime-digest matches.

Observed result: terminal output showed guard exit 1 containing the categorical diagnostic, with no canonical TAP or frozen-test-name body sentinel; static guard ordering established rejection before body spawn. The independently captured metadata established the mismatch; production state remained unchanged; the exact fixture was removed. The drill JSON and reviewed harness source were ephemeral and are not represented as retained artifacts; the removed source's reviewed SHA-256 was `6C09AF80A153969D3E742F43268A7C2AB237E1FEEC1E0DB2FCE0B7E188421CFA`.
