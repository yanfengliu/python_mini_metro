# Recurrent RL framework review

## Verdict

APPROVED after fixes. Three in-process finder/refuter lanes converged with no remaining actionable finding, and the available external Opus reviewer approved the final live code and documentation. Codex and preferred Fable were attempted and their unavailability is preserved verbatim.

## Findings and dispositions

| Severity | Finding | Evidence checked | Disposition |
| --- | --- | --- | --- |
| Medium | The initial test checked the terminal stacked observation but did not prove the horizon marker or recurrent critic bootstrap path | `test/test_rl_training.py`, pinned SB3-Contrib rollout implementation | Fixed with `TimeLimit.truncated` assertion and an end-to-end `predict_values`/rollout-reward regression |
| Medium | `meanDeliveries` could be presented as a final game-over total even when horizon rows were right-censored | `scripts/evaluate_rl.py`, terminal metadata contract | Fixed with game-over/horizon counts and rates, censoring/completeness fields, conditional game-over mean, and exact interpretation text |
| Medium | Evaluation guidance could pseudo-replicate episodes from the same trained policy | `docs/rl-model-selection.md`, cited empirical-RL guidance | Fixed by making trained run/seed the top-level independent unit and specifying paired held-out suites plus run-first hierarchical bootstrap intervals |
| Medium | The callback helper's new default mislabeled legacy PPO checkpoints as recurrent | `src/rl/training.py`, legacy callback integration | Fixed by retaining the historical PPO default while the CLI explicitly passes the resolved algorithm; filename regression added |
| Medium | Current-PPO CI and separate drift tests did not prove the composed pre-recurrent authenticated evaluation path | Manifest, artifact index, exact model bytes, evaluator dispatch | Fixed with a real PPO zip under a historically shaped manifest requiring both drift opt-ins; a genuine July 10 pre-recurrent artifact was also resumed and evaluated successfully |
| Medium | The proposed recurrent batch 256 created material padded-image memory risk | SB3-Contrib recurrent buffer, live process-tree profiling | Fixed with recurrent-only batch 64; feed-forward PPO retains its established preferred batch 256 |
| Low/Medium | `src/rl/training.py` grew to 630 lines and mixed too many roles | Live file boundaries and repo size policy | Fixed by introducing focused `dependencies.py` and `policy.py`; compatibility re-exports and training fingerprint coverage were verified |
| Medium/Low | Missing or unknown termination metadata could coexist with an “all episodes reached game over” interpretation | Evaluation helper and unknown-reason test | Fixed with `terminationMetadataComplete`, `primaryMetricComplete`, and an indeterminate interpretation for unknown metadata |
| Low | `test/test_rl_training.py` exceeded the preferred 500-line boundary | Live file size | Fixed by moving authenticated legacy coverage into `test/test_rl_legacy_compat.py` and adding that module to Windows CI |
| Low | Documentation called batch 256 an ablation although the supported CLI exposes only batch 64 | Policy factory and CLI arguments | Fixed by describing 256 accurately as a rejected profiled former candidate |

## In-process adversarial review

- Recurrent correctness lane verified state/mask behavior, MultiDiscrete support, actual timeout bootstrapping, current fresh/resume dispatch, batch 64, and the unknown-metadata fix. Final verdict: APPROVED.
- Artifact/compatibility lane verified exact indexed bytes, old-PPO drift gates, callback naming, compatibility re-export identity, split-module fingerprint coverage, lock/provenance, and explicit CI inclusion of the moved legacy test. Final verdict: APPROVED.
- Research/documentation lane verified frame and parameter math, measured resource wording, censoring semantics, statistical independence, citations/recommendation fit, and README/architecture/progress alignment. Final verdict: APPROVED.

## External multi-CLI review

- Plan review: Codex was attempted but returned HTTP 401; preferred Fable hit quota; Opus fallback identified five plan gaps. The plan was revised, and a second Opus fallback approved it. Raw evidence is under `raw/plan-*`.
- Final Codex review: Codex CLI 0.144.1 with `gpt-5.6-sol`/ultra was attempted in read-only mode and returned HTTP 401. The exact stderr is `raw/codex.stderr.log`; stdout is retained separately.
- Final preferred Claude review: `claude-fable-5[1m]` returned its usage-limit message in `raw/opus.md`.
- Final fallback review: `opus[1m]` read every scoped live file because its Bash session was unavailable, then returned APPROVED with no High/Medium finding in `raw/opus-fallback.md`. Its low residual about genuine pre-refactor resume was closed afterward using the authenticated July 10 `final-fresh` artifact; its offline citation limitation is covered by the driver's primary-source web verification.

## Residual boundaries

- The implemented hidden/cell state persists within an episode and resets across games and process restarts. Checkpoints persist learned weights, not a mid-game transient LSTM state or full environment snapshot.
- The short lifecycle runs prove plumbing and contracts, not policy quality. Architecture promotion still requires the documented multi-run held-out delivery benchmark.
- Live Node verification remains bounded by unrelated sibling-engine drift; the pinned 2.2.0 acceptance layout is green.
