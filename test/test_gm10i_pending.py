"""GM-10i contract: PENDING week-boundary offer persistence (save-schema v4, D-047).

A mid-offer save persists the held "week" boundary + the SHOWN offers so a Continue
reloads INTO the modal re-presenting the SAME offers (instead of resolving with no
choice past the boundary). The offers are PERSISTED (a v4 `pendingOffers` key), NOT
re-derived on load: the derivation inputs (`WEEK_LENGTH_STEPS`/`OFFERS_PER_WEEK`/the
pool) are provisional-for-GM-11, so a re-derive would diverge across a balance change
(Codex plan BLOCKER-1). Serialize validates the stored offers == the canonical
derivation (integrity, before the atomic write); load restores them verbatim.
"""

from __future__ import annotations

import copy
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import num_carriages as CONFIG_NUM_CARRIAGES
from config import num_metros as CONFIG_NUM_METROS
from env import MiniMetroEnv
from maps import resolve_map
from mediator import Mediator
from offers import OfferKind, describe
from save_game import serialize_game
from save_load import deserialize_game
from save_schema import (
    SAVE_SCHEMA_VERSION,
    SAVE_SCHEMA_VERSION_V4,
    validate_save,
)

pygame.init()

_FIXTURES = os.path.dirname(os.path.realpath(__file__)) + "/../scripts/fixtures"


def _at_boundary(seed=0, map_definition=None, speed=17):
    kwargs = {"seed": seed}
    if map_definition is not None:
        kwargs["map_definition"] = map_definition
    m = Mediator(**kwargs)
    m.week_calendar = True
    guard = 0
    while not m.is_week_boundary_pending and guard < 6000:
        m.increment_time(speed)
        guard += 1
    assert m.is_week_boundary_pending, "never reached a week boundary"
    return m


class TestGM10iRoundTrip(unittest.TestCase):
    def test_saving_at_a_river_boundary_round_trips_the_pending_offers(self):
        m = _at_boundary(map_definition=resolve_map("river", 1))
        offers = m.current_offers
        self.assertTrue(offers, "a held boundary has offers")
        loaded = deserialize_game(serialize_game(m))
        self.assertTrue(loaded.is_week_boundary_pending, "Continue re-enters the modal")
        self.assertEqual(loaded.current_offers, offers, "same offers re-presented")

    def test_saving_at_a_classic_boundary_round_trips(self):
        # CLASSIC has no TUNNEL in its pool; the restored offers must reflect that.
        m = _at_boundary()
        offers = m.current_offers
        loaded = deserialize_game(serialize_game(m))
        self.assertEqual(loaded.current_offers, offers)
        self.assertNotIn(
            OfferKind.TUNNEL, {o.kind for o in loaded.current_offers}, "no tunnel"
        )

    def test_a_grown_fleet_at_a_boundary_round_trips(self):
        # THE BLOCKER (both plan lanes): a mid-offer save made AFTER earlier upgrades
        # carries a GROWN fleet (numMetros/numCarriages ABOVE config) + a tunnel bonus.
        # The v4 fleet pin must ACCEPT it -- a v3-only gate takes the legacy exact-equality
        # branch and rejects the v4 save, losing the run. A fresh-start test (fleet at
        # config) never exercises this.
        m = _at_boundary(map_definition=resolve_map("river", 1))
        m.num_metros = CONFIG_NUM_METROS + 1
        m.num_carriages = CONFIG_NUM_CARRIAGES + 2
        m.tunnel_bonus = 1
        offers = m.current_offers
        loaded = deserialize_game(serialize_game(m))
        self.assertEqual(
            loaded.num_metros, CONFIG_NUM_METROS + 1, "grown fleet survives"
        )
        self.assertEqual(loaded.num_carriages, CONFIG_NUM_CARRIAGES + 2)
        self.assertEqual(loaded.tunnel_bonus, 1)
        self.assertEqual(loaded.current_offers, offers, "offers re-presented")

    def test_a_speed_four_boundary_round_trips(self):
        # A boundary CROSSED at speed 4 lands PAST the exact multiple (steps=1202), so
        # steps % WEEK_LENGTH != 0 -- the schema/load must not assume an exact landing.
        m = Mediator(seed=0)
        m.week_calendar = True
        while m.steps < 1200 - 2:  # speed 1 up to W-2
            m.increment_time(17)
        m.game_speed_multiplier = 4
        m.increment_time(17)  # W-2 -> W+2, jumping ACROSS the boundary
        self.assertTrue(m.is_week_boundary_pending)
        self.assertNotEqual(m.steps % 1200, 0, "crossed at speed 4, not landed on")
        offers = m.current_offers
        loaded = deserialize_game(serialize_game(m))
        self.assertEqual(loaded.current_offers, offers)


class TestGM10iCrossVersionStable(unittest.TestCase):
    def test_pending_offers_are_restored_verbatim_not_recomputed(self):
        # Codex plan BLOCKER-1: load must NOT re-derive (the derivation inputs are
        # provisional-for-GM-11). Prove it: hand-edit the saved pendingOffers to a
        # DIFFERENT valid pair and confirm the load restores THAT, not a recomputation.
        m = _at_boundary(map_definition=resolve_map("river", 1))
        doc = serialize_game(m)
        # a distinct, pool-valid, consistent pending set (river pool includes all four)
        forced = ["carriage", "tunnel"]
        self.assertNotEqual(
            doc["pendingOffers"], forced, "choose a genuinely different set"
        )
        doc = copy.deepcopy(doc)
        doc["pendingOffers"] = forced
        loaded = deserialize_game(doc)
        self.assertEqual(
            [o.kind.value for o in loaded.current_offers],
            forced,
            "restored the STORED offers, not a re-derivation",
        )


class TestGM10iSerializeGuard(unittest.TestCase):
    def test_a_pending_state_re_saves_without_re_deriving_the_offers(self):
        # Codex impl BLOCKER: serialize must NOT re-derive + demand `== canonical`, or a v4
        # pending save made under OLD rules could not be RE-SAVED once GM-11 retunes the
        # derivation (WEEK_LENGTH_STEPS/OFFERS_PER_WEEK/pool). Prove it: a pending mediator
        # whose current_offers is NOT the live derivation still serializes, storing exactly
        # those offers (a `== canonical` guard would raise here).
        m = _at_boundary(map_definition=resolve_map("river", 1))
        forced = (describe(OfferKind.CARRIAGE), describe(OfferKind.NEW_LINE))
        self.assertNotEqual(m.current_offers, forced, "pick a non-derived pair")
        m.current_offers = forced
        doc = serialize_game(m)
        self.assertEqual(doc["pendingOffers"], ["carriage", "new_line"])
        self.assertEqual(deserialize_game(doc).current_offers, forced, "round-trips")

    def test_serialize_rejects_a_tunnel_offer_on_an_unbounded_map(self):
        # The one LOAD invariant validate_save can't see (it has no resolved map): a TUNNEL
        # offer on CLASSIC is impossible (the pool excludes it). Reject at serialize so an
        # unloadable save never clobbers a valid autosave.
        m = _at_boundary()  # classic
        m.current_offers = (describe(OfferKind.TUNNEL), describe(OfferKind.NEW_LINE))
        with self.assertRaisesRegex(ValueError, "TUNNEL offer on the unbounded"):
            serialize_game(m)

    def test_serialize_rejects_a_malformed_offer_with_an_actionable_error(self):
        # Fleet error-message rule: a malformed current_offers gives a named ValueError,
        # not a raw AttributeError/TypeError.
        m = _at_boundary(map_definition=resolve_map("river", 1))
        m.current_offers = ("bogus",)  # not an Offer
        with self.assertRaisesRegex(ValueError, "not a valid Offer"):
            serialize_game(m)
        m.current_offers = None  # not a tuple
        with self.assertRaisesRegex(ValueError, "must be a tuple"):
            serialize_game(m)

    def test_serialize_rejects_a_week_pause_without_offers(self):
        m = _at_boundary()
        m.current_offers = ()  # week held but no offers -- inconsistent (schema catches it)
        with self.assertRaises(ValueError):
            serialize_game(m)


class TestGM10iValidateRejects(unittest.TestCase):
    def _pending_doc(self):
        return serialize_game(_at_boundary(map_definition=resolve_map("river", 1)))

    def test_v4_is_the_current_version(self):
        self.assertEqual(SAVE_SCHEMA_VERSION, SAVE_SCHEMA_VERSION_V4)
        self.assertEqual(self._pending_doc()["schemaVersion"], 4)

    def test_week_pause_reason_rejected_for_v3(self):
        doc = self._pending_doc()
        doc = copy.deepcopy(doc)
        doc["schemaVersion"] = 3
        del doc["pendingOffers"]  # v3 must not carry it
        with self.assertRaises(ValueError):
            validate_save(doc)

    def test_week_with_game_over_rejected(self):
        doc = copy.deepcopy(self._pending_doc())
        doc["isGameOver"] = True
        with self.assertRaises(ValueError):
            deserialize_game(doc)

    def test_tunnel_offer_on_an_unbounded_map_rejected(self):
        # A CLASSIC (unbounded) save whose pendingOffers claims TUNNEL is impossible/forged.
        doc = copy.deepcopy(serialize_game(_at_boundary()))  # classic
        doc["pendingOffers"] = ["tunnel", "new_line"]
        doc["pauseReasons"] = sorted(set(doc["pauseReasons"]) | {"week"})
        with self.assertRaises(ValueError):
            deserialize_game(doc)

    def test_v4_missing_pending_offers_key_rejected(self):
        doc = copy.deepcopy(self._pending_doc())
        del doc["pendingOffers"]
        with self.assertRaises(ValueError):
            validate_save(doc)

    def test_pending_offers_without_week_rejected(self):
        doc = copy.deepcopy(self._pending_doc())
        doc["pauseReasons"] = [r for r in doc["pauseReasons"] if r != "week"]
        with self.assertRaises(ValueError):
            validate_save(doc)

    def test_unknown_offer_kind_rejected(self):
        # validate_save's OWN documented "known kind" guarantee (review MAJOR/MINOR: a
        # deserialize-only backstop leaves the public validator's guarantee unproven).
        doc = copy.deepcopy(self._pending_doc())
        doc["pendingOffers"] = ["bogus_kind", "new_line"]
        with self.assertRaises(ValueError):
            validate_save(doc)

    def test_duplicate_offer_kind_rejected(self):
        # The distinct-kinds guarantee has NO load backstop (OfferKind("new_line") twice
        # both succeed), so the schema check is the only guard -- pin it (review MAJOR/MINOR).
        doc = copy.deepcopy(self._pending_doc())
        doc["pendingOffers"] = ["new_line", "new_line"]
        with self.assertRaises(ValueError):
            validate_save(doc)

    def test_v1_and_v2_reject_a_grown_fleet(self):
        # Codex MAJOR: the grown-fleet relaxation is v3/v4 ONLY -- v1/v2 must still REJECT a
        # numMetros above config (no upgrade mechanism existed there). An incorrect v1/v2
        # relaxation would otherwise pass the v3/v4 round-trip tests.
        base = copy.deepcopy(serialize_game(Mediator(seed=0)))  # classic, not pending
        base["numMetros"] = CONFIG_NUM_METROS + 1
        for version, strip in (
            (1, ("mapId", "mapDefinitionVersion", "tunnelBonus", "pendingOffers")),
            (2, ("tunnelBonus", "pendingOffers")),
        ):
            doc = copy.deepcopy(base)
            doc["schemaVersion"] = version
            for key in strip:
                doc.pop(key, None)
            with self.assertRaises(ValueError):
                deserialize_game(doc)


class TestGM10iFixture(unittest.TestCase):
    def test_the_frozen_v4_river_pending_fixture_loads_with_its_offers(self):
        # The byte-frozen capability fixture pins CROSS-PROCESS reconstruction of a HELD
        # boundary: schema v4, "week" pending, and the exact shown offers restored (a v3
        # loader would reject the "week" reason -- so this also guards the version bump).
        from save_game import load_game

        loaded = load_game(f"{_FIXTURES}/save-v4-river-pending.json")
        self.assertTrue(loaded.is_week_boundary_pending)
        self.assertEqual(
            [o.kind.value for o in loaded.current_offers], ["tunnel", "new_line"]
        )

    def test_the_frozen_v4_river_pending_fixture_bytes_are_pinned(self):
        # Codex MAJOR: pin the capability fixture's bytes (LF, no CR, length, SHA) like the
        # classic determinism fixture, so the held-boundary reconstruction can't drift.
        with open(f"{_FIXTURES}/save-v4-river-pending.json", "rb") as handle:
            payload = handle.read()
        self.assertNotIn(b"\r", payload)
        self.assertTrue(payload.endswith(b"\n"))
        self.assertEqual(len(payload), 14745)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "0ecbb58f51bfc4f8ac2b6d717caabf8dab0a018e43a5e08229ffe9684bc3bf7f",
        )


class TestGM10iContinuePath(unittest.TestCase):
    def test_a_loaded_pending_save_promotes_to_the_offer_modal(self):
        # End-to-end (both plan lanes): a Continue that restores a pending boundary must
        # re-enter the OFFER modal re-presenting the SAME offers. Feed a real loaded v4
        # pending mediator to a real AppController and reconcile -- it promotes to OFFER
        # with the restored offers intact (the per-frame promotion the run loop runs).
        from app_controller import AppController, AppScreen

        loaded = deserialize_game(
            serialize_game(_at_boundary(map_definition=resolve_map("river", 1)))
        )
        offers = loaded.current_offers
        self.assertTrue(offers)

        class _Session:
            def __init__(self):
                self.dispatched = []

            def dispatch(self, event):
                self.dispatched.append(event)

        session = _Session()
        controller = AppController(
            lambda map_id="classic": (loaded, SimpleNamespace(), session),
            start_state=AppScreen.PLAYING,
        )
        controller.mediator = loaded
        controller.session = session
        controller.reconcile_week_boundary()
        self.assertEqual(
            controller.state, AppScreen.OFFER, "Continue re-enters the modal"
        )
        self.assertEqual(
            controller.mediator.current_offers, offers, "same offers shown"
        )


class TestGM10iWindowCloseAutosave(unittest.TestCase):
    def test_a_mid_offer_autosave_writes_loadable_pending_bytes(self):
        # Codex MAJOR: the GM-10a QUIT test uses a fake mediator (current_offers=(), which
        # the REAL serializer rejects), so it proves "call the seam", not "loadable v4 bytes
        # were written". Drive the REAL autosave writer on a REAL pending mediator through a
        # redirected AUTOSAVE_PATH, then load the file back and confirm the held boundary +
        # offers survived on disk -- the actual mid-offer window-close persistence.
        import main

        m = _at_boundary(map_definition=resolve_map("river", 1))
        offers = m.current_offers
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "autosave.json"
            with mock.patch.object(main, "AUTOSAVE_PATH", path):
                main.write_autosave(m)
                self.assertTrue(path.exists(), "the pending state was written to disk")
                self.assertTrue(main.peek_autosave())
                loaded = main.load_autosave()
        self.assertTrue(loaded.is_week_boundary_pending, "Continue re-enters the modal")
        self.assertEqual(loaded.current_offers, offers, "the same offers, from disk")


class TestGM10iRLUnaffected(unittest.TestCase):
    def test_headless_env_is_never_pending_and_stores_empty_offers(self):
        env = MiniMetroEnv()
        env.reset(seed=0)
        for _ in range(1200 + 60):
            env.mediator.step_time(17)
        self.assertFalse(env.mediator.is_week_boundary_pending)
        self.assertEqual(env.mediator.current_offers, ())
        self.assertEqual(serialize_game(env.mediator)["pendingOffers"], [])


if __name__ == "__main__":
    unittest.main()
