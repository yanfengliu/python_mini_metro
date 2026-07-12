# GM-01c scope and quality plan review

NOT APPROVED before amendment. Four MEDIUM issues were grounded in the live code.

1. Apply recursive thresholds after `env.reset`, because reset replaces the mediator, and prove this with a replacement-mediator regression.
2. Distinguish affected Node tests, the known 23/42 local pin-mismatch baseline, and the required 42/42 pinned-CI result; update the default-fixture schema assertion too.
3. Preserve the exact config alias and immutable recursive v2 dispatch contract.
4. Record the temporary GM-03 mediator size exception, keep GM-01c mediator changes minimal, avoid adding to the 498-line checkpoint module, and route new tests into focused modules before crossing 500 lines.

First re-review found one remaining MEDIUM wording defect: the amended plan froze the old `23/42` Node total even though new Node tests can raise the total. The gate was amended to require every new test to pass, preserve exactly the known 19 pin-only failures, record the observed total, and require the complete updated suite to pass in pinned CI.

Final amended-plan re-review: APPROVED with no remaining HIGH or MEDIUM defect.
