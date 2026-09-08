# Rendering change under review

The live uncommitted diff is authoritative. It adds fixed-step session timing, immutable visual route layout, antialiased network caching, render-only metro interpolation, lazy renderer-owned resources, pure draw transforms, first-frame layout preparation, persistent GUI renderer/presentation surfaces, deterministic render-purity coverage, refreshed visuals, and matching architecture/rules/user/progress documentation.

Pre-review validation: 226 Python tests pass. Real software-surface tests prove identical repeated RGBA bytes, unchanged canonical and explicit render-facing state, rendered-vs-never-rendered trajectory equivalence, and one-entry cache reuse. A warmed 1920x1080 fixture rendered 300 frames in 0.4051 seconds.
