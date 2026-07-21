# GM-06b explicit fleet assignment diff ledger

Status: the reviewed implementation and local gates are complete; the exact payload is ready for Commit A

## Intended production surface

- Add one stateless fleet-management boundary, public facade methods, strict actions, and visible plus/minus controls.
- Remove transitional automatic allocation; support multiple locomotives, empty moving queued return, and compositional redistribution over canonical collections.
- Add visible queue state to Metro rendering and structured observation without changing PlayerPixel info or low-level actions.
- Add explicit checkpoint v3, recursive-input v4, and agent-play v4, index-only persisted fleet actions, a shared pre-tick legacy adapter, exact old-version fixtures, and Node v4 replay projection.

## Intended evidence surface

- Preserve three research reports and three first-pass plan reviews; require three clean re-reviews before red tests.
- Add focused red/green fleet transaction, timing, boarding, terminal settlement, gesture-matrix, multi-queue presentation, quantized controls, pixels, checkpoint prefix/suffix, recursive/agent timing, Node verifier, demonstrator, line-count, and compatibility tests.
- Update public/project docs, parent state/decision/evidence, GM-06a downstream reconciliation, and this iteration's reviewed raw evidence.

No production behavior changed before the recorded combined red. The final payload adds `src/fleet_management.py`, `src/fleet_input.py`, `src/recursive_checkpoint_schema.py`, and `src/ui/fleet_button.py`; integrates their narrow boundaries across the existing facade, environment, rendering, recursive, agent, and demonstrator surfaces; updates frozen fixtures and affected legacy tests; and documents the player/programmatic contract. The definitive local suite passes 825 tests with 12 expected skips, the GM-06b lane passes 72 Python plus four Node tests, and the canonical Node suite passes 245 of 249 registered tests with four platform skips. All changed Python files and exact-file hooks pass, and the three implementation reviews are clean after three accepted test-first fixes. The exact 88-path stage has 4,882 insertions and 313 deletions with zero forbidden paths, high-confidence credential matches, or unstaged tracked drift; Commit A and remote evidence remain to be recorded only after they exist.
