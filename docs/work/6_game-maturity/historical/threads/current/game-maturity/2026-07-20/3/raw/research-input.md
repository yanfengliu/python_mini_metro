# GM-05b input-convention research

Recommended gesture: press and hold an assigned colored line button, drag through the desired station order, and release on the final station. This is the smallest compatible interaction.

The live input path currently gives assigned buttons no mouse-down behavior and gives held motion no behavior outside path creation, while mouse-up on an assigned button removes it. A real pygame-event probe confirmed button-down through station motions to station-up is currently a complete no-op, and bare mouse-up still removes the line.

The same DOWN/MOTION/UP actions already exist for pixel policies, so no action-schema change is needed. The route draft should remain facade-owned and off-live, and the stateless InputCoordinator should clear it before calling the existing public replacement hook.

The lane also reproduced the required adjacent renderer fix: physical metro pose `(622.5, 818.5)` and retained-edge rebind from index 0 to 2 became immediate no-tick display pose `(544, 942)` because the interpolator trusted the preserved path ID. Recording the exact current segment in bounded snapshots and rejecting stale cached topology is the smallest robust correction.

Recommended tests cover linear/loop real events, structured/manual checkpoint equivalence, compatibility deletion/purchase/speed/creation paths, invalid/unsafe/exception cleanup, deterministic observational previews, zero-step continuity, next-step interpolation resumption, and one low-level PlayerPixelEnv redraw.

The event converter currently discards the pygame button number. Tests should send button 1, but strict left-button modeling is a separate event-schema change and is outside GM-05b.
