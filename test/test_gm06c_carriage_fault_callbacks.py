from __future__ import annotations

import os
import sys
import unittest
from copy import copy
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from entity.passenger import Passenger
from geometry.point import Point
from test.test_gm06c_carriage_transactions import (
    _assert_snapshot,
    _carriage_type,
    _full_graph,
    _management,
    _snapshot,
)


class _CallbackAppend(list):
    def __init__(self, values, callback, error=None) -> None:
        super().__init__(values)
        self.callback, self.error = callback, error

    def append(self, value) -> None:
        super().append(value)
        self.callback()
        if self.error is not None:
            raise self.error


class _CallbackRemove(list):
    def __init__(self, values, callback, error=None) -> None:
        super().__init__(values)
        self.callback, self.error, self.armed = callback, error, True

    def _after(self) -> None:
        if not self.armed:
            return
        self.armed = False
        self.callback()
        if self.error is not None:
            raise self.error

    def pop(self, index=-1):
        value = super().pop(index)
        self._after()
        return value

    def remove(self, value) -> None:
        index = next(
            index for index, candidate in enumerate(self) if candidate is value
        )
        self.pop(index)

    def __delitem__(self, key) -> None:
        super().__delitem__(key)
        self._after()

    def __setitem__(self, key, value) -> None:
        super().__setitem__(key, value)
        if isinstance(key, slice) and len(self) == 0:
            self._after()


class TestGM06cCarriageFaultCallbacks(unittest.TestCase):
    def _invoke(self, callback, error) -> None:
        if isinstance(error, BaseException) and not isinstance(error, Exception):
            try:
                callback()
            except BaseException as raised:
                self.assertIs(raised, error)
            else:
                self.fail(f"{type(error).__name__} was not raised")
        else:
            self.assertFalse(callback())

    def test_append_remove_and_factory_callbacks_execute_and_rollback(self) -> None:
        for operation in ("attach", "detach"):
            for error in (None, RuntimeError("list fault"), KeyboardInterrupt()):
                with self.subTest(
                    operation=operation,
                    error=None if error is None else type(error).__name__,
                ):
                    host, paths, metros, _ = _full_graph(61200 + len(operation))
                    metro = metros[0]
                    known = _carriage_type()()
                    callback = MagicMock()
                    if operation == "attach":
                        metro.carriages = _CallbackAppend([], callback, error)
                    else:
                        metro.carriages = _CallbackRemove([known], callback, error)
                    before = _snapshot(host)
                    factory = MagicMock(return_value=known)
                    getter = MagicMock(return_value=factory)

                    def invoke():
                        if operation == "attach":
                            return _management().attach(
                                host,
                                paths[0],
                                get_carriage_factory=getter,
                                reconcile_station_service=MagicMock(),
                            )
                        return _management().detach(
                            host,
                            paths[0],
                            reconcile_station_service=MagicMock(),
                        )

                    if error is None:
                        self.assertTrue(invoke())
                    else:
                        self._invoke(invoke, error)
                        _assert_snapshot(self, host, before)
                    callback.assert_called_once_with()
                    if operation == "attach":
                        getter.assert_called_once_with()
                        factory.assert_called_once_with()

    def test_factory_identity_and_readonly_id_collisions_restore_fingerprint(
        self,
    ) -> None:
        host, paths, metros, _ = _full_graph(61300)
        existing = _carriage_type()()
        metros[0].carriages.append(existing)
        duplicate_id = copy(existing)
        self.assertIsNot(duplicate_id, existing)
        self.assertEqual(duplicate_id.id, existing.id)
        for candidate in (existing, duplicate_id):
            with self.subTest(identity=candidate is existing):
                before = _snapshot(host)
                factory = MagicMock(return_value=candidate)
                getter = MagicMock(return_value=factory)
                self.assertFalse(
                    _management().attach(
                        host,
                        paths[1],
                        get_carriage_factory=getter,
                        reconcile_station_service=MagicMock(),
                    )
                )
                getter.assert_called_once_with()
                factory.assert_called_once_with()
                _assert_snapshot(self, host, before)


class TestGM06cRejectionFingerprints(unittest.TestCase):
    def test_corrupt_geometry_ownership_composition_and_capacity_reject_exactly(
        self,
    ) -> None:
        def cases(host, paths, metros):
            Carriage = _carriage_type()
            return (
                (
                    "geometry-alias",
                    lambda: setattr(
                        paths[0], "padding_segments", paths[0].path_segments
                    ),
                ),
                (
                    "line-endpoint",
                    lambda: setattr(
                        paths[0].path_segments[0].line, "end", Point(-5, -7)
                    ),
                ),
                ("ownership", lambda: host.metros.append(metros[0])),
                (
                    "shared-empty-lists",
                    lambda: setattr(metros[0], "carriages", metros[1].carriages),
                ),
                (
                    "shared-identity",
                    lambda: (
                        metros[0].carriages.append(item := Carriage()),
                        metros[1].carriages.append(item),
                    ),
                ),
                (
                    "duplicate-id",
                    lambda: (
                        metros[0].carriages.append(item := Carriage()),
                        metros[1].carriages.append(copy(item)),
                    ),
                ),
                ("negative-base", lambda: setattr(metros[0], "_base_capacity", -1)),
                ("boolean-base", lambda: setattr(metros[0], "_base_capacity", True)),
                (
                    "overfilled",
                    lambda: (
                        items := [
                            Passenger(paths[0].stations[0].shape) for _ in range(19)
                        ],
                        metros[0].passengers.extend(items),
                        host.passengers.extend(items),
                    ),
                ),
                ("path-id", lambda: setattr(paths[1], "id", paths[0].id)),
            )

        for index in range(10):
            host, paths, metros, _ = _full_graph(61400 + index)
            name, corrupt = cases(host, paths, metros)[index]
            with self.subTest(name=name):
                corrupt()
                before = _snapshot(host)
                getter = MagicMock(side_effect=AssertionError("factory resolved"))
                reconcile = MagicMock(side_effect=AssertionError("reconciled"))
                self.assertFalse(
                    _management().attach(
                        host,
                        paths[0],
                        get_carriage_factory=getter,
                        reconcile_station_service=reconcile,
                    )
                )
                _assert_snapshot(self, host, before)
                self.assertFalse(
                    _management().detach(
                        host, paths[0], reconcile_station_service=reconcile
                    )
                )
                getter.assert_not_called()
                reconcile.assert_not_called()
                _assert_snapshot(self, host, before)


if __name__ == "__main__":
    unittest.main()
