# GM-04b A3 documentation audit

Documentation audit result: A3 needs cursor/evidence/review updates, but no `README.md` or `ARCHITECTURE.md` contract change.

1. `STATE.md` is materially stale at lines 11–24, 34, 69, and 120–121.

Use wording equivalent to:

> Current status: GM-04a is remotely finalized; corrective GM-04b Commit A2 `16d786098543f32d3b00e8aef37b56a88f67b9a5` made setup/verification pass on Ubuntu and Windows in exact run `29753292420`, and Windows `rl-smoke` succeeded, but Ubuntu `build` failed during canonical `npm test` on two production portability/snapshot-order defects; corrective Commit A3 is active and GM-04c remains closed.

> Durability transaction: failed GM-04b Commits A and A2 are public; A2’s exact-link correction is remotely proved, and corrective A3 is active from `16d786098543f32d3b00e8aef37b56a88f67b9a5`.

> Expected remote implementation baseline: `16d786098543f32d3b00e8aef37b56a88f67b9a5`, whose exact [run 29753292420](https://github.com/yanfengliu/python_mini_metro/actions/runs/29753292420) failed overall after both hosted-platform setup paths succeeded; A3 must correct both downstream Node failures and pass its exact workflow before Commit B.

Set the marker to `[GM-04b:A3]`. Replace resume step 2 with finishing/reviewing/validating the scoped A3 correction, committing/pushing A3, waiting for its exact workflow, and creating B only after green. Update ledger rows 34 and 69 to show A failed, A2 `16d7860` / run `29753292420` failed downstream, and A3 active.

At lines 120–121, record that A3 started from `main == origin/main == 16d7860`; retain `.agents/`, ignored output/pin state, and the sibling outside scope. Replace “GM-04 will isolate” with the current fact that root resolution now targets the retained 2.2.0 pin while the clean 2.4.1 sibling remains untouched.

2. `EVIDENCE.md` needs historical clarification at lines 604 and 613 plus a new A2/A3 section.

Change line 604’s ending to historical wording such as “GM-04c stayed closed; the corrective history follows.” Change line 613’s final sentence to “At that checkpoint, commit, push, and exact remote gates remained pending; their outcome follows.”

Append:

> ## GM-04b Commit A2 - remote setup success and downstream correction

> Corrective Commit A2 is `16d786098543f32d3b00e8aef37b56a88f67b9a5` (`fix: create exact civ-engine root link [GM-04b:A2]`). Exact [run 29753292420](https://github.com/yanfengliu/python_mini_metro/actions/runs/29753292420) proved the missing-only exact-link setup on both hosted platforms: Ubuntu setup/verification passed; Windows setup and strict verification passed; and Windows `rl-smoke` job `88389102133` succeeded. Ubuntu `build` job `88389102169` later failed during canonical `npm test`, so the run was not green and GM-04b remained open.

> Ubuntu exposed two production defects. The win32-injected child-environment contract used host `path.join`, producing mixed separators instead of target-platform Git/npm config and cache paths. Publication verification sampled source and destination directory metadata concurrently, allowing destination mode mutation to occur after the destination snapshot and escape the intended comparison.

> Corrective A3 derives all synthesized child paths with `path.win32` or `path.posix` selected by the requested platform and snapshots source directory metadata before destination metadata. Record the two new regression names, actual focused/full counts, fresh A3 reviews, audits, and staging evidence here after they complete; do not reuse A2’s `239/235` result as A3 validation.

3. Iteration-4 `PLAN.md` is stale at lines 3, 5, and 67.

Update the status with A2 SHA/run and the exact split outcome, set `[GM-04b:A3]`, and make step 6 reflect the real sequence: A failed setup, A2 proved setup but failed downstream, A3 is the current corrective implementation, and evidence-only B waits for A3’s exact green workflow. The frozen contracts at lines 39, 47, and 50 already cover cross-platform controlled paths and complete source/destination mode comparison; no new design decision is needed.

4. Iteration-4 `REVIEW.md` is stale at lines 3 and 49.

Replace the status with the A2 remote outcome and A3-active state. Make line 49 explicitly historical (“At the A2 pre-commit checkpoint…”), then append separate A2-remote and A3-correction paragraphs. State that A2’s clean reviews remain valid only for A2 and are not A3 approval.

Existing raw A2 reviews must remain verbatim. Add fresh A3 records, e.g.:

- `raw/implementation-a3-portability.md`
- `raw/implementation-a3-promotion.md`
- optionally this documentation audit as `raw/implementation-a3-docs.md`

5. `PROGRESS.md` line 132 is still broadly accurate, but A3 is substantive enough for one short additional July 20 bullet:

> Corrected two production defects exposed after the exact-link setup passed on both hosted platforms: controlled child paths now follow the selected platform’s path rules, and publication verification snapshots source-directory metadata before destination comparison so mode drift cannot evade the fail-closed check.

6. `diff.md` should gain one concise A3 bullet:

> Correct target-platform child-path synthesis and serialize publication metadata snapshots, with regressions for both downstream failures exposed by A2’s exact workflow.

7. No changes recommended to `README.md` or `ARCHITECTURE.md`.

`README.md:24–34` already states the intended cross-platform and fail-closed race behavior; A3 makes implementation satisfy that existing public contract without changing commands or recovery guidance. `ARCHITECTURE.md:297` already assigns controlled child environments and complete mode comparison to the correct modules; source-before-destination sampling is an internal ordering fix, not a new boundary or data flow.

One additional truthfulness gap: parent `PLAN.md:5` names goal thread `019f5286-dfca-75e1-9e79-58719dbe1efb`, while `STATE.md:5` names `019f7c1a-897b-7c31-9662-4edbb4e128a6`. If the latter is canonical, label the former as the original thread and add the resumed thread, or update it so the durable documents agree.
