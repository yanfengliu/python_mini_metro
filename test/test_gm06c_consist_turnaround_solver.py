from __future__ import annotations

import itertools
import math
import os
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import config
from rendering.turnaround import turnaround_positions

_GLOBAL_SOLVER_START = (
    (427.7193154721547, -0.8082692437451344),
    (96.6683136158967, 0.5853125037024789),
    (233.87402120557618, -2.627194885798448),
    (175.5543133481621, -1.3475040849614615),
)
_TERMINAL_TANGENT = -0.825428206330248
_GLOBAL_SOLVER_END = tuple(
    (radius, _TERMINAL_TANGENT) for radius in (70.0, 140.0, 210.0, 280.0)
)
_INFEASIBLE_START = (
    (55.963730510340525, 0.9042264811092258),
    (5.574164464780852, -1.556422128375813),
    (57.432500597530726, 2.782898918475537),
    (2.2849500363407533, 0.9366472735208813),
)
_INFEASIBLE_TANGENT = 0.6053038410518834
_INFEASIBLE_END = tuple(
    (radius, _INFEASIBLE_TANGENT) for radius in (70.0, 140.0, 210.0, 280.0)
)
_INFEASIBLE_ALPHA = 0.0037608136444927664


def _cartesian(polar: tuple[float, float]) -> tuple[float, float]:
    radius, angle = polar
    return (radius * math.cos(angle), radius * math.sin(angle))


def _clearances(previous, current):
    pairs = tuple(itertools.combinations(range(len(previous)), 2))
    return pairs, {
        pair: min(
            float(config.carriage_body_length),
            math.dist(previous[pair[0]], previous[pair[1]]),
            math.dist(current[pair[0]], current[pair[1]]),
        )
        for pair in pairs
    }


class TestGM06cTurnaroundSolver(unittest.TestCase):
    def test_degenerate_body_sets_remain_exact_finite_and_pure(self) -> None:
        arguments = ((0.0, 0.0),) * 3
        self.assertEqual(
            turnaround_positions(*arguments, (), (), 0.5, 1.0, 60.0),
            (),
        )
        zero_pair = ((0.0, 0.0), (0.0, 0.0))
        self.assertEqual(
            turnaround_positions(*arguments, zero_pair, zero_pair, 0.5, 1.0, 60.0),
            zero_pair,
        )
        single = turnaround_positions(
            *arguments, ((3.0, 4.0),), ((6.0, 8.0),), 0.5, 1.0, 60.0
        )
        self.assertTrue(all(math.isfinite(value) for value in single[0]))

    def test_infeasible_angular_bounds_expand_radii_without_a_jump(self) -> None:
        previous = tuple(_cartesian(polar) for polar in _INFEASIBLE_START)
        current = tuple(_cartesian(polar) for polar in _INFEASIBLE_END)
        pairs, clearances = _clearances(previous, current)

        samples = tuple(
            turnaround_positions(
                (0.0, 0.0),
                (0.0, 0.0),
                (0.0, 0.0),
                previous,
                current,
                alpha,
                1.0,
                60.0,
            )
            for alpha in (
                0.0,
                1e-8,
                _INFEASIBLE_ALPHA - 1e-6,
                _INFEASIBLE_ALPHA,
                _INFEASIBLE_ALPHA + 1e-6,
                1.0 - 1e-6,
                1.0,
            )
        )
        for sample in samples:
            self.assertTrue(
                all(math.isfinite(value) for point in sample for value in point)
            )
            for pair in pairs:
                self.assertGreaterEqual(
                    math.dist(sample[pair[0]], sample[pair[1]]),
                    clearances[pair] - 1e-6,
                )
        self.assertEqual(samples[0], previous)
        self.assertEqual(samples[-1], current)
        for body, endpoint in zip(samples[1], previous):
            self.assertLess(math.dist(body, endpoint), 0.01)
        for body, endpoint in zip(samples[-2], current):
            self.assertLess(math.dist(body, endpoint), 0.01)
        for before, after in zip(samples[2:4], samples[3:5]):
            for prior_body, body in zip(before, after):
                self.assertLess(math.dist(prior_body, body), 0.01)

    def test_global_projection_back_propagates_when_greedy_bounds_cross(self) -> None:
        previous = tuple(_cartesian(polar) for polar in _GLOBAL_SOLVER_START)
        current = tuple(_cartesian(polar) for polar in _GLOBAL_SOLVER_END)
        pairs, clearances = _clearances(previous, current)
        self.assertEqual(clearances[(0, 1)], 60.0)

        actual = turnaround_positions(
            (0.0, 0.0),
            (0.0, 0.0),
            (0.0, 0.0),
            previous,
            current,
            0.91,
            1.0,
            60.0,
        )
        self.assertEqual(
            actual,
            turnaround_positions(
                (0.0, 0.0),
                (0.0, 0.0),
                (0.0, 0.0),
                previous,
                current,
                0.91,
                1.0,
                60.0,
            ),
        )
        self.assertTrue(
            all(math.isfinite(value) for point in actual for value in point)
        )
        for pair in pairs:
            self.assertGreaterEqual(
                math.dist(actual[pair[0]], actual[pair[1]]),
                clearances[pair] - 1e-6,
            )

        for alpha, endpoint in (
            (0.0, previous),
            (1e-6, previous),
            (1.0 - 1e-6, current),
            (1.0, current),
        ):
            near_endpoint = turnaround_positions(
                (0.0, 0.0),
                (0.0, 0.0),
                (0.0, 0.0),
                previous,
                current,
                alpha,
                1.0,
                60.0,
            )
            tolerance = 1e-9 if alpha in (0.0, 1.0) else 0.01
            for body, expected in zip(near_endpoint, endpoint):
                self.assertLess(math.dist(body, expected), tolerance)


if __name__ == "__main__":
    unittest.main()
