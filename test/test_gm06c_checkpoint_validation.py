import os
import sys
import unittest
from copy import deepcopy
from types import SimpleNamespace

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.metro import Metro
from entity.passenger import Passenger
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint, normalize_checkpoint
from test.gm06c_simulation_ui_support import boardable_passenger


def apply(env, action):
    _, _, _, info = env.step(action, dt_ms=0)
    if not info["action_ok"]:
        raise AssertionError(f"fixture action was rejected: {action!r}")


def attached_env(*, count=1, metros=1, seed=811):
    env = MiniMetroEnv()
    env.reset(seed=seed)
    apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    for _ in range(metros):
        apply(env, {"type": "assign_locomotive", "path_index": 0})
    env.mediator.num_carriages = max(env.mediator.num_carriages, count)
    for _ in range(count):
        apply(env, {"type": "attach_carriage", "path_index": 0})
    return env


def set_carriage_field(value, index, field, replacement):
    value["carriages"][index][field] = replacement
    if index < len(value["structured"]["carriages"]):
        value["structured"]["carriages"][index][field] = replacement


def add_carriage_field(value, field, replacement):
    value["carriages"][0][field] = replacement
    value["structured"]["carriages"][0][field] = replacement


def set_global_reference(value, replacement):
    value["metroMotion"][0]["carriage_indices"][0] = replacement
    value["structured"]["metros"][0]["carriage_indices"][0] = replacement


def set_global_total_capacity(value, replacement):
    value["metroMotion"][0]["capacity"] = replacement
    value["structured"]["metros"][0]["capacity"] = replacement


def add_path_only_carriage(env, carriage):
    suffix = Metro()
    env.mediator.paths[0].add_metro(suffix)
    suffix.is_unassignment_queued = True
    suffix.carriages.append(carriage)
    return suffix


class TestGM06cCheckpointScalarValidation(unittest.TestCase):
    def test_v4_rejects_unknown_uuid_and_every_invalid_carriage_scalar(self):
        valid = canonical_checkpoint(attached_env(count=1), schema_version=4)
        mutations = {
            "unknown carriage key": lambda value: add_carriage_field(
                value, "unknown", 1
            ),
            "raw carriage id": lambda value: add_carriage_field(
                value, "id", "Carriage-process-local"
            ),
            "raw owner id": lambda value: add_carriage_field(
                value, "metro_id", "Metro-process-local"
            ),
            "boolean carriage capacity": lambda value: set_carriage_field(
                value, 0, "capacity", True
            ),
            "zero carriage capacity": lambda value: set_carriage_field(
                value, 0, "capacity", 0
            ),
            "negative carriage capacity": lambda value: set_carriage_field(
                value, 0, "capacity", -1
            ),
            "boolean owner": lambda value: set_carriage_field(
                value, 0, "metro_motion_index", False
            ),
            "negative owner": lambda value: set_carriage_field(
                value, 0, "metro_motion_index", -1
            ),
            "out-of-range owner": lambda value: set_carriage_field(
                value, 0, "metro_motion_index", 99
            ),
            "boolean attachment index": lambda value: set_carriage_field(
                value, 0, "attachment_index", False
            ),
            "negative attachment index": lambda value: set_carriage_field(
                value, 0, "attachment_index", -1
            ),
            "boolean reference": lambda value: set_global_reference(value, False),
            "negative reference": lambda value: set_global_reference(value, -1),
            "out-of-range reference": lambda value: set_global_reference(value, 99),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(valid)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                normalize_checkpoint(candidate)

    def test_v4_rejects_float_string_and_none_for_every_new_integer_domain(self):
        valid = canonical_checkpoint(attached_env(count=1, seed=812), schema_version=4)
        setters = {
            "carriage capacity": lambda value, replacement: set_carriage_field(
                value, 0, "capacity", replacement
            ),
            "carriage owner": lambda value, replacement: set_carriage_field(
                value, 0, "metro_motion_index", replacement
            ),
            "attachment index": lambda value, replacement: set_carriage_field(
                value, 0, "attachment_index", replacement
            ),
            "carriage reference": set_global_reference,
            "inventory limit": lambda value, replacement: value["progression"][
                "limits"
            ].__setitem__("num_carriages", replacement),
            "fleet total": lambda value, replacement: value["structured"][
                "fleet"
            ].__setitem__("carriages_total", replacement),
            "fleet assigned": lambda value, replacement: value["structured"][
                "fleet"
            ].__setitem__("carriages_assigned", replacement),
            "fleet available": lambda value, replacement: value["structured"][
                "fleet"
            ].__setitem__("carriages_available", replacement),
            "base capacity": lambda value, replacement: value["metroMotion"][
                0
            ].__setitem__("base_capacity", replacement),
            "total capacity": set_global_total_capacity,
        }
        for name, setter in setters.items():
            for invalid in (1.0, "1", None):
                candidate = deepcopy(valid)
                setter(candidate, invalid)
                with (
                    self.subTest(name=name, invalid=invalid),
                    self.assertRaises(ValueError),
                ):
                    normalize_checkpoint(candidate)

    def test_v4_rejects_uuid_fields_outside_canonical_carriage_records(self):
        valid = canonical_checkpoint(attached_env(count=1, seed=8121), schema_version=4)
        mutations = {
            "structured Metro carriage IDs": lambda value: value["structured"][
                "metros"
            ][0].__setitem__("carriage_ids", ["Carriage-process-local"]),
            "structured Metro owner ID": lambda value: value["structured"]["metros"][
                0
            ].__setitem__("metro_id", "Metro-process-local"),
            "motion carriage IDs": lambda value: value["metroMotion"][0].__setitem__(
                "carriage_ids", ["Carriage-process-local"]
            ),
            "motion Metro ID": lambda value: value["metroMotion"][0].__setitem__(
                "metro_id", "Metro-process-local"
            ),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(valid)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                normalize_checkpoint(candidate)

    def test_v4_rejects_bool_negative_inventory_and_capacity_equations(self):
        valid = canonical_checkpoint(attached_env(count=1, seed=813), schema_version=4)
        mutations = {
            "boolean inventory limit": lambda value: value["progression"][
                "limits"
            ].__setitem__("num_carriages", True),
            "negative inventory limit": lambda value: value["progression"][
                "limits"
            ].__setitem__("num_carriages", -1),
            "boolean fleet total": lambda value: value["structured"][
                "fleet"
            ].__setitem__("carriages_total", True),
            "negative fleet total": lambda value: value["structured"][
                "fleet"
            ].__setitem__("carriages_total", -1),
            "boolean fleet assigned": lambda value: value["structured"][
                "fleet"
            ].__setitem__("carriages_assigned", True),
            "negative fleet assigned": lambda value: value["structured"][
                "fleet"
            ].__setitem__("carriages_assigned", -1),
            "boolean fleet available": lambda value: value["structured"][
                "fleet"
            ].__setitem__("carriages_available", True),
            "negative fleet available": lambda value: value["structured"][
                "fleet"
            ].__setitem__("carriages_available", -1),
            "boolean base capacity": lambda value: value["metroMotion"][0].__setitem__(
                "base_capacity", True
            ),
            "negative base capacity": lambda value: value["metroMotion"][0].__setitem__(
                "base_capacity", -1
            ),
            "boolean total capacity": lambda value: set_global_total_capacity(
                value, True
            ),
            "negative total capacity": lambda value: set_global_total_capacity(
                value, -1
            ),
            "base plus carriage mismatch": lambda value: value["metroMotion"][
                0
            ].__setitem__("base_capacity", 7),
            "total capacity mismatch": lambda value: set_global_total_capacity(
                value, 13
            ),
            "fleet formula mismatch": lambda value: value["structured"][
                "fleet"
            ].__setitem__("carriages_available", 99),
            "coherent assigned count mismatch": lambda value: value["structured"][
                "fleet"
            ].update({"carriages_assigned": 2, "carriages_available": 0}),
            "inventory limit and fleet total mismatch": lambda value: value[
                "progression"
            ]["limits"].__setitem__("num_carriages", 3),
            "queue composition mismatch": lambda value: value["structured"]["metros"][
                0
            ].__setitem__(
                "unassignment_queued",
                not value["metroMotion"][0]["unassignment_queued"],
            ),
        }
        for name, mutate in mutations.items():
            candidate = deepcopy(valid)
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                normalize_checkpoint(candidate)


class TestGM06cCheckpointCompositionValidation(unittest.TestCase):
    def test_generation_rejects_duplicate_owner_and_duck_typed_carriage(self):
        duplicate = attached_env(count=1, seed=8130)
        path = duplicate.mediator.paths[0]
        path.metros.append(path.metros[0])
        with self.subTest(corruption="duplicate owner"), self.assertRaises(ValueError):
            canonical_checkpoint(duplicate, schema_version=4)

        duck = attached_env(count=1, seed=8131)
        real = duck.mediator.metros[0].carriages[0]
        duck.mediator.metros[0].carriages[0] = SimpleNamespace(
            id=real.id,
            capacity=real.capacity,
        )
        with self.subTest(corruption="duck carriage"), self.assertRaises(ValueError):
            canonical_checkpoint(duck, schema_version=4)

    def test_v4_rejects_duplicate_topology_metro_ownership_reference(self):
        valid = canonical_checkpoint(attached_env(count=1, seed=8132), schema_version=4)
        corruptions = {
            "duplicate topology reference": lambda item: item["topology"]["paths"][0][
                "metro_indices"
            ].append(0),
            "missing actual owner": lambda item: item["metroMotion"][0].__setitem__(
                "path_index", None
            ),
            "out-of-range actual owner": lambda item: item["metroMotion"][
                0
            ].__setitem__("path_index", 99),
            "boolean actual owner": lambda item: item["metroMotion"][0].__setitem__(
                "path_index", False
            ),
        }
        for name, corrupt in corruptions.items():
            checkpoint = deepcopy(valid)
            corrupt(checkpoint)
            with self.subTest(corruption=name), self.assertRaises(ValueError):
                normalize_checkpoint(checkpoint)

    def test_v4_preserves_valid_per_path_order_distinct_from_global_order(self):
        env = attached_env(count=1, metros=2, seed=8133)
        env.mediator.paths[0].metros.reverse()

        checkpoint = canonical_checkpoint(env, schema_version=4)

        self.assertEqual(checkpoint["topology"]["paths"][0]["metro_indices"], [1, 0])
        self.assertEqual(normalize_checkpoint(checkpoint), checkpoint)

        suffix_env = attached_env(count=1, seed=8134)
        carriage_type = type(suffix_env.mediator.metros[0].carriages[0])
        suffix = add_path_only_carriage(suffix_env, carriage_type())
        path = suffix_env.mediator.paths[0]
        path.metros.remove(suffix)
        path.metros.insert(0, suffix)

        suffix_checkpoint = canonical_checkpoint(suffix_env, schema_version=4)
        self.assertEqual(
            suffix_checkpoint["topology"]["paths"][0]["metro_indices"],
            [1, 0],
        )
        self.assertEqual(normalize_checkpoint(suffix_checkpoint), suffix_checkpoint)

    def test_v4_rejects_coherent_but_interleaved_owner_slices(self):
        env = attached_env(count=4, metros=2, seed=821)
        valid = canonical_checkpoint(env, schema_version=4)
        self.assertEqual(
            [len(metro["carriage_indices"]) for metro in valid["metroMotion"]],
            [2, 2],
        )

        candidate = deepcopy(valid)
        records = candidate["carriages"]
        candidate["carriages"] = [records[0], records[2], records[1], records[3]]
        candidate["structured"]["carriages"] = deepcopy(candidate["carriages"])
        candidate["metroMotion"][0]["carriage_indices"] = [0, 2]
        candidate["metroMotion"][1]["carriage_indices"] = [1, 3]
        candidate["structured"]["metros"][0]["carriage_indices"] = [0, 2]
        candidate["structured"]["metros"][1]["carriage_indices"] = [1, 3]

        with self.assertRaises(ValueError):
            normalize_checkpoint(candidate)

    def test_generation_rejects_duplicate_identity_id_and_aliased_lists(self):
        def shared_identity(env):
            env.mediator.metros[1].carriages[0] = env.mediator.metros[0].carriages[0]

        def duplicate_id(env):
            env.mediator.metros[1].carriages[0].id = (
                env.mediator.metros[0].carriages[0].id
            )

        def aliased_lists(env):
            env.mediator.metros[1].carriages = env.mediator.metros[0].carriages

        for name, corrupt in (
            ("shared identity", shared_identity),
            ("duplicate id", duplicate_id),
            ("aliased carriage lists", aliased_lists),
        ):
            env = attached_env(count=2, metros=2, seed=823)
            corrupt(env)
            with self.subTest(name=name), self.assertRaises(ValueError):
                canonical_checkpoint(env, schema_version=4)

    def test_generation_rejects_shared_empty_carriage_list_without_other_corruption(
        self,
    ):
        env = attached_env(count=0, metros=2, seed=824)
        shared = []
        env.mediator.metros[0].carriages = shared
        env.mediator.metros[1].carriages = shared

        with self.assertRaises(ValueError):
            canonical_checkpoint(env, schema_version=4)

    def test_generation_rejects_global_suffix_duplicate_identity_and_id(self):
        for duplicate in ("identity", "id"):
            env = attached_env(count=1, seed=825)
            canonical = env.mediator.metros[0].carriages[0]
            if duplicate == "identity":
                suffix_carriage = canonical
            else:
                suffix_carriage = type(canonical)()
                suffix_carriage.id = canonical.id
            add_path_only_carriage(env, suffix_carriage)

            with self.subTest(duplicate=duplicate), self.assertRaises(ValueError):
                canonical_checkpoint(env, schema_version=4)

    def test_normalizer_rejects_passenger_overcapacity_even_when_totals_balance(self):
        env = attached_env(count=0, seed=826)
        metro = env.mediator.metros[0]
        passenger = Passenger(env.mediator.stations[0].shape)
        metro.add_passenger(passenger)
        env.mediator.passengers.append(passenger)
        valid = canonical_checkpoint(env, schema_version=4)
        candidate = deepcopy(valid)
        candidate["metroMotion"][0]["base_capacity"] = 0
        set_global_total_capacity(candidate, 0)

        with self.assertRaises(ValueError):
            normalize_checkpoint(candidate)

    def test_generation_rejects_passenger_overcapacity(self):
        env = attached_env(count=0, seed=827)
        metro = env.mediator.metros[0]
        metro._base_capacity = 0
        passenger = Passenger(env.mediator.stations[0].shape)
        metro.passengers.append(passenger)
        env.mediator.passengers.append(passenger)
        self.assertGreater(len(metro.passengers), metro.capacity)
        with self.assertRaises(ValueError):
            canonical_checkpoint(env, schema_version=4)

    def test_generation_accepts_matching_service_cache_and_rejects_stale_parts(self):
        env = attached_env(count=0, seed=829)
        mediator = env.mediator
        path = mediator.paths[0]
        metro = mediator.metros[0]
        start = path.stations[0]
        metro.current_station = start
        metro.position = start.position
        for existing in tuple(start.passengers):
            start.remove_passenger(existing)
            if existing in mediator.passengers:
                mediator.passengers.remove(existing)
            mediator.travel_plans.pop(existing, None)
        rider = boardable_passenger(
            mediator,
            start,
            path.stations[1],
            path,
            name="checkpoint-current-boarder",
        )
        mediator.move_passengers(250)
        current = metro._station_service_action
        self.assertIsNotNone(current)
        assert current is not None
        kind, planned = current
        self.assertIs(planned, rider)

        checkpoint = canonical_checkpoint(env, schema_version=4)
        self.assertEqual(checkpoint["schemaVersion"], 4)

        stale_actions = (
            ("not-the-current-kind", rider),
            (kind, Passenger(path.stations[1].shape)),
        )
        for stale in stale_actions:
            metro._station_service_action = stale
            with self.subTest(stale=stale), self.assertRaises(ValueError):
                canonical_checkpoint(env, schema_version=4)
        metro._station_service_action = current


if __name__ == "__main__":
    unittest.main()
