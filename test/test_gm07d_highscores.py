"""GM-07d red contract: the ``highscores`` leaderboard module (D-028).

Mints the persistent map-and-rules high-score document type: versioned strict
validation, pure ranked insertion with a per-key cap, START-EMPTY tolerant
loading, and the GM-07b atomic canonical-ASCII writer. Every missing product
surface becomes a clean FAILURE (never an import/collection ERROR) through the
``require_attribute`` guards, mirroring ``test_gm07b_save_schema``.
"""

from __future__ import annotations

import copy
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

HIGHSCORES_MODULE = "highscores"
STATE_CONTRACT = "mini-metro-highscores-v1"


def _module(testcase, name=HIGHSCORES_MODULE):
    try:
        return importlib.import_module(name)
    except ModuleNotFoundError as error:  # pragma: no cover - product guard
        testcase.fail(f"GM-07d product module is missing: {name} ({error})")


def _symbol(testcase, name, module_name=HIGHSCORES_MODULE):
    value = getattr(_module(testcase, module_name), name, None)
    testcase.assertIsNotNone(
        value, f"GM-07d product symbol is missing: {module_name}.{name}"
    )
    return value


def _empty_doc() -> dict:
    return {"schemaVersion": 2, "stateContract": STATE_CONTRACT, "entries": []}


def _entry(map_id: str, rules: str, deliveries: int, version: int = 1) -> dict:
    # GM-09f2 v2 entry: keyed by the full map identity (map, mapDefinitionVersion).
    return {
        "map": map_id,
        "mapDefinitionVersion": version,
        "rulesVersion": rules,
        "deliveries": deliveries,
    }


def _valid_doc() -> dict:
    return {
        "schemaVersion": 2,
        "stateContract": STATE_CONTRACT,
        "entries": [
            _entry("classic", "rules-v1", 7),
            _entry("classic", "rules-v1", 3),
        ],
    }


def _record(
    testcase,
    document,
    deliveries,
    map="classic",
    rules_version="rules-v1",
    map_definition_version=1,
):
    record_score = _symbol(testcase, "record_score")
    return record_score(
        document,
        deliveries=deliveries,
        map=map,
        map_definition_version=map_definition_version,
        rules_version=rules_version,
    )


def _group(document, map="classic", rules="rules-v1", version=1):
    return [
        entry
        for entry in document["entries"]
        if entry["map"] == map
        and entry["rulesVersion"] == rules
        and entry["mapDefinitionVersion"] == version
    ]


def _deliveries(entries):
    return [entry["deliveries"] for entry in entries]


class TestGM07dHighscoresConstants(unittest.TestCase):
    def test_versioned_constants(self):
        module = _module(self)
        for name, expected in (
            ("HIGHSCORES_SCHEMA_VERSION", 2),
            ("HIGHSCORES_STATE_CONTRACT", STATE_CONTRACT),
            ("HIGHSCORES_PER_KEY_CAP", 10),
            ("HIGHSCORES_MAP_CLASSIC", "classic"),
        ):
            self.assertEqual(getattr(module, name, None), expected, name)


class TestGM07dValidateHighscores(unittest.TestCase):
    def test_accepts_a_valid_document(self):
        validate = _symbol(self, "validate_highscores")
        self.assertIsNone(validate(_valid_doc()))
        self.assertIsNone(validate(_empty_doc()), "an empty board is valid")

    def _assert_rejected(self, mutations):
        validate = _symbol(self, "validate_highscores")
        for name, mutate in mutations.items():
            candidate = _valid_doc()
            mutate(candidate)
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate(candidate)

    def test_header_strictness(self):
        self._assert_rejected(
            {
                # 2 is now the SUPPORTED version (GM-09f2); 3 is the forward version.
                "forward schemaVersion": lambda d: d.update(schemaVersion=3),
                "legacy v1 schemaVersion": lambda d: d.update(schemaVersion=1),
                "zero schemaVersion": lambda d: d.update(schemaVersion=0),
                "bool schemaVersion": lambda d: d.update(schemaVersion=True),
                "string schemaVersion": lambda d: d.update(schemaVersion="2"),
                "float schemaVersion": lambda d: d.update(schemaVersion=2.0),
                "null schemaVersion": lambda d: d.update(schemaVersion=None),
                "wrong stateContract": lambda d: d.update(stateContract="other"),
                "empty stateContract": lambda d: d.update(stateContract=""),
                "null stateContract": lambda d: d.update(stateContract=None),
            }
        )

    def test_top_level_key_set_is_exact(self):
        self._assert_rejected(
            {
                "unknown top-level key": lambda d: d.update(extra=1),
                "missing entries": lambda d: d.pop("entries"),
                "missing schemaVersion": lambda d: d.pop("schemaVersion"),
                "missing stateContract": lambda d: d.pop("stateContract"),
                "entries not a list": lambda d: d.update(entries={}),
                "empty object": lambda d: d.clear(),
            }
        )
        validate = _symbol(self, "validate_highscores")
        for bad in ([], "x", 3, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate(bad)

    def test_entry_key_and_type_strictness(self):
        self._assert_rejected(
            {
                "entry unknown key": lambda d: d["entries"][0].update(bonus=1),
                "entry missing map": lambda d: d["entries"][0].pop("map"),
                "entry missing mapDefinitionVersion": lambda d: d["entries"][0].pop(
                    "mapDefinitionVersion"
                ),
                "entry missing rulesVersion": lambda d: d["entries"][0].pop(
                    "rulesVersion"
                ),
                "entry missing deliveries": lambda d: d["entries"][0].pop("deliveries"),
                "entry not an object": lambda d: d["entries"].__setitem__(0, [1, 2]),
                "non-string map": lambda d: d["entries"][0].update(map=1),
                # GM-09f2 map grammar: non-empty ASCII, no whitespace (mirrors the save).
                "empty map": lambda d: d["entries"][0].update(map=""),
                "whitespace map": lambda d: d["entries"][0].update(map="a b"),
                "non-ascii map": lambda d: d["entries"][0].update(map="rivér"),
                # GM-09f2 mapDefinitionVersion: positive non-bool int (mirrors the save).
                "zero mapDefinitionVersion": lambda d: d["entries"][0].update(
                    mapDefinitionVersion=0
                ),
                "negative mapDefinitionVersion": lambda d: d["entries"][0].update(
                    mapDefinitionVersion=-1
                ),
                "bool mapDefinitionVersion": lambda d: d["entries"][0].update(
                    mapDefinitionVersion=True
                ),
                "float mapDefinitionVersion": lambda d: d["entries"][0].update(
                    mapDefinitionVersion=1.0
                ),
                "string mapDefinitionVersion": lambda d: d["entries"][0].update(
                    mapDefinitionVersion="1"
                ),
                "non-string rulesVersion": lambda d: d["entries"][0].update(
                    rulesVersion=2
                ),
                "negative deliveries": lambda d: d["entries"][0].update(deliveries=-1),
                "bool deliveries": lambda d: d["entries"][0].update(deliveries=True),
                "float deliveries": lambda d: d["entries"][0].update(deliveries=3.0),
                "string deliveries": lambda d: d["entries"][0].update(deliveries="3"),
            }
        )

    def test_duplicate_json_keys_are_rejected(self):
        # Mirrors save_load._reject_duplicate_keys: the shared object_pairs_hook
        # raises ValueError before an exact-key check ever collapses a repeat.
        reject_hook = _symbol(self, "_reject_duplicate_keys")
        with self.assertRaises(ValueError):
            json.loads(
                '{"schemaVersion":1,"schemaVersion":1}', object_pairs_hook=reject_hook
            )
        self.assertEqual(
            reject_hook([("schemaVersion", 1), ("entries", [])]),
            {"schemaVersion": 1, "entries": []},
            "distinct keys must still parse to a mapping",
        )


class TestGM07dRecordScore(unittest.TestCase):
    def test_record_result_exposes_document_rank_and_is_best(self):
        result = _record(self, _empty_doc(), 5)
        for attr in ("document", "rank", "is_best"):
            self.assertTrue(hasattr(result, attr), f"RecordResult must carry .{attr}")
        self.assertIsInstance(result.document, dict)

    def test_record_score_is_pure(self):
        document = _valid_doc()
        before = copy.deepcopy(document)
        _record(self, document, 99)
        self.assertEqual(document, before, "record_score must never mutate its input")

    def test_first_ever_entry_is_rank_one_and_best_even_at_zero(self):
        result = _record(self, _empty_doc(), 0)
        self.assertEqual(result.rank, 1)
        self.assertIs(result.is_best, True)
        self.assertEqual(_group(result.document), [_entry("classic", "rules-v1", 0)])

    def test_new_entry_equal_to_the_current_best_ranks_two_not_best(self):
        first = _record(self, _empty_doc(), 5)
        second = _record(self, first.document, 5)
        self.assertEqual(second.rank, 2, "an equal entry sorts after the earlier best")
        self.assertIs(second.is_best, False)
        self.assertEqual(_deliveries(_group(second.document)), [5, 5])

    def test_descending_ranking_for_higher_between_and_lower(self):
        doc = _record(self, _empty_doc(), 5).document
        higher = _record(self, doc, 10)
        self.assertEqual((higher.rank, higher.is_best), (1, True))
        between = _record(self, higher.document, 7)
        self.assertEqual((between.rank, between.is_best), (2, False))
        lower = _record(self, between.document, 1)
        self.assertEqual((lower.rank, lower.is_best), (4, False))
        self.assertEqual(_deliveries(_group(lower.document)), [10, 7, 5, 1])

    def test_exact_ties_are_stable_over_append_order(self):
        doc = _empty_doc()
        ranks = []
        for _ in range(3):
            result = _record(self, doc, 5)
            ranks.append(result.rank)
            doc = result.document
        self.assertEqual(ranks, [1, 2, 3], "each equal entry appends after prior ties")
        self.assertEqual(_deliveries(_group(doc)), [5, 5, 5])

    def test_entries_are_stored_in_the_pinned_canonical_order(self):
        doc = _empty_doc()
        for deliveries, map_id, rules in (
            (5, "classic", "rules-v1"),
            (9, "classic", "rules-v1"),
            (1, "beta", "rules-v1"),
            (2, "classic", "rules-v2"),
        ):
            doc = _record(
                self, doc, deliveries, map=map_id, rules_version=rules
            ).document
        self.assertEqual(
            doc["entries"],
            [
                _entry("beta", "rules-v1", 1),
                _entry("classic", "rules-v1", 9),
                _entry("classic", "rules-v1", 5),
                _entry("classic", "rules-v2", 2),
            ],
            "map asc, rulesVersion asc, deliveries desc",
        )

    def _capped_doc(self):
        doc = _empty_doc()
        for deliveries in range(1, 11):
            doc = _record(self, doc, deliveries).document
        self.assertEqual(len(_group(doc)), 10)
        return doc

    def test_eleventh_lower_entry_drops_out_beyond_the_cap(self):
        doc = self._capped_doc()
        result = _record(self, doc, 0)
        self.assertIsNone(result.rank, "an over-cap loser gets no rank")
        self.assertIs(result.is_best, False)
        self.assertEqual(_deliveries(_group(result.document)), list(range(10, 0, -1)))

    def test_eleventh_higher_entry_evicts_the_lowest(self):
        doc = self._capped_doc()
        result = _record(self, doc, 100)
        self.assertEqual((result.rank, result.is_best), (1, True))
        group = _deliveries(_group(result.document))
        self.assertEqual(len(group), 10, "the per-key cap holds at ten")
        self.assertIn(100, group)
        self.assertNotIn(1, group, "the previous lowest is evicted")

    def test_recording_under_another_key_leaves_the_first_key_intact(self):
        doc = _record(self, _empty_doc(), 9).document
        doc = _record(self, doc, 5).document
        doc = _record(self, doc, 3, map="beta").document
        before_classic = _group(doc, "classic", "rules-v1")
        result = _record(self, doc, 2, rules_version="rules-v2")
        self.assertEqual(
            _group(result.document, "classic", "rules-v1"),
            before_classic,
            "cross-key recording preserves the first key's entries and order",
        )
        self.assertEqual(
            _group(result.document, "beta", "rules-v1"),
            [_entry("beta", "rules-v1", 3)],
        )

    def test_record_score_rejects_invalid_deliveries(self):
        # A public misuse -- a negative, boolean, float, or string deliveries --
        # must fail fast rather than mint a bogus entry that later corrupts the
        # persisted board (codex MAJOR-2).
        record_score = _symbol(self, "record_score")
        for bad in (-1, True, 3.0, "3"):
            with self.assertRaises(
                ValueError, msg=f"deliveries={bad!r} must be rejected"
            ):
                record_score(
                    _empty_doc(),
                    deliveries=bad,
                    map="classic",
                    map_definition_version=1,
                    rules_version="rules-v1",
                )

    def test_record_score_requires_explicit_map_identity_and_rules_version(self):
        # map, mapDefinitionVersion, and rules identity are required, never silently
        # defaulted, so a caller can never record under the wrong key (codex MINOR-3;
        # GM-09f2 adds mapDefinitionVersion to that rule).
        record_score = _symbol(self, "record_score")
        with self.assertRaises(TypeError):
            record_score(_empty_doc(), deliveries=5)
        with self.assertRaises(TypeError):
            # map + rules given, but mapDefinitionVersion omitted -> still required.
            record_score(
                _empty_doc(), deliveries=5, map="classic", rules_version="rules-v1"
            )

    def test_record_score_rejects_invalid_map_identity(self):
        # GM-09f2 codex MINOR-1: a malformed map id or a non-positive/non-int map
        # version must fail fast here, not silently mint an entry that only breaks at
        # save. map grammar mirrors the save's mapId (non-empty ASCII, no whitespace).
        record_score = _symbol(self, "record_score")
        for bad_map in ("", "a b", "rivér", 1):
            with self.assertRaises(ValueError, msg=f"map={bad_map!r} must be rejected"):
                record_score(
                    _empty_doc(),
                    deliveries=5,
                    map=bad_map,
                    map_definition_version=1,
                    rules_version="rules-v1",
                )
        for bad_version in (0, -1, True, 1.0, "1"):
            with self.assertRaises(
                ValueError, msg=f"mapDefinitionVersion={bad_version!r} must be rejected"
            ):
                record_score(
                    _empty_doc(),
                    deliveries=5,
                    map="classic",
                    map_definition_version=bad_version,
                    rules_version="rules-v1",
                )

    def test_recording_one_key_never_drops_another_over_cap_key(self):
        # An externally authored board may hold an over-cap group that validation
        # accepts (it checks structure, not the cap); recording a DIFFERENT key
        # must never truncate that unrelated group (codex MAJOR-3).
        board = {
            "schemaVersion": 2,
            "stateContract": STATE_CONTRACT,
            "entries": [_entry("beta", "rules-v1", d) for d in range(11, 0, -1)],
        }
        _symbol(self, "validate_highscores")(board)  # the board is structurally valid
        result = _record(self, board, 5, map="classic", rules_version="rules-v1")
        self.assertEqual(
            len(_group(result.document, "beta", "rules-v1")),
            11,
            "recording classic must not drop an unrelated over-cap beta entry",
        )
        self.assertEqual((result.rank, result.is_best), (1, True))


class TestGM07dLoadHighscores(unittest.TestCase):
    def _load(self, payload: bytes | None):
        load_highscores = _symbol(self, "load_highscores")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            if payload is not None:
                target.write_bytes(payload)
            return load_highscores(target)

    def test_valid_file_returns_the_parsed_document(self):
        document = _valid_doc()
        payload = json.dumps(document).encode("ascii")
        self.assertEqual(self._load(payload), document)

    def test_start_empty_on_missing_or_corrupt_inputs(self):
        deep = ("[" * 200_000 + "]" * 200_000).encode("ascii")
        cases = {
            "missing file": None,
            "truncated json": b'{"schemaVersion":1',
            "not json": b"this is not json at all",
            "utf-8 BOM": b"\xef\xbb\xbf" + json.dumps(_valid_doc()).encode("ascii"),
            "non-ascii tolerated field": json.dumps(
                {
                    "schemaVersion": 1,
                    "stateContract": STATE_CONTRACT,
                    "entries": [_entry("cléssic", "rules-v1", 1)],
                }
            ).encode("utf-8"),
            "duplicate keys": b'{"schemaVersion":1,"schemaVersion":1,'
            b'"stateContract":"' + STATE_CONTRACT.encode("ascii") + b'","entries":[]}',
            "forward version": json.dumps(
                {"schemaVersion": 3, "stateContract": STATE_CONTRACT, "entries": []}
            ).encode("ascii"),
            # GM-09f2 (D-039): a legacy v1 board (three-field entries, no
            # mapDefinitionVersion) is NOT migrated -- its map labels are not
            # provably accurate -- so it starts empty like any other unreadable
            # format rather than synthesizing authoritative classic@1.
            "legacy v1 board": json.dumps(
                {
                    "schemaVersion": 1,
                    "stateContract": STATE_CONTRACT,
                    "entries": [
                        {"map": "classic", "rulesVersion": "rules-v1", "deliveries": 9}
                    ],
                }
            ).encode("ascii"),
            # A SUPPORTED-version (v2) board that is still malformed must START-EMPTY:
            # the loader validates, it does not trust any v2 mapping (codex MINOR).
            "malformed v2 (extra entry key)": json.dumps(
                {
                    "schemaVersion": 2,
                    "stateContract": STATE_CONTRACT,
                    "entries": [dict(_entry("classic", "rules-v1", 5), bonus=1)],
                }
            ).encode("ascii"),
            "malformed v2 (bad mapDefinitionVersion)": json.dumps(
                {
                    "schemaVersion": 2,
                    "stateContract": STATE_CONTRACT,
                    "entries": [
                        {
                            "map": "classic",
                            "mapDefinitionVersion": True,
                            "rulesVersion": "rules-v1",
                            "deliveries": 5,
                        }
                    ],
                }
            ).encode("ascii"),
            "pathologically deep nesting": deep,
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    self._load(payload),
                    _empty_doc(),
                    "a corrupt leaderboard must start empty and never raise",
                )


class _InjectedFdopenFailure(Exception):
    """Stand in for a raising os.fdopen (OOM/EMFILE) that never returns a handle."""


class TestGM07dSaveHighscores(unittest.TestCase):
    def test_save_writes_canonical_ascii_bytes(self):
        save_highscores = _symbol(self, "save_highscores")
        document = _valid_doc()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            save_highscores(document, target)
            payload = target.read_bytes()
        expected = (
            json.dumps(
                document,
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
        payload.decode("ascii")

    def test_interrupted_replace_preserves_the_prior_file_without_litter(self):
        save_highscores = _symbol(self, "save_highscores")
        created: list[str] = []
        real_mkstemp = tempfile.mkstemp

        def recording_mkstemp(*args, **kwargs):
            descriptor, name = real_mkstemp(*args, **kwargs)
            created.append(name)
            return descriptor, name

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            target.write_bytes(b"precious-bytes\n")
            with (
                mock.patch("tempfile.mkstemp", recording_mkstemp),
                mock.patch(
                    "os.replace", side_effect=OSError("injected replace failure")
                ),
            ):
                with self.assertRaises(OSError):
                    save_highscores(_valid_doc(), target)
            self.assertEqual(len(created), 1, "mkstemp ran before the injected fault")
            self.assertFalse(Path(created[0]).exists(), "no .tmp litter may remain")
            self.assertEqual(target.read_bytes(), b"precious-bytes\n")
            self.assertEqual(os.listdir(directory), ["highscores.json"])

    def test_save_rejects_and_never_persists_an_invalid_document(self):
        # save validates before writing, so a structurally invalid board (here a
        # negative deliveries) RAISES and can never overwrite a valid file with
        # bytes that would reload as empty (codex MAJOR-2).
        save_highscores = _symbol(self, "save_highscores")
        invalid = _empty_doc()
        invalid["entries"] = [_entry("classic", "rules-v1", -1)]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            target.write_bytes(b"precious-bytes\n")
            with self.assertRaises(ValueError):
                save_highscores(invalid, target)
            self.assertEqual(
                target.read_bytes(),
                b"precious-bytes\n",
                "an invalid board must never overwrite a valid file",
            )
            self.assertEqual(os.listdir(directory), ["highscores.json"], "no litter")

    def test_fdopen_failure_closes_the_descriptor_without_masking_or_litter(self):
        # Twin of the save_game seam test: when os.fdopen itself raises
        # (OOM/EMFILE) it never returns a handle, so the with block never runs to
        # close the raw descriptor. The writer must close that fd in its finally,
        # or it leaks and -- on Windows -- the still-open temporary cannot be
        # unlinked, masking the real error and leaving .tmp litter (codex MINOR).
        save_highscores = _symbol(self, "save_highscores")
        created: list[tuple[int, str]] = []
        real_mkstemp = tempfile.mkstemp

        def recording_mkstemp(*args, **kwargs):
            descriptor, name = real_mkstemp(*args, **kwargs)
            created.append((descriptor, name))
            return descriptor, name

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "highscores.json"
            target.write_bytes(b"precious-bytes\n")
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
                    save_highscores(_valid_doc(), target)
            self.assertEqual(len(created), 1, "mkstemp ran before the injected fault")
            descriptor, temporary_name = created[0]
            # The writer's finally must have closed the raw fd; a leaked (still
            # open) fd would let this second close succeed instead of raising.
            with self.assertRaises(OSError):
                os.close(descriptor)
            self.assertFalse(Path(temporary_name).exists(), "no .tmp litter may remain")
            self.assertEqual(target.read_bytes(), b"precious-bytes\n")
            self.assertEqual(os.listdir(directory), ["highscores.json"])


if __name__ == "__main__":
    unittest.main()
