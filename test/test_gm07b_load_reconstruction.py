"""GM-07b loader reds: reconstruction mechanics, IDs, and fail-closed loads."""

from __future__ import annotations

import importlib
import json
import os
import random
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np

from config import passenger_color, passenger_size
from entity.passenger import Passenger
from env import MiniMetroEnv
from utils import get_shape_from_type

SAVE_GAME_MODULE = "save_game"
SAVE_SCHEMA_MODULE = "save_schema"


def _module(testcase, name):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:
        testcase.fail(f"GM-07b product module is missing: {name} ({error})")


def _symbol(testcase, module_name, name):
    value = getattr(_module(testcase, module_name), name, None)
    testcase.assertIsNotNone(
        value, f"GM-07b product symbol is missing: {module_name}.{name}"
    )
    return value


def _apply(env, action):
    _, _, _, info = env.step(action, dt_ms=0)
    if not info["action_ok"]:
        raise AssertionError(f"scenario action was rejected: {action!r}")


def _line_env(seed, dt_ms=250):
    env = MiniMetroEnv(dt_ms=dt_ms)
    env.reset(seed=seed)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    return env


def _rich_env(seed=7101):
    env = _line_env(seed)
    _apply(env, {"type": "attach_carriage", "path_index": 0})
    for _ in range(120):
        env.step({"type": "noop"})
        mediator = env.mediator
        if (
            mediator.metros[0].passengers
            and any(station.passengers for station in mediator.stations)
            and mediator.travel_plans
        ):
            return env
    raise AssertionError("rich scenario did not converge")


def _passenger_bound_for(mediator, station):
    for candidate in mediator.stations:
        if candidate.shape.type != station.shape.type:
            shape = get_shape_from_type(
                candidate.shape.type, passenger_color, passenger_size
            )
            return Passenger(shape)
    raise AssertionError("scenario needs two station shape types")


def _over_capacity_env(seed=6203):
    env = _line_env(seed)
    mediator = env.mediator
    target = mediator.stations[0]
    while len(target.passengers) <= target.capacity + 1:
        extra = _passenger_bound_for(mediator, target)
        target.passengers.append(extra)
        mediator.passengers.append(extra)
    return env, target


def _loaded_from_env(testcase, env):
    save_game = _symbol(testcase, SAVE_GAME_MODULE, "save_game")
    load_game = _symbol(testcase, SAVE_GAME_MODULE, "load_game")
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "game.save.json"
        save_game(env.mediator, target)
        return load_game(target)


def _wrapped(env, loaded):
    wrapped = MiniMetroEnv(dt_ms=env.dt_ms_default, reward_mode=env.reward_mode)
    wrapped.mediator = loaded
    wrapped.last_deliveries = env.last_deliveries
    wrapped.last_line_credits = env.last_line_credits
    wrapped.last_score = env.last_score
    return wrapped


def _contains(items, target):
    return any(item is target for item in items)


def _write_canonical(directory, document, name):
    payload = (
        json.dumps(
            document,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
        + b"\n"
    )
    target = Path(directory) / name
    target.write_bytes(payload)
    return target


class TestGM07bIdPreservation(unittest.TestCase):
    def test_every_entity_id_class_survives_the_roundtrip(self):
        env = _rich_env()
        control = env.observe()["structured"]
        loaded = _loaded_from_env(self, env)
        observed = _wrapped(env, loaded).observe()["structured"]
        for section in ("stations", "paths", "metros", "carriages", "passengers"):
            self.assertEqual(
                [record["id"] for record in control[section]],
                [record["id"] for record in observed[section]],
                section,
            )
        self.assertEqual(
            [station.id for station in env.mediator.all_stations],
            [station.id for station in loaded.all_stations],
        )
        self.assertEqual(control, observed)

    def test_pre_save_path_id_drives_post_load_structured_actions(self):
        env = _rich_env()
        pre_save_path_id = env.mediator.paths[0].id
        loaded = _loaded_from_env(self, env)
        self.assertTrue(
            loaded.apply_action(
                {"type": "attach_carriage", "path_id": pre_save_path_id}
            )
        )
        self.assertTrue(
            loaded.apply_action(
                {"type": "assign_locomotive", "path_id": pre_save_path_id}
            )
        )
        self.assertTrue(
            loaded.apply_action({"type": "remove_path", "path_id": pre_save_path_id})
        )
        self.assertIsNone(loaded.get_path_by_id(pre_save_path_id))


class TestGM07bObjectReconstruction(unittest.TestCase):
    def test_carriage_private_capacity_is_restored(self):
        env = _rich_env()
        env.mediator.metros[0].carriages[0]._capacity = 9
        loaded = _loaded_from_env(self, env)
        carriage = loaded.metros[0].carriages[0]
        self.assertEqual(carriage._capacity, 9)
        self.assertEqual(carriage.capacity, 9)
        self.assertEqual(loaded.metros[0].capacity, loaded.metros[0]._base_capacity + 9)

    def test_metro_binding_color_and_segment_identity(self):
        env = _rich_env()
        control_metro = env.mediator.metros[0]
        loaded = _loaded_from_env(self, env)
        metro = loaded.metros[0]
        path = loaded.paths[0]
        self.assertTrue(_contains(path.metros, metro))
        self.assertTrue(_contains(loaded.metros, metro))
        self.assertEqual(metro.path_id, path.id)
        self.assertIs(metro.current_segment, path.segments[metro.current_segment_idx])
        self.assertEqual(metro.current_segment_idx, control_metro.current_segment_idx)
        self.assertEqual(tuple(metro.shape.color), tuple(path.color))
        self.assertEqual(
            tuple(float(part) for part in metro.shape.color),
            tuple(float(part) for part in control_metro.shape.color),
        )

    def test_travel_plans_are_keyed_by_restored_objects(self):
        env = _rich_env()
        loaded = _loaded_from_env(self, env)
        self.assertEqual(len(loaded.travel_plans), len(env.mediator.travel_plans))
        self.assertTrue(loaded.travel_plans)
        pool = loaded.all_stations
        for passenger, plan in loaded.travel_plans.items():
            self.assertTrue(_contains(loaded.passengers, passenger))
            if plan.next_path is not None:
                self.assertTrue(_contains(loaded.paths, plan.next_path))
            if plan.next_station is not None:
                self.assertTrue(_contains(pool, plan.next_station))
            for node in plan.node_path:
                self.assertTrue(_contains(pool, node.station))
                for path in node.paths:
                    self.assertTrue(_contains(loaded.paths, path))

    def test_python_rng_restores_via_deep_tuple_reconstruction(self):
        env = _rich_env()
        mediator = env.mediator
        expected_python = mediator.context.python_random.getstate()
        expected_numpy = deepcopy(mediator.context.numpy_random.bit_generator.state)
        loaded = _loaded_from_env(self, env)
        self.assertEqual(loaded.context.python_random.getstate(), expected_python)
        self.assertEqual(
            loaded.context.numpy_random.bit_generator.state, expected_numpy
        )
        self.assertEqual(
            loaded.context.python_random.random(),
            mediator.context.python_random.random(),
        )
        self.assertEqual(
            loaded.context.numpy_random.random(),
            mediator.context.numpy_random.random(),
        )

    def test_over_capacity_station_queue_restores_by_direct_append(self):
        env, target = _over_capacity_env()
        control_count = len(target.passengers)
        self.assertGreater(control_count, target.capacity)
        loaded = _loaded_from_env(self, env)
        station = next(
            station for station in loaded.stations if station.id == target.id
        )
        self.assertEqual(len(station.passengers), control_count)
        self.assertGreater(len(station.passengers), station.capacity)
        for rider in station.passengers:
            self.assertTrue(_contains(loaded.passengers, rider))

    def test_button_state_is_rebuilt_and_blink_restored(self):
        env = _rich_env()
        mediator = env.mediator
        mediator.purchased_num_paths = 2
        mediator.update_unlocked_num_paths()
        control_blinks = [
            button.unlock_blink_start_time_ms for button in mediator.path_buttons
        ]
        control_locks = [button.is_locked for button in mediator.path_buttons]
        self.assertIsNotNone(control_blinks[1])
        loaded = _loaded_from_env(self, env)
        self.assertEqual(len(loaded.path_to_button), len(loaded.paths))
        self.assertIs(loaded.path_to_button[loaded.paths[0]], loaded.path_buttons[0])
        self.assertEqual(
            [button.unlock_blink_start_time_ms for button in loaded.path_buttons],
            control_blinks,
        )
        self.assertEqual(
            [button.is_locked for button in loaded.path_buttons], control_locks
        )


class TestGM07bFailClosedLoads(unittest.TestCase):
    def _document(self, env):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        return serialize_game(env.mediator)

    def test_doctored_documents_with_contradictions_are_rejected(self):
        deserialize_game = _symbol(self, SAVE_GAME_MODULE, "deserialize_game")
        document = self._document(_rich_env())
        mutations = {
            "contradictory slot lock": lambda value: value["pathButtons"][
                0
            ].__setitem__("isLocked", True),
            "active flag off inside prefix": lambda value: value["stations"][
                0
            ].__setitem__("active", False),
            "active flag on beyond prefix": lambda value: value["stations"][
                5
            ].__setitem__("active", True),
            "path color disagreement": lambda value: value["pathToColor"][
                0
            ].__setitem__(1, value["pathColors"][1][0]),
            "slot array shorter than num_paths": lambda value: value[
                "pathButtons"
            ].pop(),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(document)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                deserialize_game(candidate)

    def test_metro_overfill_document_is_rejected(self):
        deserialize_game = _symbol(self, SAVE_GAME_MODULE, "deserialize_game")
        env, target = _over_capacity_env(seed=6233)
        document = self._document(env)
        station_record = next(
            record for record in document["stations"] if record["id"] == target.id
        )
        metro_record = document["metros"][0]
        capacity = metro_record["baseCapacity"] + sum(
            carriage["capacity"] for carriage in metro_record["carriages"]
        )
        overflow = capacity + 1 - len(metro_record["onboardPassengerIds"])
        moved = station_record["waitingPassengerIds"][:overflow]
        station_record["waitingPassengerIds"] = station_record["waitingPassengerIds"][
            overflow:
        ]
        metro_record["onboardPassengerIds"].extend(moved)
        self.assertGreater(len(metro_record["onboardPassengerIds"]), capacity)
        with self.assertRaises(ValueError):
            deserialize_game(document)

    def test_load_game_raises_after_construction_begins_and_stays_usable(self):
        # The doctored document is SCHEMA-VALID (the segment index bound
        # depends on rebuilt segments), so the failure provably occurs
        # after Mediator construction and RNG overwrite have begun; no
        # partial state or host-global RNG effect may escape.
        load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        env = _rich_env()
        document = self._document(env)
        doctored = deepcopy(document)
        doctored["metros"][0]["currentSegmentIdx"] = 999
        self.assertIsNone(validate_save(doctored))
        random.seed(24601)
        np.random.seed(1729)
        python_before = random.getstate()
        numpy_before = np.random.get_state()
        with tempfile.TemporaryDirectory() as directory:
            bad = _write_canonical(directory, doctored, "doctored.save.json")
            with self.assertRaises(ValueError):
                load_game(bad)
            self.assertEqual(random.getstate(), python_before)
            numpy_after = np.random.get_state()
            self.assertEqual(numpy_after[0], numpy_before[0])
            np.testing.assert_array_equal(numpy_after[1], numpy_before[1])
            self.assertEqual(numpy_after[2:], numpy_before[2:])
            good = _write_canonical(directory, document, "good.save.json")
            loaded = load_game(good)
        self.assertEqual(
            [path.id for path in loaded.paths],
            [path.id for path in env.mediator.paths],
        )


class TestGM07bSaveBoundary(unittest.TestCase):
    def test_mid_gesture_saves_are_rejected_but_mouse_down_is_not(self):
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        save_game = _symbol(self, SAVE_GAME_MODULE, "save_game")
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        env = _line_env(6240)
        mediator = env.mediator
        blockers = {
            "is_creating_path": (True, False),
            "path_being_created": (mediator.paths[0], None),
            "path_redraw": (object(), None),
            "path_edit_selection": (object(), None),
        }
        for name, (active, baseline) in blockers.items():
            with self.subTest(blocker=name):
                setattr(mediator, name, active)
                try:
                    with self.assertRaises(ValueError):
                        serialize_game(mediator)
                    with tempfile.TemporaryDirectory() as directory:
                        target = Path(directory) / "blocked.save.json"
                        with self.assertRaises(ValueError):
                            save_game(mediator, target)
                        self.assertEqual(os.listdir(directory), [])
                finally:
                    setattr(mediator, name, baseline)
        mediator.is_mouse_down = True
        document = serialize_game(mediator)
        self.assertIsInstance(document, dict)
        self.assertIsNone(validate_save(document))

    def test_failed_save_leaves_destination_and_directory_untouched(self):
        save_game = _symbol(self, SAVE_GAME_MODULE, "save_game")
        env = _line_env(6241)
        env.mediator.is_creating_path = True
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "existing.save.json"
            destination.write_bytes(b"precious-bytes\n")
            with self.assertRaises(ValueError):
                save_game(env.mediator, destination)
            self.assertEqual(destination.read_bytes(), b"precious-bytes\n")
            self.assertEqual(os.listdir(directory), ["existing.save.json"])


class _FailingWriter:
    """Wrap the real temp-file handle, failing at one chosen method."""

    def __init__(self, handle, fail_on):
        self._handle = handle
        self._fail_on = fail_on

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self._handle.close()
        return False

    def write(self, payload):
        if self._fail_on == "write":
            raise OSError("injected write failure")
        return self._handle.write(payload)

    def flush(self):
        if self._fail_on == "flush":
            raise OSError("injected flush failure")
        return self._handle.flush()

    def fileno(self):
        return self._handle.fileno()


class _InjectedFdopenFailure(Exception):
    """Stand in for a raising os.fdopen (OOM/EMFILE) that never returns a handle."""


class TestGM07bAtomicWriteSeams(unittest.TestCase):
    """Inject failures AFTER mkstemp at every atomic-writer seam.

    Each case proves the real temporary file was created, the injected
    failure propagated, the temporary file was removed, and the
    destination (existing or absent) was left exactly as it was.
    """

    def _run_injected(self, fail_on, existing):
        save_game_module = _module(self, SAVE_GAME_MODULE)
        env = _line_env(6250)
        real_mkstemp = tempfile.mkstemp
        real_fdopen = os.fdopen
        created = []

        def recording_mkstemp(*args, **kwargs):
            descriptor, name = real_mkstemp(*args, **kwargs)
            created.append(name)
            return descriptor, name

        def failing_fdopen(descriptor, *args, **kwargs):
            return _FailingWriter(real_fdopen(descriptor, *args, **kwargs), fail_on)

        patches = [mock.patch("tempfile.mkstemp", recording_mkstemp)]
        if fail_on in ("write", "flush"):
            patches.append(mock.patch("os.fdopen", failing_fdopen))
        elif fail_on == "fsync":
            patches.append(
                mock.patch("os.fsync", side_effect=OSError("injected fsync failure"))
            )
        elif fail_on == "replace":
            patches.append(
                mock.patch(
                    "os.replace", side_effect=OSError("injected replace failure")
                )
            )
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "atomic.save.json"
            if existing:
                destination.write_bytes(b"precious-bytes\n")
            try:
                for patch in patches:
                    patch.start()
                with self.assertRaises(OSError):
                    save_game_module.save_game(env.mediator, destination)
            finally:
                for patch in reversed(patches):
                    patch.stop()
            self.assertEqual(len(created), 1, "mkstemp must have run before the fault")
            self.assertFalse(
                Path(created[0]).exists(), "temporary file must be cleaned up"
            )
            if existing:
                self.assertEqual(destination.read_bytes(), b"precious-bytes\n")
                self.assertEqual(os.listdir(directory), ["atomic.save.json"])
            else:
                self.assertEqual(os.listdir(directory), [])

    def test_injected_failures_after_mkstemp_leave_no_litter(self):
        for fail_on in ("write", "flush", "fsync", "replace"):
            for existing in (True, False):
                with self.subTest(fail_on=fail_on, existing=existing):
                    self._run_injected(fail_on, existing)

    def test_fdopen_failure_closes_the_descriptor_without_masking_or_litter(self):
        # The one atomic-writer seam the wrapping seams above cannot reach: when
        # os.fdopen itself raises (OOM/EMFILE) it never returns a handle, so the
        # with block never runs to close the raw descriptor. The writer must
        # close that fd in its finally -- otherwise it leaks and, on Windows, the
        # still-open temporary cannot be unlinked, masking the real error and
        # leaving .tmp litter behind (codex GM-07d MINOR).
        save_game_module = _module(self, SAVE_GAME_MODULE)
        env = _line_env(6251)
        real_mkstemp = tempfile.mkstemp
        created = []

        def recording_mkstemp(*args, **kwargs):
            descriptor, name = real_mkstemp(*args, **kwargs)
            created.append((descriptor, name))
            return descriptor, name

        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "atomic.save.json"
            destination.write_bytes(b"precious-bytes\n")
            with (
                mock.patch("tempfile.mkstemp", recording_mkstemp),
                mock.patch(
                    "os.fdopen",
                    side_effect=_InjectedFdopenFailure("injected fdopen failure"),
                ),
            ):
                # The injected error must propagate unmasked -- no PermissionError
                # from a doomed unlink of a still-open temporary may replace it.
                with self.assertRaises(_InjectedFdopenFailure):
                    save_game_module.save_game(env.mediator, destination)
            self.assertEqual(len(created), 1, "mkstemp must have run before the fault")
            descriptor, temporary_name = created[0]
            # The writer's finally must have closed the raw fd; a leaked (still
            # open) fd would let this second close succeed instead of raising.
            with self.assertRaises(OSError):
                os.close(descriptor)
            self.assertFalse(Path(temporary_name).exists(), "no .tmp litter may remain")
            self.assertEqual(destination.read_bytes(), b"precious-bytes\n")
            self.assertEqual(os.listdir(directory), ["atomic.save.json"])


if __name__ == "__main__":
    unittest.main()
