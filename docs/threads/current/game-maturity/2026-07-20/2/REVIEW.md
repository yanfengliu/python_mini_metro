# GM-05a review synthesis

Status: complete and `CLEAN`; implementation Commit A `c7effd8365ab47454f3a722befadab488ae5f550` passed exact workflow run `29776047898`, and evidence-only Commit B `47b93491662ebe56a38aba8653d868ae66249d6c` passed exact workflow run `29776631928`

The pre-plan live-code audits converged on strict selector and unique-station rules, off-live geometry, semantic metro rebinding, global waiting replanning, deferred onboard replanning at a retained safe alight, exact rollback including RNG, and direct identity tests in addition to checkpoint/replay equality.

The implementation avoids a new hidden pending set or checkpoint schema by reducing each onboard plan to a one-alight marker using existing checkpoint-visible fields. It rejects removal of an edited-line rider's target alight, maps moving padding only across the same retained transition, reconstructs stopped metros from their arrival edge before selecting candidate post-arrival state, and mutates live topology only after whole-network preflight plus exact off-live candidate validation.

Initial plan reviewers correctly found that every binding category needs all-candidate ambiguity handling; invariant checks must precede a no-op; moving positions need an on-segment proof; marker Nodes must come from the committed fresh graph rather than the old route; rollback claims must match the standard effect surface; network-wide marking requires network-wide holder/plan validation; preflight must not call the mutating plan getter; global waiting refresh needs a stable captured batch; marker alights need a scoped planner rather than repeated global bulk passes; and the action/factory/file-size/gate/docs contracts needed exact wording. Corrected-plan review additionally caught pre-guard legacy boarding evaluation that can consume Python RNG at a full station and required one exact private late-bound scoped-replanner boundary shared by replacement and alight handling. All findings were accepted and resolved before production work.

Implementation review then found that malformed candidates needed complete list-container and canonical geometry validation; preflight needed broader live topology, holder, node-list, and cross-storage alias rejection; exact rounded angled and zero-length geometry needed production-constant parity; shared segment, internal point/line, station-position, malformed numeric, Boolean, non-finite, and overflow inputs needed fail-closed coverage; the scoped passenger operation needed a direct contract with four-field marker clearing before late resolution; rollback needed a second-waiter fault after one successful replan; and all changed handwritten files plus public documentation needed an explicit size/truthfulness audit.

Every implementation finding was accepted. The transaction now rejects all confirmed alias and malformed-geometry reproducers off-live, accepts genuine production NumPy real coordinates, validates the complete canonical segment interleaving and style, preserves the target's five list identities, clears marker fields before resolving the scoped planner, and restores exact state after a first-waiter success followed by a second-waiter failure. Reviewer-driven regressions expanded the focused surface from the original 27 red methods to 40 green methods across five modules.

Final implementation lane results are `CLEAN`: API/action/checkpoint/replay passed 40 focused and 89 adjacent tests; passenger/RNG/rollback passed 73 GM-05a and adjacent passenger tests; metro/topology/geometry/atomicity passed all 40 focused tests. Each lane also passed its relevant Ruff check and format checks; every focused helper and test file is under 500 lines, while the explicit 652-line Mediator facade remains below the 1,000-line hard ceiling. The final parent run passed 622 tests in 7.257 seconds with 12 expected optional-stack skips, and all 12 changed Python files passed Ruff check and format validation.

The exact static logical and rounded segment geometry assertions are sufficient for GM-05a's programmatic scope: they compare candidate/live station, path, padding, endpoint, order, and width semantics while separately proving unchanged metro pose. GM-05b retains the explicit obligation to inspect selected-line redraw and interpolation-frame continuity.

The canonical Node suite was not rerun for this non-loop work unit because a pre-existing concurrent `.civ-engine-setup.lock` lease refused setup; no unrelated process or lock was terminated. AGENTS requires that suite for loop-machinery changes, which GM-05a does not contain. EOF, trailing-whitespace, Ruff, and Ruff-format hooks plus cached staging audits passed on the exact 35-path Commit A payload. Exact hooks/cached audits for the four-document Commit B payload and B's own remote workflow remain delivery gates.

The public multi-CLI workflow was not retried because the established repository-export authorization boundary has not changed. The independent lanes are compensating in-process review only; no external reviewer has read or approved GM-05a. Available verbatim reviewer outputs plus the passenger lane's explicitly labeled recovered summaries are preserved under `raw/`.

## Remote Commit A gate

Implementation Commit A `c7effd8365ab47454f3a722befadab488ae5f550` passed exact workflow [run 29776047898](https://github.com/yanfengliu/python_mini_metro/actions/runs/29776047898), run number 130. The exact-run watcher exited successfully after exact-head `build` job `88465530550` and exact-head `rl-smoke` job `88465530480` passed every configured step.

Evidence-only Commit B records this result without changing production. It has no remote result yet and does not open GM-05b before its own exact workflow succeeds.

## Remote Commit B gate

Evidence-only Commit B `47b93491662ebe56a38aba8653d868ae66249d6c` passed exact push workflow [run 29776631928](https://github.com/yanfengliu/python_mini_metro/actions/runs/29776631928), run number 131. Exact-head `build` job `88467464598` and exact-head `rl-smoke` job `88467464551` both passed. GM-05a is remotely finalized; iteration 3 reconciles this result before GM-05b production work.
