"""GM-07b determinism reds: lockstep replay, isolation, and the v1 fixture."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

import numpy as np

from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
FIXTURE_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v1.json"
# GM-09f: the DETERMINISTIC v1->v2 upgrade of save-v1.json -- identical bytes except
# schemaVersion 2 + the sorted-inserted map identity (classic@1). A v1 save now
# re-saves as exactly these bytes (the upgrade is pinned), and this v2 fixture is
# self-idempotent on re-save.
FIXTURE_V2_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v2-classic.json"
# GM-10h: the DETERMINISTIC v2->v3 upgrade -- identical bytes except schemaVersion 3
# + the sorted-inserted additive `tunnelBonus: 0`. A v1 OR v2 save now re-saves as
# exactly these v3 bytes (the current version), and this v3 fixture is self-idempotent.
FIXTURE_V3_PATH = REPO_ROOT / "scripts" / "fixtures" / "save-v3-classic.json"
SAVE_GAME_MODULE = "save_game"
SAVE_SCHEMA_MODULE = "save_schema"
# Modules only `main` may import: the save/load stack plus the main-owned
# persistence and runtime seams (highscores, settings, and the GM-08b `audio`
# backend). The name is historical — the set now also guards a non-save runtime
# module — but the guarantee is unchanged: no headless/agent/RL surface imports
# any of these (GM-08b, review MINOR-5).
SAVE_MODULE_NAMES = {
    "save_game",
    "save_schema",
    "save_load",
    "save_schema_records",
    "highscores",
    "settings",
    "audio",
}

# PLACEHOLDER pins — the implementer freezes scripts/fixtures/save-v1.json by
# writing the exact bytes of _fixture_bytes() (the seeded scenario below) and
# then fills the real byte length and SHA-256 digest here. Until the freeze,
# the fixture tests fail cleanly on the missing file / unfilled pins.
EXPECTED_SAVE_V1_BYTE_LENGTH: int | None = 15442
EXPECTED_SAVE_V1_SHA256: str | None = (
    "d34736a6dfe1023e3ce9a9c9a9d2f9428a1d6e2c696d83fb31838ae22deacd1e"
)
# GM-09f: the frozen v2-classic upgrade bytes (save-v1.json + header-only delta).
EXPECTED_SAVE_V2_BYTE_LENGTH: int | None = 15485
EXPECTED_SAVE_V2_SHA256: str | None = (
    "60f2bc16c39610b8822288ebf08eea214cb2d0f54c9ac0208113a0892badbd84"
)
# GM-10h: the frozen v3-classic upgrade bytes (save-v2-classic.json + additive
# "tunnelBonus":0). This is now the LATEST version a re-save of v1/v2/v3 produces.
EXPECTED_SAVE_V3_BYTE_LENGTH: int | None = 15501
EXPECTED_SAVE_V3_SHA256: str | None = (
    "50d7d2c4390db42b4b3ee013bdf8f79ba5c72d0e6b5c0231a289920bdf6400df"
)

_WORKER = """\
import hashlib
import json
import sys

sys.path.insert(0, __SRC__)

import save_game
from env import MiniMetroEnv
from recursive_checkpoint import canonical_checkpoint


def canonical_bytes(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


mode, target = sys.argv[1], sys.argv[2]
if mode == "resave":
    # Entity IDs are shortuuid-minted independently of the game seed, so a
    # fresh build is never byte-reproducible across processes; the honest
    # hash-seed oracle is load -> re-save idempotence over the frozen bytes.
    loaded = save_game.load_game(sys.argv[3])
    save_game.save_game(loaded, target)
    with open(target, "rb") as handle:
        payload = handle.read()
    print(
        json.dumps(
            {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
            }
        )
    )
else:
    loaded = save_game.load_game(target)
    # The fixture holds the menu pause reason; release it so the replay
    # exercises ACTIVE ticks (movement, boarding, spawning), not pauses.
    loaded.release_pause_reason("menu")
    env = MiniMetroEnv(dt_ms=250)
    env.mediator = loaded
    env.last_deliveries = loaded.deliveries
    env.last_line_credits = loaded.line_credits
    chunks = []
    for _ in range(10):
        env.step({"type": "noop"})
        chunks.append(canonical_bytes(canonical_checkpoint(env)))
    print(
        json.dumps(
            {
                "digest": hashlib.sha256(b"|".join(chunks)).hexdigest(),
                "ticks": len(chunks),
                "time_ms": env.mediator.time_ms,
            }
        )
    )
"""


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


def _canonical_bytes(value):
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


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


def _saved_then_loaded(testcase, env):
    save_game = _symbol(testcase, SAVE_GAME_MODULE, "save_game")
    load_game = _symbol(testcase, SAVE_GAME_MODULE, "load_game")
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "game.save.json"
        save_game(env.mediator, target)
        loaded = load_game(target)
    wrapped = MiniMetroEnv(dt_ms=env.dt_ms_default, reward_mode=env.reward_mode)
    wrapped.mediator = loaded
    wrapped.last_deliveries = env.last_deliveries
    wrapped.last_line_credits = env.last_line_credits
    wrapped.last_score = env.last_score
    return wrapped


def _assert_numpy_random_state_equal(case, left, right):
    case.assertEqual(left[0], right[0])
    np.testing.assert_array_equal(left[1], right[1])
    case.assertEqual(left[2:], right[2:])


def _fixture_bytes(testcase):
    serialize_game = _symbol(testcase, SAVE_GAME_MODULE, "serialize_game")
    canonical_save_bytes = _symbol(testcase, SAVE_SCHEMA_MODULE, "canonical_save_bytes")
    env = MiniMetroEnv(dt_ms=250)
    env.reset(seed=4207)
    _apply(env, {"type": "create_path", "stations": [0, 1, 2], "loop": False})
    _apply(env, {"type": "assign_locomotive", "path_index": 0})
    _apply(env, {"type": "attach_carriage", "path_index": 0})
    for _ in range(8):
        env.step({"type": "noop"})
    env.mediator.hold_pause_reason("menu")
    return canonical_save_bytes(serialize_game(env.mediator))


class TestGM07bLockstepTrajectory(unittest.TestCase):
    def test_loaded_env_replays_lockstep_with_never_saved_control(self):
        control = _line_env(4501, dt_ms=17)
        for _ in range(5):
            control.step({"type": "noop"})
        loaded = _saved_then_loaded(self, control)
        self.assertEqual(
            _canonical_bytes(canonical_checkpoint(control)),
            _canonical_bytes(canonical_checkpoint(loaded)),
        )
        for tick in range(12):
            control.step({"type": "noop"})
            loaded.step({"type": "noop"})
            self.assertEqual(
                _canonical_bytes(canonical_checkpoint(control)),
                _canonical_bytes(canonical_checkpoint(loaded)),
                f"trajectories diverged at tick {tick}",
            )

    def test_save_and_load_do_not_touch_host_global_rngs(self):
        random.seed(8128)
        np.random.seed(4096)
        python_before = random.getstate()
        numpy_before = np.random.get_state()

        control = _line_env(4502, dt_ms=17)
        loaded = _saved_then_loaded(self, control)
        for _ in range(5):
            control.step({"type": "noop"})
            loaded.step({"type": "noop"})

        self.assertEqual(random.getstate(), python_before)
        _assert_numpy_random_state_equal(self, np.random.get_state(), numpy_before)


class TestGM07bFreshProcessIdentity(unittest.TestCase):
    def _run_worker(self, worker, mode, target, environment, source=None):
        command = [sys.executable, str(worker), mode, str(target)]
        if source is not None:
            command.append(str(source))
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout.strip().splitlines()[-1])

    def test_distinct_hash_seed_processes_agree_byte_for_byte(self):
        # Requires the save modules; probe them first for a clean red FAIL.
        # Entity IDs are shortuuid-minted independently of the game seed, so
        # fresh builds are never byte-reproducible across processes; the honest
        # oracle is cross-process load -> re-save idempotence over the frozen
        # fixture bytes, which pins the serializer. DISTINCT hash seeds per
        # worker (plus the test process's own third seed) pin hash-seed
        # independence; the replay releases the menu hold and must advance
        # real active ticks, byte-agreeing with the in-process control.
        _symbol(self, SAVE_GAME_MODULE, "save_game")
        load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
        environment_one = {**os.environ, "PYTHONHASHSEED": "1"}
        environment_two = {**os.environ, "PYTHONHASHSEED": "2"}
        with tempfile.TemporaryDirectory() as directory:
            worker = Path(directory) / "gm07b_worker.py"
            worker.write_text(
                _WORKER.replace("__SRC__", json.dumps(str(SRC_ROOT))),
                encoding="utf-8",
            )
            save_a = Path(directory) / "save-a.json"
            save_b = Path(directory) / "save-b.json"
            first_save = self._run_worker(
                worker, "resave", save_a, environment_one, source=FIXTURE_PATH
            )
            second_save = self._run_worker(
                worker, "resave", save_b, environment_two, source=FIXTURE_PATH
            )
            self.assertEqual(first_save, second_save)
            self.assertEqual(save_a.read_bytes(), save_b.read_bytes())
            # GM-10h: re-saving the frozen v1 save UPGRADES it to the CURRENT version
            # (v3) deterministically, so both hash-seed workers emit exactly the frozen
            # save-v3-classic bytes (hash-seed independence proven against the pinned
            # upgrade, not v1).
            self.assertEqual(save_a.read_bytes(), FIXTURE_V3_PATH.read_bytes())

            first_replay = self._run_worker(worker, "replay", save_a, environment_one)
            second_replay = self._run_worker(worker, "replay", save_a, environment_two)
            self.assertEqual(first_replay, second_replay)
            self.assertEqual(first_replay["ticks"], 10)
            # Ten released ticks at dt 250 from the fixture's 2000 ms: the
            # replay provably ran active simulation, not paused no-ops.
            self.assertEqual(first_replay["time_ms"], 2_000 + 10 * 250)

            loaded = load_game(save_a)
            loaded.release_pause_reason("menu")
            env = MiniMetroEnv(dt_ms=250)
            env.mediator = loaded
            env.last_deliveries = loaded.deliveries
            env.last_line_credits = loaded.line_credits
            chunks = []
            for _ in range(10):
                env.step({"type": "noop"})
                chunks.append(_canonical_bytes(canonical_checkpoint(env)))
            in_process = hashlib.sha256(b"|".join(chunks)).hexdigest()
            self.assertEqual(in_process, first_replay["digest"])
            self.assertEqual(env.mediator.time_ms, first_replay["time_ms"])


class TestGM07bIsolation(unittest.TestCase):
    def test_runtime_surfaces_gain_no_save_imports(self):
        # regression guard: green at baseline (no surface imports a main-owned
        # module); the scan forbids every name in SAVE_MODULE_NAMES (the save
        # stack plus highscores/settings/audio) and includes the one-way
        # checkpoint verifier boundary.
        targets = [
            SRC_ROOT / "env.py",
            SRC_ROOT / "agent_play.py",
            SRC_ROOT / "recursive_playtest.py",
            SRC_ROOT / "recursive_checkpoint.py",
            *sorted((SRC_ROOT / "rl").glob("*.py")),
        ]
        self.assertGreater(len(targets), 4)
        for target in targets:
            tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                else:
                    continue
                for name in names:
                    self.assertNotIn(
                        name.split(".")[0],
                        SAVE_MODULE_NAMES,
                        f"{target.relative_to(REPO_ROOT)} imports {name}",
                    )


class TestGM07bFrozenFixture(unittest.TestCase):
    def test_frozen_save_v1_fixture_bytes_are_pinned(self):
        self.assertTrue(
            FIXTURE_PATH.exists(),
            "scripts/fixtures/save-v1.json is missing - freeze it from the "
            "_fixture_bytes recipe and fill the pins above",
        )
        payload = FIXTURE_PATH.read_bytes()
        self.assertNotIn(b"\r", payload)
        self.assertTrue(payload.endswith(b"\n"))
        self.assertIsNotNone(
            EXPECTED_SAVE_V1_BYTE_LENGTH, "fixture byte-length pin is unfilled"
        )
        self.assertIsNotNone(EXPECTED_SAVE_V1_SHA256, "fixture SHA-256 pin is unfilled")
        self.assertEqual(len(payload), EXPECTED_SAVE_V1_BYTE_LENGTH)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V1_SHA256)

    def test_frozen_save_v2_classic_fixture_bytes_are_pinned(self):
        # GM-09f: the v2-classic upgrade fixture is byte-frozen (LF, no CR), so the
        # v1->v2 upgrade the idempotence/cross-process tests pin can never silently
        # drift.
        self.assertTrue(FIXTURE_V2_PATH.exists(), "save-v2-classic.json is missing")
        payload = FIXTURE_V2_PATH.read_bytes()
        self.assertNotIn(b"\r", payload)
        self.assertTrue(payload.endswith(b"\n"))
        self.assertEqual(len(payload), EXPECTED_SAVE_V2_BYTE_LENGTH)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V2_SHA256)

    def test_frozen_save_v3_classic_fixture_bytes_are_pinned(self):
        # GM-10h: the v3-classic upgrade fixture is byte-frozen (LF, no CR), so the
        # v2->v3 additive-key upgrade the idempotence/cross-process tests pin can never
        # silently drift.
        self.assertTrue(FIXTURE_V3_PATH.exists(), "save-v3-classic.json is missing")
        payload = FIXTURE_V3_PATH.read_bytes()
        self.assertNotIn(b"\r", payload)
        self.assertTrue(payload.endswith(b"\n"))
        self.assertEqual(len(payload), EXPECTED_SAVE_V3_BYTE_LENGTH)
        self.assertEqual(hashlib.sha256(payload).hexdigest(), EXPECTED_SAVE_V3_SHA256)

    def test_frozen_fixture_matches_the_freeze_recipe_and_loads(self):
        self.assertTrue(
            FIXTURE_PATH.exists(),
            "scripts/fixtures/save-v1.json is missing - freeze it from the "
            "_fixture_bytes recipe and fill the pins above",
        )
        payload = FIXTURE_PATH.read_bytes()
        validate_save = _symbol(self, SAVE_SCHEMA_MODULE, "validate_save")
        self.assertIsNone(validate_save(json.loads(payload)))
        load_game = _symbol(self, SAVE_GAME_MODULE, "load_game")
        serialize_game = _symbol(self, SAVE_GAME_MODULE, "serialize_game")
        canonical_save_bytes = _symbol(self, SAVE_SCHEMA_MODULE, "canonical_save_bytes")
        deserialize_game = _symbol(self, SAVE_GAME_MODULE, "deserialize_game")
        loaded = load_game(FIXTURE_PATH)
        self.assertEqual(sorted(loaded._pause_reasons), ["menu"])
        self.assertEqual(loaded.time_ms, 2_000)
        self.assertEqual(len(loaded.paths), 1)
        self.assertEqual(len(loaded.metros[0].carriages), 1)
        # GM-10h: loading the frozen v1 save and re-saving it now UPGRADES it to the
        # CURRENT version (v3) -- a deterministic additive-keys transform -- so the
        # re-save equals the frozen save-v3-classic.json byte-for-byte. v2 ALSO upgrades
        # to v3, and v3 is self-idempotent on re-save (v1->v3, v2->v3, v3->v3).
        v3_payload = FIXTURE_V3_PATH.read_bytes()
        self.assertEqual(canonical_save_bytes(serialize_game(loaded)), v3_payload)
        self.assertEqual(
            canonical_save_bytes(serialize_game(load_game(FIXTURE_V2_PATH))), v3_payload
        )
        self.assertEqual(
            canonical_save_bytes(serialize_game(load_game(FIXTURE_V3_PATH))), v3_payload
        )
        # The freeze recipe regenerates the same STATE modulo entity IDs:
        # compare through the UUID-free checkpoint oracle instead of bytes.
        regenerated = deserialize_game(json.loads(_fixture_bytes(self)))
        for mediator in (loaded, regenerated):
            self.assertEqual(sorted(mediator._pause_reasons), ["menu"])
        fixture_env = MiniMetroEnv(dt_ms=250)
        fixture_env.mediator = loaded
        fixture_env.last_deliveries = loaded.deliveries
        fixture_env.last_line_credits = loaded.line_credits
        regenerated_env = MiniMetroEnv(dt_ms=250)
        regenerated_env.mediator = regenerated
        regenerated_env.last_deliveries = regenerated.deliveries
        regenerated_env.last_line_credits = regenerated.line_credits
        self.assertEqual(
            _canonical_bytes(canonical_checkpoint(fixture_env)),
            _canonical_bytes(canonical_checkpoint(regenerated_env)),
        )


if __name__ == "__main__":
    unittest.main()
