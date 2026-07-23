"""GM-08a red contract: the ``settings`` typed store (D-029).

Mints the persistent, presentation-only settings document type: a typed frozen
``Settings`` with defaults, strict versioned validation, FAIL-SAFE-TO-DEFAULTS
loading (a missing or malformed file never raises), and the GM-07b atomic
canonical-ASCII writer. Every missing product surface becomes a clean FAILURE
(never an import/collection ERROR) through the ``require_attribute`` guards,
mirroring ``test_gm07d_highscores``.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

SETTINGS_MODULE = "settings"
STATE_CONTRACT = "mini-metro-settings-v1"


def _module(testcase, name=SETTINGS_MODULE):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-08a product module is missing: {name} ({error})")


def _symbol(testcase, name, module_name=SETTINGS_MODULE):
    value = getattr(_module(testcase, module_name), name, None)
    testcase.assertIsNotNone(
        value, f"GM-08a product symbol is missing: {module_name}.{name}"
    )
    return value


def _valid_doc(**overrides) -> dict:
    document = {
        "schemaVersion": 1,
        "stateContract": STATE_CONTRACT,
        "fullscreen": False,
        "masterVolume": 100,
        "musicVolume": 100,
        "sfxVolume": 100,
        "reducedMotion": False,
    }
    document.update(overrides)
    return document


class TestGM08aSettingsConstants(unittest.TestCase):
    def test_versioned_constants(self):
        module = _module(self)
        for name, expected in (
            ("SETTINGS_SCHEMA_VERSION", 1),
            ("SETTINGS_STATE_CONTRACT", STATE_CONTRACT),
        ):
            self.assertEqual(getattr(module, name, None), expected, name)

    def test_default_settings_are_the_documented_defaults(self):
        default = _symbol(self, "DEFAULT_SETTINGS")
        self.assertIs(default.fullscreen, False)
        self.assertIs(default.reduced_motion, False)
        self.assertEqual(
            (default.master_volume, default.music_volume, default.sfx_volume),
            (100, 100, 100),
        )

    def test_settings_is_an_immutable_value(self):
        default = _symbol(self, "DEFAULT_SETTINGS")
        with self.assertRaises(Exception):
            default.fullscreen = True  # frozen dataclass -> FrozenInstanceError


class TestGM08aValidateSettings(unittest.TestCase):
    def test_accepts_a_valid_document(self):
        validate = _symbol(self, "validate_settings")
        self.assertIsNone(validate(_valid_doc()))
        self.assertIsNone(validate(_valid_doc(fullscreen=True, reducedMotion=True)))
        self.assertIsNone(validate(_valid_doc(masterVolume=0, sfxVolume=100)))

    def _assert_rejected(self, mutations):
        validate = _symbol(self, "validate_settings")
        for name, mutate in mutations.items():
            candidate = _valid_doc()
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate(candidate)

    def test_header_strictness(self):
        self._assert_rejected(
            {
                "forward schemaVersion": lambda d: d.update(schemaVersion=2),
                "zero schemaVersion": lambda d: d.update(schemaVersion=0),
                "bool schemaVersion": lambda d: d.update(schemaVersion=True),
                "string schemaVersion": lambda d: d.update(schemaVersion="1"),
                "float schemaVersion": lambda d: d.update(schemaVersion=1.0),
                "wrong stateContract": lambda d: d.update(stateContract="other"),
                "null stateContract": lambda d: d.update(stateContract=None),
            }
        )

    def test_exact_key_set(self):
        self._assert_rejected(
            {
                "unknown key": lambda d: d.update(extra=1),
                "missing fullscreen": lambda d: d.pop("fullscreen"),
                "missing masterVolume": lambda d: d.pop("masterVolume"),
                "missing reducedMotion": lambda d: d.pop("reducedMotion"),
                "missing schemaVersion": lambda d: d.pop("schemaVersion"),
            }
        )
        validate = _symbol(self, "validate_settings")
        for bad in ([], "x", 3, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(bad)

    def test_field_type_strictness(self):
        self._assert_rejected(
            {
                "int fullscreen": lambda d: d.update(fullscreen=1),
                "string fullscreen": lambda d: d.update(fullscreen="true"),
                "int reducedMotion": lambda d: d.update(reducedMotion=0),
                "bool masterVolume": lambda d: d.update(masterVolume=True),
                "float masterVolume": lambda d: d.update(masterVolume=50.0),
                "string masterVolume": lambda d: d.update(masterVolume="50"),
                "negative musicVolume": lambda d: d.update(musicVolume=-1),
                "over-100 sfxVolume": lambda d: d.update(sfxVolume=101),
            }
        )

    def test_duplicate_json_keys_are_rejected(self):
        reject_hook = _symbol(self, "_reject_duplicate_keys")
        with self.assertRaises(ValueError):
            json.loads(
                '{"schemaVersion":1,"schemaVersion":1}', object_pairs_hook=reject_hook
            )

    def test_non_string_keys_raise_valueerror_not_typeerror(self):
        # A directly-built dict with mixed non-string keys must raise ValueError,
        # never let the shared _exact_keys sorted() leak a TypeError (codex).
        validate = _symbol(self, "validate_settings")
        document = _valid_doc()
        document[1] = "x"
        document[None] = "y"
        with self.assertRaises(ValueError):
            validate(document)


class TestGM08aSettingsRoundtrip(unittest.TestCase):
    def test_settings_to_document_and_back(self):
        settings_from = _symbol(self, "settings_from_document")
        settings_to = _symbol(self, "settings_to_document")
        document = _valid_doc(fullscreen=True, masterVolume=40, reducedMotion=True)
        value = settings_from(document)
        self.assertIs(value.fullscreen, True)
        self.assertEqual(value.master_volume, 40)
        self.assertIs(value.reduced_motion, True)
        self.assertEqual(settings_to(value), document, "round trip is exact")

    def test_defaults_round_trip(self):
        settings_to = _symbol(self, "settings_to_document")
        settings_from = _symbol(self, "settings_from_document")
        default = _symbol(self, "DEFAULT_SETTINGS")
        self.assertEqual(settings_from(settings_to(default)), default)

    def test_settings_from_document_validates(self):
        settings_from = _symbol(self, "settings_from_document")
        with self.assertRaises(ValueError):
            settings_from(_valid_doc(masterVolume=101))


class TestGM08aLoadSettings(unittest.TestCase):
    def _load(self, payload: bytes | None):
        load_settings = _symbol(self, "load_settings")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "settings.json"
            if payload is not None:
                target.write_bytes(payload)
            return load_settings(target)

    def test_valid_file_returns_the_typed_settings(self):
        document = _valid_doc(fullscreen=True, sfxVolume=25)
        loaded = self._load(json.dumps(document).encode("ascii"))
        self.assertIs(loaded.fullscreen, True)
        self.assertEqual(loaded.sfx_volume, 25)

    def test_fail_safe_to_defaults_on_missing_or_corrupt(self):
        default = _symbol(self, "DEFAULT_SETTINGS")
        deep = ("[" * 200_000 + "]" * 200_000).encode("ascii")
        cases = {
            "missing": None,
            "empty": b"",
            "not json": b"{ not json",
            "truncated": b'{"schemaVersion":1,',
            "null": b"null",
            "array top": b"[]",
            "forward version": json.dumps(_valid_doc(schemaVersion=2)).encode("ascii"),
            "bad type": json.dumps(_valid_doc(masterVolume=999)).encode("ascii"),
            "non-ascii byte": b'{"stateContract":"caf\xe9"}',
            "deep nested": deep,
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self._load(payload),
                    default,
                    f"{name} must fail safe to the typed defaults",
                )


class TestGM08aSaveSettings(unittest.TestCase):
    def test_save_writes_canonical_ascii_bytes(self):
        save_settings = _symbol(self, "save_settings")
        settings_to = _symbol(self, "settings_to_document")
        value = _symbol(self, "settings_from_document")(_valid_doc(musicVolume=30))
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "settings.json"
            save_settings(value, target)
            payload = target.read_bytes()
        expected = (
            json.dumps(
                settings_to(value),
                allow_nan=False,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("ascii")
            + b"\n"
        )
        self.assertEqual(payload, expected)
        self.assertNotIn(b"\r", payload)
        self.assertEqual(payload.count(b"\n"), 1)

    def test_round_trips_through_disk(self):
        save_settings = _symbol(self, "save_settings")
        load_settings = _symbol(self, "load_settings")
        value = _symbol(self, "settings_from_document")(
            _valid_doc(fullscreen=True, masterVolume=10, reducedMotion=True)
        )
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "settings.json"
            save_settings(value, target)
            self.assertEqual(load_settings(target), value, "settings survive restart")

    def test_interrupted_replace_preserves_the_prior_file_without_litter(self):
        save_settings = _symbol(self, "save_settings")
        value = _symbol(self, "DEFAULT_SETTINGS")
        created: list[str] = []
        real_mkstemp = tempfile.mkstemp

        def recording_mkstemp(*args, **kwargs):
            descriptor, name = real_mkstemp(*args, **kwargs)
            created.append(name)
            return descriptor, name

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "settings.json"
            target.write_bytes(b"precious-bytes\n")
            with (
                mock.patch("tempfile.mkstemp", recording_mkstemp),
                mock.patch("os.replace", side_effect=OSError("injected")),
            ):
                with self.assertRaises(OSError):
                    save_settings(value, target)
            self.assertEqual(len(created), 1)
            self.assertFalse(Path(created[0]).exists(), "no .tmp litter")
            self.assertEqual(target.read_bytes(), b"precious-bytes\n")
            self.assertEqual(os.listdir(directory), ["settings.json"])

    def test_fdopen_failure_closes_descriptor_and_never_masks_the_error(self):
        # Regression for the fd-ownership guard (mirrors GM-07d:C): when os.fdopen
        # raises, the raw descriptor must be closed so it cannot leak and the
        # cleanup unlink cannot mask the original error with a PermissionError.
        save_settings = _symbol(self, "save_settings")
        value = _symbol(self, "DEFAULT_SETTINGS")
        captured: dict[str, object] = {}
        real_mkstemp = tempfile.mkstemp

        def recording_mkstemp(*args, **kwargs):
            descriptor, name = real_mkstemp(*args, **kwargs)
            captured["fd"] = descriptor
            captured["name"] = name
            return descriptor, name

        sentinel = OSError("injected fdopen failure")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "settings.json"
            target.write_bytes(b"precious-bytes\n")
            with (
                mock.patch("tempfile.mkstemp", recording_mkstemp),
                mock.patch("os.fdopen", side_effect=sentinel),
            ):
                with self.assertRaises(OSError) as raised:
                    save_settings(value, target)
            self.assertIs(raised.exception, sentinel, "the original error is unmasked")
            # The guard already closed the raw fd, so closing it again fails.
            with self.assertRaises(OSError):
                os.close(captured["fd"])  # type: ignore[arg-type]
            self.assertFalse(Path(captured["name"]).exists(), "no .tmp litter")
            self.assertEqual(target.read_bytes(), b"precious-bytes\n")

    def test_save_rejects_and_never_persists_an_invalid_settings_document(self):
        # save validates the derived document before writing, so a hand-built
        # out-of-range value can never overwrite a valid file (mirrors GM-07d).
        save_settings = _symbol(self, "save_settings")
        settings_type = _symbol(self, "Settings")
        bogus = settings_type(master_volume=999)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "settings.json"
            target.write_bytes(b"precious-bytes\n")
            with self.assertRaises(ValueError):
                save_settings(bogus, target)
            self.assertEqual(target.read_bytes(), b"precious-bytes\n")


if __name__ == "__main__":
    unittest.main()
