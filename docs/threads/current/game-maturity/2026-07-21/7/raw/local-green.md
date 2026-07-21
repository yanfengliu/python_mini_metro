# GM-06c final local product evidence

- Focused GM-06c discovery: 172 tests passed.
- Definitive py313 suite: 998 tests passed; 12 expected optional-stack skips.
- Adjacent GM-06b/GM-06c Node replay contracts: 8 tests passed.
- Changed-Python Ruff check: 84 files passed.
- Changed-Python Ruff format check: 84 files already formatted.
- Protocol fingerprint: `69c604ac62d46d4a2339b3efad239372c61d0eb52e45ce6c9b6cf8da946dea8f`.
- Default-task fingerprint: `719362078a7d98f1e3c944a6a797f7147b29383495f37f417aa9d61e3416016d`.
- Fidelity-task fingerprint: `cd713a6891d8e74dab1aac2ded2edc88a727cb2b5b420948c65731d3a0eb3418`.
- Environment-content fingerprint: `15b1a6ff56e74627803bce02b964cb5915afa9b65e13cd38d8621f894d398ffd`.
- Canonical-LF training-source fingerprint remains covered at `f6fa3ad50bb992152ea0f24dff35603e8e906714cf58c5fcc359ede4af54f65c`; the live mixed-line-ending checkout reports the intentionally raw-byte-sensitive value `b195946ef62db7058b5ff8c295045d285019cce10b2a12d8b86d28f180670f93`.
- Frozen checkpoint-v3: 16,262 bytes, SHA-256 `9ca2f5bce174a8c59c608cb08bc3e5903151ab0ad04df6553c21f166bed63c02`, zero carriage returns, final LF.
- Frozen recursive-v4 input: 1,608 bytes, SHA-256 `807429bf99283a79341c1e78d4984880ec53deaccab1d5bc36ec2b4cf9610cee`, zero carriage returns, final LF.
- Frozen pre-carriage outcomes: 6,486 bytes, SHA-256 `d070943f3de09df8cb18ef6e96caea875dd72541f5b5598c669e35563459e67a`, zero carriage returns, final LF.
- Every changed handwritten production file is below 500 physical lines except the explicit 757-line Mediator facade, below its 1,000-line ceiling.

The archived GM-03f differential was not freshly executed because the required isolated `C:\tmp` output write was rejected at the exhausted approval-usage boundary. Canonical guarded `npm test` was not run because the pre-existing unowned civ-engine setup lock was preserved. No pass is claimed for either unavailable gate.
