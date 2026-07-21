# GM-06c implementation review - simulation, rendering, and UI

Status: iterative `NOT CLEAN` findings, all returned for test-first correction.

- Real `Path.move_metro` terminal arrival was not always recognized as a turnaround.
- Bent terminal interpolation could collapse a two-body hairpin.
- An adjacent-only correction still allowed a four-body overlap.
- A six-carriage folded route let nonadjacent bodies 3 and 5 shrink from safe 69.6516/140-pixel endpoint distances to 1.8845 pixels at alpha `0.31`.
- A greedy all-pair projection could violate an earlier constraint even when the complete system was feasible.
- Fixed-radius difference constraints can be infeasible on a production-shaped folded route; iteration exhaustion returned unsafe positions without a postcondition.
- Dykstra correction vectors could limit-cycle on a canonical seven-carriage real terminal arrival and raise only at alpha `0.11`, while neighboring frames remained finite.

Each exact reproducer is retained as a regression. The final design uses feasibility-checked radial expansion, cyclic halfspace projection, a convergence cap, and a Cartesian all-pair postcondition.
