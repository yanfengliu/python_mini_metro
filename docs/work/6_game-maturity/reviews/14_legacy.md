# GM-04c review synthesis

Status: the declared local proof and corrected payload passed local review/gates and became evidence Commit A `60ac9530cafff88a8d112040c17631cc6a6528e8`; exact workflow run `29763804498` passed both jobs, evidence-only Commit B is active, and GM-04 remains open with GM-05 closed until B's own exact workflow succeeds

## Baseline

GM-04b is remotely finalized at evidence-only Commit B `41ecfc691ac4d4784acff549f06e3fe2f26e9c3b`. Exact workflow run `29758092140` passed `build` job `88405558876` and `rl-smoke` job `88405560427`, and GM-04c opened only after that result.

## Local proof review

Terminal-observed repeated canonical setup remained stable at the retained exact pin; its stdout was not retained. Terminal-observed canonical guarded `npm test` registered 245 tests, passed 241, reported four expected platform skips and zero failures, and preserved all 44 frozen pre-GM04 names; that console output was not retained.

Clean recursive run `output/recursive/recursive-2026-07-20T16-21-12-855Z-ea664784` completed eight operations with zero findings. The public fresh-process verifier accepted all eight checkpoint/transcript rows with matching final state, findings, and inputs; the resulting `no-fix-candidate` decision closes only the declared GM-04c proof and does not close the broader roadmap.

Strict verification and root resolution retained civ-engine 2.2.0 at commit `e0cb614a516c449159a4562c2ac45bd40bffd3df` and runtime digest `960f4af06a8012298ca7f6fda65e64590a78e059fbe4ca154c0ca5ce33282891`. The root audit remained at zero vulnerabilities, the pin development graph retained the accepted nine moderate dependency instances with zero high/critical, and high-confidence scans of all ten tracked dependency surfaces plus the exact staged 18-path evidence payload found no recognized secret signature.

## Mismatch-drill review

The isolated drill preserved captured expected path `.civ-engine-pin` with the descriptor identity above while redirecting only its task-owned fixture to captured actual path `../civ-engine`, the clean sibling at civ-engine 2.4.1, commit `2632daca2ea1d1330cf1270962941005354f775b`, and runtime digest `8da72fd76e9f513773bb5f63c899321ffd7a9ef6dbb0cf82d2aec3dbba481971`. The independent comparison reported `matches.path: false`, with version, commit, and runtime-digest matches also false.

The terminal-observed public guard exited 1 and contained `[civ-engine-guard] root civ-engine dependency needs repair`; no canonical TAP or frozen-test-name body sentinel appeared, and static guard ordering establishes that verification rejected the mismatch before body spawn. Expected and actual metadata were captured independently; the categorical production diagnostic did not reflect repository-controlled metadata. The drill JSON was ephemeral and was not retained after the fixture cleanup.

Static review of the drill found its mutations bounded to a fresh `C:\tmp` fixture, its Windows junction swap and restoration attributable, its child process fixed to `process.execPath` with `shell: false`, and its cleanup guarded by physical identity and containment checks. The harness copied the complete physical `scripts/` tree rather than only tracked required scripts; the earlier authored synthesis is corrected accordingly. Three verbatim static reviews converge `CLEAN` for controlled execution and identify only the nonblocking boundary that a stalled child or abrupt termination could retain the isolated fixture without threatening production. Those reviewers did not execute the harness and did not approve this tracked payload.

The reviewed harness source was ephemeral and removed after successful execution; its reviewed SHA-256 was `6C09AF80A153969D3E742F43268A7C2AB237E1FEEC1E0DB2FCE0B7E188421CFA`. Line links preserved verbatim in raw reviews are historical and no longer resolve.

The isolated fixture was removed. Production Git HEAD/status and root pin resolution plus the retained pin and sibling fingerprints remained unchanged.

## Commit A payload review and disposition

Two independent initial payload reviews blocked delivery on omitted expected/actual paths and `matches.path: false`, credential evidence scoped too narrowly to the documentation payload, an authored synthesis that understated the complete physical `scripts/` copy, an incomplete ephemeral harness-source boundary, and claims stronger than the diagnostic/sentinel and Git-status evidence. Every finding was accepted and corrected: path/version/commit/digest comparisons are explicit; all ten tracked dependency surfaces and the current payload were scanned and rerun after exact staging; the complete physical scripts copy is stated; the removed harness SHA, historical raw links, static-only reviews, and nonblocking timeout/residue boundary are explicit; and guard/body plus integrity wording is narrowed to observed sentinels, static ordering, Git state, link resolution, and fingerprints. Both fresh re-reviews are `CLEAN`. The acceptance review's verbatim 16-path count was correct before preserving it as the seventeenth path; preserving the evidence-focused final review produces the exact 18-path delivery allowlist.

## Limitations and disposition

Safe cleanup remains limited for four old ignored output pre-commit cache roots whose descendants are ACL-blocked: `output/gm04a-precommit-cache`, `output/gm04b-a3-precommit-cache`, `output/gm04b-final-precommit-cache`, and `output/gm04b-precommit-cache-final2`. The exact task cache `C:\tmp\python-mini-metro-gm04b-precommit-cache` was removed after the final Commit B hook run.

The local proof and corrected payload are locally approved. Commit A is committed, pushed, and remotely green; GM-04 remains in progress until evidence-only Commit B passes its own exact remote workflow.

The exact staged allowlist contains 18 paths, 248 insertions, and 17 deletions at the pre-commit checkpoint. Cached path equality, full diff review, whitespace checking, credential and dependency-surface scans, forbidden-path exclusions, and absence of unstaged tracked drift all pass; only the pre-existing `.agents/` tree remains untracked.

## Remote Commit A gate

Evidence Commit A `60ac9530cafff88a8d112040c17631cc6a6528e8` passed exact workflow [run 29763804498](https://github.com/yanfengliu/python_mini_metro/actions/runs/29763804498), run number 128. Exact-head `build` job `88424781541` succeeded from 17:28:21Z through 17:32:41Z, and exact-head `rl-smoke` job `88424781562` succeeded from 17:28:22Z through 17:32:41Z. Both job records name the exact Commit A SHA and passed every configured step.

Evidence-only Commit B records this result without changing production. It has no remote result yet and does not open GM-05 before its own exact workflow succeeds.
