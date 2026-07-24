"""Weekly upgrade offers (GM-10b / D-042).

At each GM-10a week boundary the interactive game presents a small SET of upgrade
offers. This module owns the OFFER DATA MODEL and a PURE, deterministic generator;
it deliberately imports only the standard library (no pygame/mediator/entity/config)
so it stays import-safe on every headless/RL path with no import cycle.

GM-10b generates offers only; APPLYING a chosen offer is GM-10c, the per-kind
effects are GM-10d-g, and replay/persistence reconciliation is GM-10h. The offer
RNG is supplied by the caller (the mediator derives a per-week `random.Random`
read-only from the already-persisted gameplay RNG state, so offers are
Continue-exact without any new persisted state); this module never seeds itself.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum


class OfferKind(Enum):
    """The kinds of upgrade a week boundary can offer (effects land in GM-10d-g)."""

    NEW_LINE = "new_line"
    LOCOMOTIVE = "locomotive"
    CARRIAGE = "carriage"
    TUNNEL = "tunnel"


_KIND_LABELS: dict[OfferKind, str] = {
    OfferKind.NEW_LINE: "New Line",
    OfferKind.LOCOMOTIVE: "+1 Locomotive",
    OfferKind.CARRIAGE: "+1 Carriage",
    OfferKind.TUNNEL: "+1 Tunnel",
}


@dataclass(frozen=True)
class Offer:
    """One immutable upgrade offer: its kind and the human label to display."""

    kind: OfferKind
    label: str


def describe(kind: OfferKind) -> Offer:
    """The canonical Offer for a kind (its fixed display label)."""

    return Offer(kind=kind, label=_KIND_LABELS[kind])


# EXPLICITLY-ORDERED candidate pools so `random.sample` draws deterministically for
# a given RNG state. TUNNEL is offered only on a map with a finite tunnel budget
# (a bounded map); on the open CLASSIC map (unbounded, `num_tunnels is None`) a
# tunnel grant is meaningless, so it is excluded.
_BOUNDED_POOL: tuple[OfferKind, ...] = (
    OfferKind.NEW_LINE,
    OfferKind.LOCOMOTIVE,
    OfferKind.CARRIAGE,
    OfferKind.TUNNEL,
)
_CLASSIC_POOL: tuple[OfferKind, ...] = (
    OfferKind.NEW_LINE,
    OfferKind.LOCOMOTIVE,
    OfferKind.CARRIAGE,
)


def generate_offers(
    rng: random.Random, *, count: int, tunnels_bounded: bool
) -> tuple[Offer, ...]:
    """Draw ``count`` DISTINCT upgrade offers from the map-appropriate pool.

    Pure and deterministic: the ONLY randomness consumer is ``rng`` (the caller
    owns seeding). ``tunnels_bounded`` selects the pool -- the four kinds on a
    finite-tunnel map, the three non-tunnel kinds on an unbounded (CLASSIC) map.
    """

    if count < 1:
        raise ValueError(f"count must be a positive number of offers, got {count!r}")
    pool = _BOUNDED_POOL if tunnels_bounded else _CLASSIC_POOL
    # `sample` gives DISTINCT kinds (never "+1 Locomotive" twice). The min() clamps
    # a count larger than the pool -- a SILENT cap: harmless at OFFERS_PER_WEEK=2
    # over the 3-kind CLASSIC pool, but a future count > pool would yield fewer
    # offers on CLASSIC. Fine for now; revisit if OFFERS_PER_WEEK grows past 3.
    drawn = rng.sample(pool, min(count, len(pool)))
    return tuple(describe(kind) for kind in drawn)
