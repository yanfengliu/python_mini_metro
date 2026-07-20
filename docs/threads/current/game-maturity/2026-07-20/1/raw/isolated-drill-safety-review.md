CLEAN — safe to execute at reviewed SHA-256 `6C09AF80A153969D3E742F43268A7C2AB237E1FEEC1E0DB2FCE0B7E188421CFA`.

- All mutations are confined to a unique, identity-checked `C:\tmp\python-mini-metro-gm04c-*` fixture (lines 84–104).
- The live sibling is only fingerprinted and used as a temporary junction target; no operation targets its contents (lines 54–57, 112–117, 180–182).
- Junction cleanup verifies type and exact target before unlinking, then restores and verifies the fixture-local pin link (lines 128–141).
- Recursive deletion occurs only after fixture identity verification and a complete reparse-target containment walk. An external sibling junction left by any failed recovery blocks deletion and leaves the fixture path reported for manual inspection (lines 147–172, 344–354, 427–434).
- Production root, retained pin, and sibling are re-fingerprinted afterward; fingerprints cover directory identity, package/runtime digests, Git commit/branch, and configured status (lines 180–182, 293–326).
- Provenance claims are appropriately bounded: the guard’s categorical rejection is distinguished from independently captured expected/actual metadata (lines 184–205). The exact diagnostic occurs in guard verification before its spawn boundary; absence of TAP output corroborates that the engine body did not start.
- `node --check` passes. The harness was not executed or edited.
