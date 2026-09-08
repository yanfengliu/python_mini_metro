# Independent GM-06a inventory plan review

Result: not clean on first pass.

1. Medium - clamped over-cap semantics contradicted the promised one-for-one refund and allocation wording. With total zero and assigned two, removing one Metro leaves availability zero; raising total from zero to one likewise does not permit allocation. The plan must define refunds as decrementing assigned count, with availability rising one-for-one only in a valid non-over-cap state, and directly test `0/2/0 -> 0/1/0 -> 0/0/0`, cap recovery `0/2/0 -> 1/2/0 -> 2/2/0 -> 3/2/1`, and a partial-removal failure after the first actual removal.

2. Medium - legacy HUD facade behavior was identified as a risk but not specified. Existing renderer tests pass states with only legacy delivery and score aliases. The third line needs a deterministic observational fallback, such as deriving from both `num_metros` and `metros` when present and otherwise rendering zero, with text, pixel, and no-mutation coverage.

All other reviewed inventory, ownership, temporary automatic allocation, no-duplicate-checkpoint, and GM-06b through GM-06d boundaries were coherent with live code. No files were edited by the reviewer.
