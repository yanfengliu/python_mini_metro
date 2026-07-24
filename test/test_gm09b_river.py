"""GM-09b red contract: the first river map + terrain/station regions (D-034).

A `RIVER` map with a central river obstacle and two land banks; stations spawn
deterministically on the banks and NEVER in the river. CLASSIC stays byte-identical
(region-less), and the save guard is hardened to structural equality so a FORGED
classic-with-terrain can never silently mis-save. maps.py stays import-safe.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
import unittest

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import pygame

from config import screen_height, screen_width, station_size

MODULE = "maps"


def _module(tc, name=MODULE):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        tc.fail(f"GM-09b product module missing: {name} ({error})")


def _sym(tc, name, module_name=MODULE):
    value = getattr(_module(tc, module_name), name, None)
    tc.assertIsNotNone(value, f"GM-09b product symbol missing: {module_name}.{name}")
    return value


class TestGM09bRiverDefinition(unittest.TestCase):
    def test_river_is_registered_and_resolvable(self):
        river = _sym(self, "RIVER")
        resolve = _sym(self, "resolve_map")
        self.assertEqual(river.map_id, "river")
        self.assertEqual(river.map_definition_version, 1)
        self.assertIs(resolve("river", 1), river)
        # river + classic are registered; the exact set grows as later units add
        # maps (GM-09d's delta, etc.), so assert membership, not an exact tuple.
        known = _sym(self, "KNOWN_MAP_IDS")
        self.assertIn("river", known)
        self.assertIn("classic", known)

    def test_river_has_banks_and_a_river_band(self):
        river = _sym(self, "RIVER")
        self.assertTrue(river.spawn_regions, "river has spawn regions (banks)")
        self.assertTrue(river.rivers, "river has a render band")
        # Two banks; each region is a 4-tuple (left, top, right, bottom) of floats.
        self.assertEqual(len(river.spawn_regions), 2)
        for region in river.spawn_regions:
            self.assertEqual(len(region), 4)
            left, top, right, bottom = region
            self.assertLess(left, right, "positive-width region")
            self.assertLess(top, bottom, "positive-height region")

    def test_classic_is_region_free(self):
        classic = _sym(self, "CLASSIC")
        self.assertEqual(classic.spawn_regions, ())
        self.assertEqual(classic.rivers, ())

    def test_geometry_fields_are_immutable_and_validated(self):
        map_def_cls = _sym(self, "MapDefinition")
        classic = _sym(self, "CLASSIC")
        base = dict(
            map_id="x",
            map_definition_version=1,
            shape_types=classic.shape_types,
            unique_shape_types=classic.unique_shape_types,
            unique_spawn_start_index=classic.unique_spawn_start_index,
            unique_spawn_chance=classic.unique_spawn_chance,
        )
        # Nested lists are tuple-coerced (deep immutability).
        made = map_def_cls(**base, spawn_regions=[[0.0, 0.0, 10.0, 10.0]])
        self.assertIsInstance(made.spawn_regions, tuple)
        self.assertIsInstance(made.spawn_regions[0], tuple)
        # A degenerate (non-positive-area) region is rejected.
        with self.assertRaises(Exception):
            map_def_cls(**base, spawn_regions=[[10.0, 0.0, 0.0, 10.0]])


class TestGM09bRegionSpawn(unittest.TestCase):
    def _river_bands(self, river):
        return river.rivers

    def _in_rect(self, x, y, rect):
        left, top, right, bottom = rect
        return left <= x <= right and top <= y <= bottom

    def test_river_stations_spawn_on_banks_and_never_in_the_river(self):
        from mediator import Mediator

        river = _sym(self, "RIVER")
        mediator = Mediator(seed=0, map_definition=river)
        for station in mediator.all_stations:
            x, y = station.position.left, station.position.top
            # Inside some bank region.
            self.assertTrue(
                any(self._in_rect(x, y, r) for r in river.spawn_regions),
                f"station ({x},{y}) is on a bank",
            )
            # And the whole glyph clears the river band (eroded by station_size).
            for band in river.rivers:
                left, _t, right, _b = band
                self.assertFalse(
                    left - station_size < x < right + station_size,
                    f"station ({x},{y}) glyph overlaps the river band {band}",
                )

    def test_river_construction_is_deterministic(self):
        from mediator import Mediator

        river = _sym(self, "RIVER")

        def project(seed):
            m = Mediator(seed=seed, map_definition=river)
            return [
                (
                    type(s.shape).__name__,
                    round(s.position.left, 4),
                    round(s.position.top, 4),
                )
                for s in m.all_stations
            ]

        self.assertEqual(project(0), project(0), "seed 0 reproduces exactly")
        self.assertNotEqual(project(0), project(1), "different seeds differ")

    def test_classic_construction_is_byte_identical_to_pre_region(self):
        # The GM-09a determinism fingerprints (in test_gm09a_maps) must still hold;
        # here a direct guard that CLASSIC's stations are unchanged for seed 0.
        from mediator import Mediator

        m = Mediator(seed=0)  # default CLASSIC, region-free
        shapes = [type(s.shape).__name__ for s in m.all_stations[:3]]
        positions = [
            (round(s.position.left), round(s.position.top)) for s in m.all_stations[:3]
        ]
        self.assertEqual(shapes, ["Triangle", "Rect", "Rect"])
        self.assertEqual(positions, [(1232, 318), (1132, 474), (1213, 375)])


class TestGM09bSaveGuardStructural(unittest.TestCase):
    def test_forged_classic_with_terrain_is_rejected(self):
        # Review Codex MAJOR: the guard must be STRUCTURAL, not id+version only, or
        # a forged classic-with-terrain serializes and reloads as plain Classic.
        from mediator import Mediator
        from save_game import serialize_game

        map_def_cls = _sym(self, "MapDefinition")
        classic = _sym(self, "CLASSIC")
        serialize_game(Mediator(seed=0))  # canonical Classic serializes fine
        forged = map_def_cls(
            map_id="classic",
            map_definition_version=1,
            shape_types=classic.shape_types,
            unique_shape_types=classic.unique_shape_types,
            unique_spawn_start_index=classic.unique_spawn_start_index,
            unique_spawn_chance=classic.unique_spawn_chance,
            spawn_regions=((0.0, 0.0, 10.0, 10.0),),
            rivers=((5.0, 0.0, 6.0, 10.0),),
        )
        m = Mediator(seed=0)
        m.map_definition = forged
        with self.assertRaises(Exception):
            serialize_game(m)

    def test_river_map_round_trips_through_a_v2_save(self):
        # GM-09f: a registered RIVER map now serializes (v2 records the map identity)
        # and reloads with its map preserved -- the forged-classic guard above stays
        # green because it checks STRUCTURAL equality to the registered definition.
        from mediator import Mediator
        from save_game import serialize_game
        from save_load import deserialize_game
        from save_schema import validate_save

        river = _sym(self, "RIVER")
        document = serialize_game(Mediator(seed=0, map_definition=river))
        self.assertEqual(document["mapId"], "river")
        self.assertEqual(document["mapDefinitionVersion"], 1)
        validate_save(document)
        self.assertEqual(deserialize_game(document).map_definition, river)


class TestGM09bTerrainRenderer(unittest.TestCase):
    def test_classic_paints_nothing_river_paints_something(self):
        draw_terrain = _sym(self, "draw_terrain", "rendering.terrain_renderer")
        classic = _sym(self, "CLASSIC")
        river = _sym(self, "RIVER")
        surface = pygame.Surface((screen_width, screen_height))
        surface.fill((247, 245, 239))
        before = surface.copy()
        draw_terrain(surface, classic)
        self.assertEqual(
            surface.get_view("2").raw,
            before.get_view("2").raw,
            "CLASSIC paints nothing",
        )
        draw_terrain(surface, river)
        self.assertNotEqual(
            surface.get_view("2").raw, before.get_view("2").raw, "RIVER paints the band"
        )


class TestGM09bImportSafety(unittest.TestCase):
    def test_maps_pulls_no_shapely_or_geometry_polygon(self):
        code = (
            "import sys; sys.path.insert(0, 'src'); import maps; "
            "bad=[m for m in ('pygame','mediator','shapely','geometry.polygon',"
            "'entity.station') if m in sys.modules]; "
            "print('LEAK' if bad else 'CLEAN', bad)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.realpath(__file__)) + "/..",
        )
        self.assertIn(
            "CLEAN", result.stdout, f"maps leaked: {result.stdout}{result.stderr}"
        )


if __name__ == "__main__":
    unittest.main()
