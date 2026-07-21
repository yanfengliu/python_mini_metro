from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from fleet_validation import carriage_state_is_canonical
from passenger_capacity import BOARD
from recursive_checkpoint import canonical_checkpoint
from test.gm06c_render_state_support import render_state_signature
from test.gm06c_simulation_ui_support import (
    boardable_passenger,
    make_two_station_game,
    onboard_passenger,
)
from test.test_gm06c_carriage_lifecycle import _as_env
from test.test_gm06c_carriage_transactions import (
    _assert_snapshot,
    _carriage_type,
    _management,
    _snapshot,
)


class TestGM06cStrictReconciliationPostconditions(unittest.TestCase):
    def _assert_noop_reconcile_rolls_back(self, operation: str) -> None:
        mediator, start, end, path, metro = make_two_station_game(
            seed=61970 + len(operation)
        )
        candidate = _carriage_type()()
        if operation == "attach":
            for index in range(metro.capacity):
                onboard_passenger(
                    mediator,
                    metro,
                    end,
                    name=f"full-train-{index}",
                    next_station=end,
                )
            boardable_passenger(
                mediator, start, end, path, name="newly-enabled-boarder"
            )
        else:
            metro.carriages.append(candidate)
            for index in range(metro._base_capacity):
                onboard_passenger(
                    mediator,
                    metro,
                    end,
                    name=f"full-base-train-{index}",
                    next_station=end,
                )
            boardable_passenger(
                mediator, start, end, path, name="newly-disabled-boarder"
            )
            mediator._reconcile_station_service(metro)
        if operation == "attach":
            self.assertIsNone(metro._station_service_action)
            self.assertEqual(
                (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (0, 0)
            )
        else:
            self.assertEqual(metro._station_service_action[0], BOARD)
        before = _snapshot(mediator)
        fingerprint = render_state_signature(mediator)
        env = _as_env(mediator)
        checkpoint = canonical_checkpoint(env)
        reconcile = MagicMock()

        if operation == "attach":
            result = _management().attach(
                mediator,
                path,
                get_carriage_factory=lambda: lambda: candidate,
                reconcile_station_service=reconcile,
            )
        else:
            result = _management().detach(
                mediator, path, reconcile_station_service=reconcile
            )

        self.assertFalse(result)
        reconcile.assert_called_once_with(metro)
        _assert_snapshot(self, mediator, before)
        self.assertEqual(render_state_signature(mediator), fingerprint)
        self.assertEqual(canonical_checkpoint(env), checkpoint)

    def test_attach_noop_reconciliation_rolls_back_exactly(self) -> None:
        self._assert_noop_reconcile_rolls_back("attach")

    def test_detach_noop_reconciliation_rolls_back_exactly(self) -> None:
        self._assert_noop_reconcile_rolls_back("detach")

    def test_preflight_accepts_unbound_zero_timer_fixture(self) -> None:
        mediator, start, _, path, metro = make_two_station_game(seed=61981)
        metro.carriages.append(_carriage_type()())
        onboard_passenger(mediator, metro, start, name="unbound-destination")

        self.assertIsNone(metro._station_service_action)
        self.assertEqual(
            (metro.stop_time_remaining_ms, metro.boarding_progress_ms), (0, 0)
        )
        self.assertTrue(carriage_state_is_canonical(mediator))
        self.assertFalse(
            carriage_state_is_canonical(mediator, require_bound_service=True)
        )
        self.assertTrue(_management().can_detach(mediator, path))


if __name__ == "__main__":
    unittest.main()
