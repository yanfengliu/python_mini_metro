from __future__ import annotations

import os
import sys
import unittest
from typing import Any

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from geometry.point import Point
from rendering.interpolation import MetroInterpolator
from rendering.layout import MetroPose, VisualPath, VisualSegment
from test.gm06c_simulation_ui_support import carriage_spacing, product_symbol


def segment(
    index: int,
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    kind: str = "path",
) -> VisualSegment:
    return VisualSegment(
        logical_index=index,
        kind=kind,
        start=start,
        end=end,
        start_station_id=f"s{index}" if kind == "path" else None,
        end_station_id=f"s{index + 1}" if kind == "path" else None,
    )


def visual_path(*segments: VisualSegment, looped: bool = False) -> VisualPath:
    return VisualPath(
        path_id="geometry-path",
        color=(10, 20, 30),
        order=0.0,
        is_looped=looped,
        segments=tuple(segments),
    )


def pose(
    position: tuple[float, float],
    heading: float,
    segment_index: int,
    progress: float,
    *,
    forward: bool = True,
    stopped: bool = False,
) -> MetroPose:
    return MetroPose(
        position=position,
        heading_degrees=heading,
        logical_segment_index=segment_index,
        progress=progress,
        is_forward=forward,
        is_stopped=stopped,
    )


def assert_position(
    testcase: unittest.TestCase,
    actual: tuple[float, float],
    expected: tuple[float, float],
) -> None:
    testcase.assertAlmostEqual(actual[0], expected[0], places=6)
    testcase.assertAlmostEqual(actual[1], expected[1], places=6)


def layout(
    testcase: unittest.TestCase,
    path: VisualPath,
    head: MetroPose,
    count: int,
    spacing: float,
) -> tuple[MetroPose, ...]:
    function = product_symbol(
        testcase,
        "rendering.consist_layout",
        "consist_layout",
    )
    result = function(path, head, count, spacing)
    testcase.assertIsInstance(result, tuple)
    testcase.assertEqual(len(result), count)
    testcase.assertTrue(all(isinstance(item, MetroPose) for item in result))
    return result


def spacing(testcase: unittest.TestCase) -> float:
    return carriage_spacing(testcase)


def _sampler(interpolator: MetroInterpolator) -> Any | None:
    for name in ("poses_for_consist", "consist_poses_for", "sample_consist"):
        method = getattr(interpolator, name, None)
        if callable(method):
            return method
    return None


def sample_carriages(
    testcase: unittest.TestCase,
    interpolator: MetroInterpolator,
    path: Any,
    metro: Any,
    visual_path: VisualPath,
    alpha: float,
) -> tuple[MetroPose, ...]:
    method = _sampler(interpolator)
    testcase.assertIsNotNone(
        method,
        "MetroInterpolator needs a behavior seam for coherent consist sampling",
    )
    result = method(path, metro, visual_path, alpha)
    expected_count = len(metro.carriages)
    if hasattr(result, "carriage_poses"):
        values = tuple(result.carriage_poses)
    else:
        values = tuple(result)
        if len(values) == expected_count + 1:
            values = values[1:]
    testcase.assertEqual(len(values), expected_count)
    testcase.assertTrue(all(isinstance(item, MetroPose) for item in values))
    return values


def place_on_segment(metro: Any, path: Any, index: int, progress: float) -> None:
    segment_value = path.segments[index]
    metro.current_segment_idx = index
    metro.current_segment = segment_value
    metro.current_station = None
    metro.position = Point(
        segment_value.segment_start.left
        + progress
        * (segment_value.segment_end.left - segment_value.segment_start.left),
        segment_value.segment_start.top
        + progress * (segment_value.segment_end.top - segment_value.segment_start.top),
    )
