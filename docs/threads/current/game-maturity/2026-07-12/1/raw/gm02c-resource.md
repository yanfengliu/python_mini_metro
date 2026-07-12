# GM-02c CI, resource, and documentation finder/refuter

## Findings

1. MEDIUM — default Windows lifecycle asserted only `frameStack == 8`, so an equal-count eight-frame multiscale layout could become the default unnoticed. Add exact default and legacy layout/offset/fingerprint assertions.
2. MEDIUM/LOW — durable STATE/EVIDENCE lagged the live implementation and must be reconciled before Commit A.
3. LOW — the workflow step name omitted the new named-history lifecycle.

Static checks otherwise passed; modules were registered, named fresh/evaluate/resume coverage was sound, files remained below 500 lines, and no temporary outputs remained.

## Final refutation

CLEAN. YAML loads and the full Windows body parses as PowerShell. The renamed step covers recurrent history and legacy PPO; default eight-frame and legacy four-frame lanes now assert exact contiguous layout/offsets plus paired evaluation fingerprints; the named twelve-frame lane retains exact offsets, fingerprint inheritance, parent hashes, tags, and seeds. Cursor/evidence reconciliation landed before Commit A as required.
