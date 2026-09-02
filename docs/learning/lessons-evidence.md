# Lessons evidence

The war story and the anchor behind every rule currently queued in [lessons.md](lessons.md). Not session-start reading — open an entry when its rule is in doubt, or when the work is in that area.

An entry with no anchor is folklore. Entries are corrected in place as understanding improves, with the correction dated; deletion is reserved for a lesson that has become a gate, and it is deleted in the same commit as the gate that replaced it.

Where an entry's knowledge outlived its prose, it did not evaporate: the gate carries the claim in its own header, [gate-proofs.md](gate-proofs.md) records the mutation that proved the gate, and anything with no mechanical trigger is in [canon-candidates.md](canon-candidates.md) or [../policies/local-rules.md](../policies/local-rules.md).

---

## Anchor text edits to the file's real bytes

**Anchor:** 2026-08-14; the GIF save block in `scripts/bc_spatial.py`, which collected frames for a full run and silently wrote nothing.

**Gate it is waiting for:** repo-wide line-ending normalisation plus a test asserting every tracked `.py` uses one line ending. That removes the class instead of describing it, and it is a separate change: it rewrites every file in the tree and rotates the training-source fingerprint, so it does not belong inside an unrelated commit.

Programmatic edits failed repeatedly in one session for two reasons, both silent. These files are mixed line-ending, so an anchor string built with `\n` never matches a CRLF file and the patch reports "anchor not found" at best — or, when several edits are batched before a single write, discards the edits that *did* apply. And `ruff format` may already have rewritten the exact line being matched, so an anchor copied from memory of the pre-format source no longer exists.

The GIF case is the one that cost real work: the save block's anchor had been reformatted, the edit silently never applied, and a full training run finished having captured frames it never wrote.

Measured again on 2026-09-02: `src/rl/semantic_env.py`, `src/rl/protocol.py`, `src/rl/event_gate.py` and `scripts/train_semantic.py` are CRLF while `scripts/search_policy.py`, `src/rl/shaping.py` and `src/rl/model.py` are LF, and a multi-line `\n` anchor silently matched zero times against `scripts/train_semantic.py`. The repo already pays for the mixed state elsewhere: `test/test_gm06b_fleet_player_pixels.py` normalises CRLF to LF into a temporary checkout purely to get a stable training fingerprint.

What works until the gate lands: read the file, detect its line ending from its own bytes, assert each anchor immediately before its own write rather than batching, and re-read after any formatter run.

---

The other 22 entries this file held on 2026-09-02 were retired alongside their rules.
