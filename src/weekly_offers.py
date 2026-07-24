"""Weekly-calendar boundary + offer lifecycle (GM-10a-d), factored out of Mediator.

A thin facade (like `NetworkProgression`/`PassengerFlow`) that owns the week-boundary
HOLD and the offer generate/apply LOGIC while reading and writing the host Mediator's
already-owned state (`steps`, `week_calendar`, `current_offers`, `context`,
`_progression`) -- so week identity, offers, and the offer RNG stay DERIVED from
already-persisted state with no new stored fields, exactly as the in-Mediator code did.

The spy-able steps (`_apply_offer`, `_grant_free_line`, `_offer_rng_for_current_week`)
are invoked through the host, so tests that patch those Mediator methods still
intercept them, and the mediator keeps them as its public seam.
"""

from __future__ import annotations

import hashlib
import random

from config import OFFERS_PER_WEEK, WEEK_LENGTH_STEPS
from offers import Offer, OfferKind, generate_offers

# The pause reason a held week boundary uses; frozen in Mediator._PAUSE_REASONS and
# never cleared by the Space/speed toggles (GM-10a).
WEEK_REASON = "week"


class WeeklyOffers:
    """Own the week-boundary hold + offer generate/apply for a Mediator host."""

    def maybe_hold_boundary(self, host: object, old_steps: int) -> None:
        # GM-10a (D-041): after the COMPLETE tick (post queued-return settlement),
        # hold the "week" pause if the calendar is enabled and this tick crossed a
        # NEW week boundary. Placed LAST in increment_time so settlement is never
        # interrupted, and skipped on game over so a terminal tick promotes to
        # GAME_OVER rather than an offer. WEEK_LENGTH_STEPS >> the max speed (4), so
        # at most one boundary crosses per tick; a frozen tick advances no steps, so a
        # held week never re-triggers (at speed 4 the hold lands at e.g. steps=1202).
        if not host.week_calendar or host.is_game_over:
            return
        if old_steps // WEEK_LENGTH_STEPS < host.steps // WEEK_LENGTH_STEPS:
            # GM-10b (D-042): generate the week's offers BEFORE holding, so they are
            # ready when the modal opens. Read-only derivation (no gameplay draws),
            # gated by the same calendar/crossing/not-game-over guards as the hold, so
            # RL/headless/tutorial never generate and current_offers stays ().
            host.current_offers = self.derive_current_offers(host)
            host.hold_pause_reason(WEEK_REASON)

    def derive_current_offers(self, host: object) -> tuple[Offer, ...]:
        # GM-10b: the current week's offers -- read-only derivation from the
        # already-persisted RNG state + week_index, consuming no gameplay draws. The hold
        # (above) calls it to populate `current_offers` when a boundary is first crossed. On
        # a mid-offer Continue the STORED offers are restored VERBATIM (GM-10i persists them
        # rather than re-deriving, since WEEK_LENGTH_STEPS/OFFERS_PER_WEEK/the pool are
        # provisional GM-11 defaults), so this is NOT re-run at load or serialize.
        return generate_offers(
            host._offer_rng_for_current_week(),
            count=OFFERS_PER_WEEK,
            tunnels_bounded=host.num_tunnels is not None,
        )

    def resolve(self, host: object, offer: Offer | None) -> None:
        # Continue past a week boundary: APPLY the chosen offer (GM-10c), then clear
        # the week's offers and release the pause. A None offer resolves with NO choice
        # (available as API + exercised by tests). NOTE: GM-10i changed the mid-offer
        # window-close to PERSIST the pending boundary (save-schema v4) rather than
        # force-resolve, so `main.run_game` no longer calls this None path. An offer is
        # CONFINED to a genuine pending choice (review MAJOR): only one currently presented
        # at a held boundary can be applied, so no out-of-band call (e.g. a headless
        # MiniMetroEnv with no calendar) can grant an upgrade and bypass the weekly
        # economy. GM-10h reconciles applied-offer persistence across Continue.
        if offer is not None:
            if not (host.is_week_boundary_pending and offer in host.current_offers):
                raise ValueError(
                    "cannot apply an offer that is not a currently-presented "
                    "week-boundary choice: applicable only when it is one of "
                    f"current_offers at a held boundary (got {offer!r}, "
                    f"pending={host.is_week_boundary_pending})"
                )
            host._apply_offer(offer)
        host.current_offers = ()
        host.release_pause_reason(WEEK_REASON)

    def apply_offer(self, host: object, offer: Offer) -> None:
        # Dispatch the chosen offer to its per-kind effect. Each grows a fleet/tunnel
        # quantity by one; the derived readouts (available_locomotives/available_carriages/
        # num_tunnels/available_tunnels) update for free (no cache to refresh, unlike
        # NEW_LINE's button locks), and all four persist via the GM-10h save-schema v3
        # (D-045: grown fleet TOTALS + tunnel_bonus). A future kind without a handler
        # must fail loud.
        match offer.kind:
            case OfferKind.NEW_LINE:
                host._grant_free_line()  # GM-10d
            case OfferKind.LOCOMOTIVE:
                host.num_metros += 1  # GM-10e
            case OfferKind.CARRIAGE:
                host.num_carriages += 1  # GM-10f
            case OfferKind.TUNNEL:
                # GM-10g: TUNNEL is offered only on a bounded map (the pool excludes it
                # on CLASSIC), so the bonus is always reachable when this arm runs.
                host.tunnel_bonus += 1
            case _:
                raise ValueError(f"no effect handler for offer kind {offer.kind!r}")

    def grant_free_line(self, host: object) -> None:
        # GM-10d: the NEW_LINE effect -- unlock the next line for free (no credit spend),
        # capped at num_paths. Mirrors the purchase flow's cache refresh
        # (record_path_purchase -> update_unlocked_num_paths). purchased_num_paths is
        # already persisted, so this is Continue-safe with no schema change (D-044).
        if host._progression.grant_free_path():
            host.update_unlocked_num_paths()

    def offer_rng_for_current_week(self, host: object) -> random.Random:
        # GM-10b (D-042): a dedicated per-week offer RNG, derived READ-ONLY from the
        # already-persisted gameplay RNG state + week_index. getstate() consumes no
        # draws, so the station-spawn stream is byte-untouched; and because that state
        # is restored exactly on Continue, the SAME week's offers reproduce after
        # save/load with NO new persisted state. repr() of the int-tuple state + sha256
        # is deterministic and cross-process stable -- never the salted builtin hash().
        state = host.context.python_random.getstate()
        digest = hashlib.sha256(repr((host.week_index, state)).encode()).digest()
        return random.Random(int.from_bytes(digest[:8], "big"))
