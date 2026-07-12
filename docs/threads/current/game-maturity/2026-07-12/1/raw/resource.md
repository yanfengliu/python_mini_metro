# Initial review

1. HIGH — the original fallback was impossible because only the twelve-frame candidate had more than eight samples. If it fails, keep GM-02d open and profile a preregistered greater-than-eight fallback or rerun all matched candidates under a reduced rollout contract.

2. MEDIUM — preregister numeric gates before observing results. A defensible gate is median aggregate working-set peak at most 1.25 times a freshly remeasured 8-contiguous baseline and below the prior rejected 3.909 GiB batch-256 peak, plus median end-to-end throughput at least 0.75 times baseline, all repeats green, and batch 64 unchanged.

3. MEDIUM — sum current working sets across the live process tree at each sample rather than summing nonsimultaneous per-process peaks. Record discovery and a sample interval no greater than 100 ms. The exact RL venv has no psutil, so use a tested dependency-free Windows supervisor. Do not infer absence of paging from working set or generic page-fault counts.

4. MEDIUM — require at least three fresh-process repeats per candidate in counterbalanced order. Run controls through the new wrapper, use a 1,024-transition warm-up collection/update and a measured 1,024-transition collection/update, and report collection, optimizer, and end-to-end rates separately with setup time excluded.

5. MEDIUM/LOW — record actual rollout-buffer and ring nbytes, output/padded minibatch shapes and bytes, and instantiated parameter count in addition to analytical values.

6. LOW — GM-02d promotes an engineering-safe observation contract, not proven delivery improvement; efficacy belongs to GM-12.

Live resource math: 8-contiguous uses a 486 MiB raw rollout, 3.796875 MiB ring, 121.5 MiB float32 batch-64 tensor, 364,960 CNN parameters, and 1,478,933 full policy parameters. Eight-multiscale keeps the output/buffer/model sizes but uses a 61.224609 MiB ring. Twelve-multiscale uses a 729 MiB rollout, the same 61.224609 MiB ring, a 182.25 MiB float32 batch-64 tensor, 389,536 CNN parameters, and 1,503,509 full policy parameters. Weights are negligible relative to rollout and minibatch storage. No files were edited.

# Re-review

APPROVED — all resource/default-promotion findings are resolved. The revised plan makes both eight-frame controls ineligible, declares a ten-frame fallback or full matched rerun, preregisters numeric memory/throughput gates, defines the instantaneous process-tree metric and sampling interval, requires repeated counterbalanced fresh processes and separate rates, checks actual allocations, and reserves passenger-delivery efficacy for GM-12. No remaining substantive finding.

# Implementation finder and re-review

MEDIUM — the initial provenance regression created the two new identity-bearing modules but did not independently mutate each to prove that dropping either allowlist entry would fail. LOW — the v2 malformed cases lacked one missing required top-level key and one unknown top-level key. All other architecture, dependency, allocation, file-size, docs, and regression-quality checks were clean; focused exact-RL passed 49/49.

APPROVED after fixes. The training-fingerprint test mutates each identity module independently and restores baseline, the content-fingerprint test mutates both trainer-only modules without changing content identity, and v2 tests directly remove `history` and add unknown `future`. Targeted exact-RL passed 3/3. No remaining defect and no edits.
