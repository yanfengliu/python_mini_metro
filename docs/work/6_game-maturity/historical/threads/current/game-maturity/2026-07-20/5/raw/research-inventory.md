# GM-06a inventory and lifecycle research

Live total is `config.num_metros = 4`, copied to writable `Mediator.num_metros`; live `Mediator.metros` starts empty and is consumed by simulation, rendering, structured observation, passenger flow, and replacement as assigned-only entities. Path completion lazily constructs and installs one exact Metro only while `len(metros) < num_metros`; path removal removes route Metros from the global list.

Recommendation: expose a read-only late-derived available count and retain anonymous inventory units. Do not add a pool list, preconstruct Metro objects, or duplicate availability in mutable state. In valid gameplay, available plus assigned equals total and each global Metro belongs to one active path. An artificial direct over-cap mutation clamps available to zero without ejecting existing entities.

Preserve effect ordering and partial failures. Availability changes only when the live global list changes: factory/route-add/pre-mutation append failure returns nothing, append-then-raise consumes one, and removal returns exactly the units actually removed before any later failure. Current detached route graphs and onboard-rider destruction remain unchanged; GM-06d owns the latter.

No files were changed by this research lane.
