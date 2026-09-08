CLEAN

Both prior findings are closed in the live A3 code.

- Promotion verification now orders source before destination for directory metadata, child metadata, file bytes, and link realpaths. The three split regressions are causally sound: their synchronization causes the old concurrent implementation to miss each mutation and produce `Missing expected rejection`; current ordering observes each mutation and returns the exact ownership error with `preserveSetupTransaction === true`. The tests also verify retained mutated destination state where applicable.
- `planGitInvocation` now derives synthetic home-relative paths with the selected platform implementation and normalizes hooks with that same separator model. Windows and POSIX target cases pass bidirectionally. A separate same-host parity check confirmed live-host Git config, npm cache, and hooks paths remain unchanged.
- The split verification file is 205 lines, independently discovered by the canonical test glob, and its injection/error assertions prevent incidental earlier failures from passing.

Independent checks:

- Five changed/new JavaScript files passed syntax checks.
- Focused process, promotion, verification, and cleanup suites: 24 registered, 20 passed, 4 expected platform skips, 0 failed.
- Full setup slice: 102 registered, 98 passed, 4 expected platform skips, 0 failed.
- Scoped whitespace checks produced no errors.
- No repository files were modified by this review, and no task-owned temporary fixture remains.
