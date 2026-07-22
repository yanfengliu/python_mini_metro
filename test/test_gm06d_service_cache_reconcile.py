"""GM-06d adversarial-review regressions: service-cache reconciliation.

Covers the F-1 recursive-harness crash (a schema-valid v5 document whose
paused occupied queue previously produced a non-canonical state that
crashed checkpoint v4 generation), the F-2 surviving-metro reconcile on
conserving line removal, the OBS-1 unplaceable-rider refusal, and the
OBS-4 single canonical live-only action set.
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import agent_play
import recursive_contract
import recursive_playtest
from env import MiniMetroEnv
from mediator import Mediator
from path_lifecycle import PathLifecycle
from recursive_checkpoint import canonical_checkpoint
from test.gm06c_simulation_ui_support import passenger_for
from test.path_lifecycle_direct_support import (
    FakeButton,
    FakeHost,
    FakeMetro,
    FakePath,
)

FLEET_CONTRACT = "explicit_locomotive_assignment_v1"
CARRIAGE_CONTRACT = "explicit_carriage_attachment_v1"


def paused_occupied_queue_document() -> dict[str, object]:
    """Reviewer document: persistable ops only, ending in a paused queue."""

    return {
        "schemaVersion": 5,
        "environmentRewardContract": "deliveries",
        "overduePassengerThreshold": 2,
        "fleetActionContract": FLEET_CONTRACT,
        "carriageActionContract": CARRIAGE_CONTRACT,
        "seed": 0,
        "defaultDtMs": 250,
        "operations": [
            {
                "name": "create-line",
                "action": {
                    "type": "create_path",
                    "stations": [0, 1, 2],
                    "loop": False,
                },
                "expectedActionOk": True,
            },
            {
                "name": "assign-locomotive",
                "action": {"type": "assign_locomotive", "path_index": 0},
                "expectedActionOk": True,
            },
            *(
                {
                    "name": f"advance-{index}",
                    "action": {"type": "noop"},
                    "expectedActionOk": True,
                }
                for index in range(14)
            ),
            {
                "name": "pause-mid-board",
                "action": {"type": "pause"},
                "expectedActionOk": True,
            },
            {
                "name": "queue-occupied-return",
                "action": {"type": "unassign_locomotive", "path_index": 0},
                "expectedActionOk": True,
            },
        ],
    }


class TestRecursiveHarnessPausedOccupiedQueue(unittest.TestCase):
    """F-1: run_scenario survives a legitimately-reached paused queue state."""

    def test_v5_document_with_paused_occupied_queue_completes(self) -> None:
        document = paused_occupied_queue_document()
        self.assertEqual(recursive_playtest.validate_scenario(document), document)

        with patch.dict(os.environ, {"PYTHONHASHSEED": "0"}):
            inputs, rows, findings, result = recursive_playtest.run_scenario(
                document,
                run_id="gm06d-f1-regression",
                source_path="gm06d-f1-regression.json",
            )

        self.assertEqual(inputs["schemaVersion"], 5)
        self.assertEqual(len(rows), len(document["operations"]))
        self.assertTrue(all(row["actionOk"] for row in rows))
        self.assertTrue(all(row["checkpoint"]["schemaVersion"] == 4 for row in rows))
        self.assertTrue(result["completed"])
        # The whole scenario is finding-free, including the pre-pause noop
        # steps that checkpoint the metro mid-PaddingSegment; pinned exactly
        # so a queue or padding-traversal regression cannot hide.
        self.assertEqual(findings, [])


class TestRemovalReconcilesSurvivingService(unittest.TestCase):
    """F-2: conserving removal reconciles surviving stopped Metros' caches."""

    def _two_line_shared_station_game(self):
        mediator = Mediator(seed=0)
        stations = mediator.stations
        self.assertNotEqual(stations[0].shape.type, stations[1].shape.type)
        mediator.unlocked_num_paths = mediator.num_paths
        mediator.update_path_button_lock_states()
        line_b = mediator.create_path_from_station_indices([0, 1])
        line_a = mediator.create_path_from_station_indices([1, 2])
        self.assertIsNotNone(line_b)
        self.assertIsNotNone(line_a)
        self.assertTrue(mediator.assign_locomotive(line_b))
        self.assertTrue(mediator.assign_locomotive(line_a))
        shared = stations[1]
        for owner in (line_b, line_a):
            metro = owner.metros[0]
            index = next(
                position
                for position, segment in enumerate(owner.segments)
                if getattr(segment, "start_station", None) is shared
                or getattr(segment, "end_station", None) is shared
            )
            metro.current_segment_idx = index
            metro.current_segment = owner.segments[index]
            metro.current_station = shared
            metro.position = shared.position
            metro.speed = 0
        rider = passenger_for(stations[0], name="dumped-rider")
        line_a.metros[0].passengers.append(rider)
        mediator.passengers.append(rider)
        return mediator, line_a, line_b, shared, rider

    def test_paused_removal_rebinds_surviving_parked_metro(self) -> None:
        mediator, line_a, line_b, shared, rider = self._two_line_shared_station_game()
        survivor = line_b.metros[0]
        env = MiniMetroEnv(reward_mode="deliveries")
        env.mediator = mediator
        mediator.set_paused(True)
        self.assertEqual(
            canonical_checkpoint(env, schema_version=4)["schemaVersion"], 4
        )

        mediator.remove_path(line_a)

        self.assertNotIn(line_a, mediator.paths)
        self.assertIn(rider, shared.passengers)
        self.assertIn(rider, mediator.passengers)
        plan = mediator.travel_plans.get(rider)
        self.assertIsNotNone(plan)
        self.assertIs(plan.next_path, line_b)
        # The conserving dump changed the survivor's boarding eligibility;
        # the removal transaction reconciles its cache synchronously so the
        # paused state stays canonical for checkpoint v4.
        action = survivor._station_service_action
        self.assertIsNotNone(action)
        assert action is not None
        self.assertEqual(action[0], "board")
        self.assertIs(action[1], rider)
        self.assertEqual(
            canonical_checkpoint(env, schema_version=4)["schemaVersion"], 4
        )


class TestRemovalRefusesUnplaceableRider(unittest.TestCase):
    """OBS-1: an unresolvable alight station refuses instead of dropping."""

    def test_unresolvable_alight_station_refuses_with_exact_restoration(self) -> None:
        lifecycle = PathLifecycle()
        host = FakeHost(lifecycle)
        doomed = FakePath("doomed", (1, 2, 3), host.events)
        metro = FakeMetro("unplaceable")
        rider = object()
        plan = object()
        metro.passengers = [rider]
        doomed.metros = [metro]
        host.paths = [doomed]
        host.metros = [metro]
        host.passengers = [rider]
        button = FakeButton("b0", host.events)
        button.path = doomed
        host.path_buttons = [button]
        host.path_to_button = {doomed: button}
        host.path_colors = {(1, 2, 3): True}
        host.path_to_color = {doomed: (1, 2, 3)}
        host.travel_plans = {rider: plan}

        lifecycle.remove_path(host, doomed)

        # The hypothetical silent rider drop is a safe refusal: the removal
        # transaction restores the exact prior state and keeps the line.
        self.assertEqual(host.paths, [doomed])
        self.assertEqual(host.metros, [metro])
        self.assertEqual(metro.passengers, [rider])
        self.assertEqual(doomed.metros, [metro])
        self.assertEqual(host.passengers, [rider])
        self.assertEqual(host.travel_plans, {rider: plan})
        self.assertIs(host.path_to_button[doomed], button)
        self.assertEqual(host.path_colors, {(1, 2, 3): True})
        self.assertEqual(host.path_to_color, {doomed: (1, 2, 3)})


class TestLiveOnlyActionTypesSingleSource(unittest.TestCase):
    """OBS-4: one canonical live-only action set shared across modules."""

    def test_agent_play_reuses_the_recursive_contract_set(self) -> None:
        self.assertIs(
            agent_play._LIVE_ONLY_ACTION_TYPES,
            recursive_contract._LIVE_ONLY_ACTION_TYPES,
        )
        self.assertEqual(
            recursive_contract._LIVE_ONLY_ACTION_TYPES, {"cancel_unassignment"}
        )


if __name__ == "__main__":
    unittest.main()
