import os
import subprocess
import sys
import unittest
from pathlib import Path

from test.path_lifecycle_direct_support import (
    CallbackList,
    EphemeralFactory,
    FakeButton,
    FakeHost,
    FakeMetro,
    FakeNode,
    FakePath,
    FakeStation,
    FakeTravelPlan,
    IntSubclass,
    LoggingDict,
)

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

# isort: split

from path_lifecycle import PathLifecycle


class TestPathLifecycle(unittest.TestCase):
    def setUp(self):
        self.lifecycle = PathLifecycle()

    def test_component_is_stateless_and_imports_no_domain_modules(self):
        self.assertEqual(PathLifecycle.__slots__, ())
        self.assertFalse(hasattr(self.lifecycle, "__dict__"))
        with self.assertRaises(AttributeError):
            self.lifecycle.host = object()

        repo_root = Path(__file__).resolve().parents[1]
        source_root = repo_root / "src"
        blocked = (
            "pygame",
            "mediator",
            "entity",
            "graph",
            "route_planner",
            "progression",
            "simulation_context",
            "travel_plan",
        )
        script = f"""
import sys
import path_lifecycle

blocked = {blocked!r}
loaded = sorted(
    name for name in sys.modules
    if any(name == root or name.startswith(f"{{root}}.") for root in blocked)
)
if loaded:
    raise AssertionError(loaded)
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(source_root), environment.get("PYTHONPATH")])
        )
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=repo_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_assign_paths_to_buttons_replaces_mapping_after_ordered_clears(self):
        host = FakeHost(self.lifecycle)
        paths = [
            FakePath(f"p{index}", (index, 0, 0), host.events) for index in range(2)
        ]
        host.paths = paths
        host.path_buttons = [FakeButton(f"b{index}", host.events) for index in range(3)]
        old_mapping = {paths[0]: host.path_buttons[2]}
        host.path_to_button = old_mapping

        self.lifecycle.assign_paths_to_buttons(host)

        self.assertEqual(
            host.events,
            [
                ("button:clear", "b0"),
                ("button:clear", "b1"),
                ("button:clear", "b2"),
                ("button:assign", "b0", "p0"),
                ("button:assign", "b1", "p1"),
                ("locks",),
            ],
        )
        self.assertIsNot(host.path_to_button, old_mapping)
        self.assertEqual(old_mapping, {paths[0]: host.path_buttons[2]})
        self.assertEqual(host.path_to_button, dict(zip(paths, host.path_buttons)))

    def test_remove_path_preserves_snapshots_and_plan_invalidation_contract(self):
        host = FakeHost(self.lifecycle)
        removed = FakePath("removed", (1, 2, 3), host.events)
        surviving = FakePath("surviving", (4, 5, 6), host.events)
        doomed_metro = FakeMetro("doomed")
        late_metro = FakeMetro("late")
        doomed_passenger = object()
        late_passenger = object()
        onboard_passenger = object()
        waiting_immediate = object()
        waiting_later = object()
        unrelated = object()
        doomed_metro.passengers = [doomed_passenger]
        late_metro.passengers = [late_passenger, onboard_passenger]
        removed.metros = [doomed_metro]
        host.metros = [doomed_metro, late_metro]

        def mutate_snapshotted_sources(value):
            if value is doomed_passenger:
                removed.metros.append(late_metro)
                doomed_metro.passengers.append(late_passenger)

        host.passengers = CallbackList(
            [doomed_passenger, late_passenger, onboard_passenger],
            mutate_snapshotted_sources,
        )
        kept_plan = FakeTravelPlan(surviving, [FakeNode(removed)])
        unrelated_plan = FakeTravelPlan(surviving, [FakeNode(surviving)])
        host.travel_plans = {
            doomed_passenger: FakeTravelPlan(removed),
            late_passenger: unrelated_plan,
            onboard_passenger: kept_plan,
            waiting_immediate: FakeTravelPlan(removed),
            waiting_later: FakeTravelPlan(surviving, [FakeNode(removed)]),
            unrelated: unrelated_plan,
        }
        host.paths = [removed, surviving]
        host.path_buttons = [
            FakeButton("b0", host.events),
            FakeButton("b1", host.events),
        ]
        host.path_to_button = {
            removed: host.path_buttons[0],
            surviving: host.path_buttons[1],
        }
        host.path_colors = {removed.color: True, surviving.color: True}
        host.path_to_color = {removed: removed.color, surviving: surviving.color}

        self.lifecycle.remove_path(host, removed)

        self.assertEqual(removed.metros, [doomed_metro, late_metro])
        self.assertEqual(doomed_metro.passengers, [doomed_passenger, late_passenger])
        self.assertIn(late_metro, host.metros)
        self.assertIn(late_passenger, host.passengers)
        self.assertNotIn(doomed_passenger, host.passengers)
        self.assertNotIn(removed, host.paths)
        self.assertIs(host.travel_plans[onboard_passenger], kept_plan)
        self.assertIs(host.travel_plans[unrelated], unrelated_plan)
        self.assertNotIn(waiting_immediate, host.travel_plans)
        self.assertNotIn(waiting_later, host.travel_plans)
        markers = [event[0] for event in host.events]
        self.assertEqual(markers[0], "button:clear")
        self.assertLess(
            markers.index("public:invalidate"), markers.index("public:release")
        )
        self.assertLess(markers.index("public:release"), markers.index("public:assign"))
        self.assertLess(markers.index("public:assign"), markers.index("replan"))

    def test_remove_selectors_use_first_id_and_exact_int_only(self):
        host = FakeHost(self.lifecycle)
        first = FakePath("same", (1, 0, 0), host.events)
        second = FakePath("same", (2, 0, 0), host.events)
        host.paths = [first, second]
        removed = []
        host.remove_path = removed.append

        self.assertTrue(self.lifecycle.remove_path_by_id(host, "same"))
        self.assertIs(removed[-1], first)
        self.assertFalse(self.lifecycle.remove_path_by_id(host, "missing"))
        self.assertTrue(self.lifecycle.remove_path_by_index(host, 1))
        self.assertIs(removed[-1], second)
        for invalid in (-1, 2, True, IntSubclass(0), 1.0):
            with self.subTest(invalid=invalid):
                self.assertFalse(self.lifecycle.remove_path_by_index(host, invalid))

    def test_start_is_late_single_identity_installation_and_cap_is_noop(self):
        host = FakeHost(self.lifecycle)
        station = FakeStation("a", host.events)
        colors = [(1, 0, 0), (2, 0, 0), (3, 0, 0)]
        host.path_colors = dict(zip(colors, [True, False, False]))
        host.unlocked_num_paths = 2
        snapshots = {}

        def build_path(color):
            path = FakePath("late", color, host.events)
            original_add = path.add_station

            def add_station(value):
                snapshots["add"] = (
                    host.path_to_color.get(path),
                    host.path_being_created,
                    tuple(host.paths),
                    path.is_being_created,
                )
                original_add(value)

            path.add_station = add_station
            return path

        def get_path_factory():
            snapshots["getter"] = (
                host.is_creating_path,
                host.path_colors[colors[1]],
                tuple(host.paths),
            )
            host.events.append(("factory:path:get",))
            return EphemeralFactory("path", host.events, build_path)

        self.lifecycle.start_path_on_station(
            host, station, get_path_factory=get_path_factory
        )

        path = host.paths[0]
        self.assertEqual(snapshots["getter"], (True, True, ()))
        self.assertEqual(snapshots["add"], (colors[1], None, (), False))
        self.assertIs(host.path_being_created, path)
        self.assertIs(host.path_to_color[path], path.color)
        self.assertTrue(path.is_being_created)
        factory_events = [
            event[0] for event in host.events if event[0].startswith("factory:")
        ]
        self.assertEqual(
            factory_events,
            ["factory:path:get", "factory:path:call", "factory:path:del"],
        )

        fallback = FakeHost(self.lifecycle)
        fallback.path_colors = dict(zip(colors, [True, True, False]))
        fallback.unlocked_num_paths = 2
        self.lifecycle.start_path_on_station(
            fallback,
            FakeStation("fallback", fallback.events),
            get_path_factory=lambda: fallback.path_factory,
        )
        self.assertEqual(fallback.paths[0].color, (0, 0, 0))
        self.assertFalse(fallback.path_colors[colors[2]])

        capped = FakeHost(self.lifecycle)
        capped.paths = [FakePath("full", (0, 0, 0), capped.events)]
        capped.unlocked_num_paths = 1
        self.lifecycle.start_path_on_station(
            capped,
            FakeStation("ignored", capped.events),
            get_path_factory=lambda: self.fail("factory must not resolve at cap"),
        )
        self.assertFalse(capped.is_creating_path)
        self.assertIsNone(capped.path_being_created)

    def test_programmatic_creation_validates_and_resolves_public_hooks_lazily(self):
        host = FakeHost(self.lifecycle)
        host.stations = [FakeStation(name, host.events) for name in "abcd"]
        host.path_colors = {(1, 2, 3): False}
        for invalid in (None, (), [0], [0, True], [0, 4], [-1, 0]):
            with self.subTest(invalid=invalid):
                self.assertIsNone(
                    self.lifecycle.create_path_from_station_indices(host, invalid)
                )
        self.assertFalse(any(event[0] == "public:start" for event in host.events))

        calls = []
        created = FakePath("captured", (1, 2, 3), host.events)

        def start(station):
            calls.append(("start", station.name))
            host.paths.append(created)
            host.path_being_created = created
            created.is_being_created = True
            host.add_station_to_path = second_add

        def second_add(station):
            calls.append(("add", station.name))

        def end(station):
            calls.append(("end", station.name))
            created.is_being_created = False
            host.path_being_created = FakePath("replacement", (0, 0, 0), host.events)

        host.start_path_on_station = start
        host.end_path_on_station = end
        result = self.lifecycle.create_path_from_station_indices(host, [0, 1, 2, 3])

        self.assertIs(result, created)
        self.assertEqual(
            calls, [("start", "a"), ("add", "b"), ("add", "c"), ("end", "d")]
        )

        loop_host = FakeHost(self.lifecycle)
        loop_host.stations = [FakeStation(name, loop_host.events) for name in "abc"]
        loop_host.path_colors = {(9, 8, 7): False}
        loop_path = self.lifecycle.create_path_from_station_indices(
            loop_host, [0, 1, 2], loop=True
        )
        self.assertIsNotNone(loop_path)
        self.assertEqual(
            [station.name for station in loop_path.stations], ["a", "b", "c"]
        )
        self.assertTrue(loop_path.is_looped)

        closed_host = FakeHost(self.lifecycle)
        closed_host.stations = [FakeStation(name, closed_host.events) for name in "abc"]
        closed_host.path_colors = {(6, 5, 4): False}
        closed_path = self.lifecycle.create_path_from_station_indices(
            closed_host, [0, 1, 2, 0], loop=True
        )
        self.assertIsNotNone(closed_path)
        self.assertEqual(
            [station.name for station in closed_path.stations], ["a", "b", "c"]
        )
        self.assertTrue(closed_path.is_looped)
        self.assertEqual(
            [event[1] for event in closed_host.events if event[0] == "public:add"],
            ["b", "c"],
        )
        self.assertEqual(
            [event[1] for event in closed_host.events if event[0] == "blip"],
            ["b", "c"],
        )
        self.assertEqual(
            [event[1] for event in closed_host.events if event[0] == "public:end"],
            ["a"],
        )

    def test_add_station_preserves_duplicate_loop_and_snap_rules(self):
        host = FakeHost(self.lifecycle)
        first = FakeStation("a", host.events)
        second = FakeStation("b", host.events)
        third = FakeStation("c", host.events)
        path = FakePath("draft", (1, 2, 3), host.events)
        path.stations = [first, second]
        host.path_being_created = path

        self.lifecycle.add_station_to_path(host, FakeStation("b", host.events))
        self.lifecycle.add_station_to_path(host, FakeStation("a", host.events))
        self.assertTrue(path.is_looped)
        self.lifecycle.add_station_to_path(host, third)
        self.assertFalse(path.is_looped)
        self.lifecycle.add_station_to_path(host, second)

        self.assertEqual(
            [station.name for station in path.stations], ["a", "b", "c", "b"]
        )
        blips = [event for event in host.events if event[0] == "blip"]
        self.assertEqual([event[1] for event in blips], ["a", "c", "b"])

    def test_release_and_abort_preserve_order_and_live_rebinding(self):
        host = FakeHost(self.lifecycle)
        original = FakePath("original", (1, 2, 3), host.events)
        host.path_colors = LoggingDict({original.color: True}, host.events, "colors")
        host.path_to_color = LoggingDict({original: original.color}, host.events, "map")

        self.lifecycle.release_color_for_path(host, original)

        self.assertEqual(
            host.events,
            [("colors:set", original.color, False), ("map:del", original)],
        )

        rebound = FakeHost(self.lifecycle)
        first = FakePath("first", (1, 1, 1), rebound.events)
        replacement = FakePath("replacement", (2, 2, 2), rebound.events)
        old_paths = [first]
        rebound.paths = old_paths
        rebound.path_being_created = first
        rebound.is_creating_path = True

        def release(value):
            self.assertIs(value, first)
            self.assertFalse(rebound.is_creating_path)
            rebound.events.append(("release-rebind",))
            rebound.paths = [replacement]
            rebound.path_being_created = replacement

        rebound.release_color_for_path = release
        self.lifecycle.abort_path_creation(rebound)

        self.assertEqual(old_paths, [first])
        self.assertEqual(rebound.paths, [])
        self.assertIsNone(rebound.path_being_created)
        self.assertEqual(rebound.events, [("release-rebind",)])

    def test_finish_cleans_draft_without_allocating_and_preserves_button_failures(
        self,
    ):
        host = FakeHost(self.lifecycle)
        path = FakePath("draft", (1, 2, 3), host.events)
        path.is_being_created = True
        host.path_being_created = path
        host.is_creating_path = True
        existing = FakeMetro("existing")
        path.metros = [existing]
        host.metros = [existing]
        snapshots = {}

        def assign():
            snapshots["assign"] = (
                host.path_being_created,
                tuple(path.metros),
                tuple(host.metros),
            )
            host.events.append(("public:assign",))

        host.assign_paths_to_buttons = assign
        self.lifecycle.finish_path_creation(host)

        self.assertFalse(host.is_creating_path)
        self.assertFalse(path.is_being_created)
        self.assertIsNone(path.temp_point)
        self.assertIsNone(host.path_being_created)
        self.assertEqual(snapshots["assign"], (None, (existing,), (existing,)))
        self.assertEqual(path.metros, [existing])
        self.assertEqual(host.metros, [existing])
        names = [event[0] for event in host.events]
        self.assertLess(names.index("path:remove-temp"), names.index("public:assign"))

        failing = FakeHost(self.lifecycle)
        failing_path = FakePath("failing", (0, 0, 0), failing.events)
        failing_path.is_being_created = True
        failing.path_being_created = failing_path
        failing.is_creating_path = True

        def explode():
            raise RuntimeError("button assignment failed")

        failing.assign_paths_to_buttons = explode
        with self.assertRaisesRegex(RuntimeError, "button assignment failed"):
            self.lifecycle.finish_path_creation(failing)
        self.assertFalse(failing.is_creating_path)
        self.assertFalse(failing_path.is_being_created)
        self.assertIsNone(failing_path.temp_point)
        self.assertIsNone(failing.path_being_created)
        self.assertEqual(failing_path.metros, [])
        self.assertEqual(failing.metros, [])

    def test_end_path_dispatches_exact_finish_loop_add_and_abort_branches(self):
        cases = (
            ("current", ["a", "b"], "b", ["finish"], False, ["a", "b"]),
            ("loop", ["a", "b"], "a", ["finish"], True, ["a", "b"]),
            ("new", ["a", "b"], "c", ["finish"], False, ["a", "b", "c"]),
            ("abort", ["a"], "a", ["abort"], False, ["a"]),
        )
        for name, station_names, endpoint_name, calls, looped, expected_names in cases:
            with self.subTest(name=name):
                host = FakeHost(self.lifecycle)
                stations = [FakeStation(value, host.events) for value in station_names]
                path = FakePath("draft", (1, 2, 3), host.events)
                path.stations = stations
                host.path_being_created = path
                dispatched = []
                host.finish_path_creation = lambda: dispatched.append("finish")
                host.abort_path_creation = lambda: dispatched.append("abort")

                self.lifecycle.end_path_on_station(
                    host, FakeStation(endpoint_name, host.events)
                )

                self.assertEqual(dispatched, calls)
                self.assertEqual(path.is_looped, looped)
                self.assertEqual(
                    [station.name for station in path.stations], expected_names
                )
                blips = [event for event in host.events if event[0] == "blip"]
                self.assertEqual(len(blips), 1 if name == "new" else 0)


if __name__ == "__main__":
    unittest.main()
