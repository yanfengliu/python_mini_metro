"""GM-09c river-crossing geometry (D-035).

Pure, dependency-light: imports only ``geometry.point`` and reads plain
``(left, top, right, bottom)`` river-band tuples (from a ``MapDefinition``) — no
``pygame``, ``shapely``, ``entity``, or ``mediator`` — so it is import-safe for
every headless/RL path and consumed one-way by the mediator, the route-edit gate,
and the renderer.

A crossing is counted on a path's CENTERLINE (consecutive ``station.position``
pairs plus the loop closure), never the lane-offset ``PathSegment`` geometry,
which is ``path_order``-dependent and ``round()``-quantized (non-deterministic
w.r.t. the logical route). So a line's crossing count depends only on its own
stations, and ``available_tunnels`` derived from it needs no snapshot state.
"""

from __future__ import annotations

from collections.abc import Sequence

from geometry.point import Point

Band = tuple[float, float, float, float]


def segment_crosses_band(start: Point, end: Point, band: Band) -> Point | None:
    """Return the ENTRY point where segment start→end first enters the STRICT
    INTERIOR of the axis-aligned ``band`` (Liang-Barsky), or None if it does not.

    STRICT-interior semantics: a segment must actually pass through the band's
    interior to count. A mere grazing touch (a zero-length overlap at a corner) and
    a positive-length overlap that only runs ALONG an edge (collinear with a band
    side) both count as ZERO -- the latter is reachable on the LAKE map, whose
    vertical water edges sit at integer x with no x-erosion of the top/bottom banks,
    so a line between two stations on that exact edge lies on dry land, not in the
    water (review Codex/harness; this supersedes GM-09c's deferral). The test: the
    MIDPOINT of the in-band overlap must be strictly inside the rectangle. A genuine
    crossing's overlap midpoint is interior; an edge-collinear overlap's midpoint is
    on the edge. The returned ENTRY point (for the portal marker) is unchanged for a
    genuine crossing; RIVER/DELTA never place a centerline on an edge, so their
    counts are unaffected."""
    left, top, right, bottom = band
    ax, ay = float(start.left), float(start.top)
    dx, dy = float(end.left) - ax, float(end.top) - ay
    t_enter, t_exit = 0.0, 1.0
    for p, q in (
        (-dx, ax - left),
        (dx, right - ax),
        (-dy, ay - top),
        (dy, bottom - ay),
    ):
        if p == 0.0:
            if q < 0.0:
                return None  # parallel to this edge and wholly outside it
        else:
            r = q / p
            if p < 0.0:
                if r > t_exit:
                    return None
                t_enter = max(t_enter, r)
            else:
                if r < t_enter:
                    return None
                t_exit = min(t_exit, r)
    if t_enter >= t_exit:
        # Empty overlap (miss) or a zero-length grazing touch -> not a crossing.
        return None
    # Strict interior: the overlap's midpoint must be strictly inside, so a segment
    # running ALONG an edge (midpoint on the boundary) is not charged a crossing.
    t_mid = 0.5 * (t_enter + t_exit)
    mid_x, mid_y = ax + t_mid * dx, ay + t_mid * dy
    if not (left < mid_x < right and top < mid_y < bottom):
        return None
    return Point(round(ax + t_enter * dx), round(ay + t_enter * dy))


def _centerline_segments(
    positions: Sequence[Point], is_looped: bool
) -> list[tuple[Point, Point]]:
    segments = [(positions[i], positions[i + 1]) for i in range(len(positions) - 1)]
    # The loop closure adds a NEW segment only for 3+ stations; a 2-station loop's
    # closure RETRACES the single segment, so counting it would double-charge one
    # physical crossing (review Codex).
    if is_looped and len(positions) >= 3:
        segments.append((positions[-1], positions[0]))
    return segments


def path_crossings(
    positions: Sequence[Point], is_looped: bool, rivers: Sequence[Band]
) -> tuple[Point, ...]:
    """Every river-band entry point on the path's centerline (one per crossing)."""
    if not rivers or len(positions) < 2:
        return ()
    crossings: list[Point] = []
    for start, end in _centerline_segments(positions, is_looped):
        for band in rivers:
            point = segment_crosses_band(start, end, band)
            if point is not None:
                crossings.append(point)
    return tuple(crossings)


def within_tunnel_budget(
    host: object, stations: Sequence, is_looped: bool, *, exclude: object = None
) -> bool:
    """The single route-edit gate for both creation and reroute (GM-09c).

    Would a line over ``stations`` (looped or not) fit ``host``'s finite tunnel
    budget? Counts the CANDIDATE line's crossings plus every committed line's
    crossings EXCEPT ``exclude`` (the draft being finished or the line being
    rerouted) and any line still being drafted. A None budget (CLASSIC, or any map
    without rivers) is always within budget. Read-only, so a rejected edit mutates
    nothing; ``available_tunnels`` is derived, so a later removal/reroute refunds
    for free. Reads the host by duck-typed ``getattr`` so this module imports no
    gameplay code and stays import-safe for every headless/RL path. The budget and
    the rivers come from the SAME ``map_definition`` (not a cached ``num_tunnels``
    field), so a swapped map or a host without that field can never fail open on a
    finite map (review Codex).
    """
    map_definition = getattr(host, "map_definition", None)
    num_tunnels = getattr(map_definition, "tunnel_budget", None)
    if num_tunnels is None:
        return True
    rivers = getattr(map_definition, "rivers", ())
    if not rivers:
        return True
    candidate = len(path_crossings([s.position for s in stations], is_looped, rivers))
    others = sum(
        len(path_crossings([s.position for s in path.stations], path.is_looped, rivers))
        for path in getattr(host, "paths", ())
        if path is not exclude and not getattr(path, "is_being_created", False)
    )
    return candidate + others <= num_tunnels
