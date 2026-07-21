from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.realpath(__file__)) + "/../src")

from test.test_gm06c_carriage_fault_callbacks import (
    _CallbackAppend,
    _CallbackRemove,
)
from test.test_gm06c_carriage_transactions import (
    _assert_snapshot,
    _carriage_type,
    _full_graph,
    _management,
    _mutate_full_graph,
    _snapshot,
)


def _fault(mode: str, label: str) -> BaseException | None:
    if mode == "ordinary":
        return RuntimeError(f"{label} ordinary fault")
    if mode == "base":
        return KeyboardInterrupt(f"{label} base fault")
    return None


class _IdentityExceptionCase(unittest.TestCase):
    def assert_transaction_failure(self, callback, error) -> None:
        if error is not None and not isinstance(error, Exception):
            try:
                callback()
            except BaseException as raised:
                self.assertIs(raised, error)
            else:
                self.fail(f"{type(error).__name__} was not raised")
        else:
            self.assertFalse(callback())


class TestGM06cResolverTransactionSeam(_IdentityExceptionCase):
    def test_outer_factory_resolver_mutation_return_raise_and_base_roll_back(self):
        for mode in ("return", "ordinary", "base"):
            with self.subTest(mode=mode):
                host, paths, metros, plans = _full_graph(61600 + len(mode))
                before = _snapshot(host)
                error = _fault(mode, "factory resolver")
                getter_calls = MagicMock()
                factory = MagicMock(return_value=_carriage_type()())

                def getter():
                    getter_calls()
                    _mutate_full_graph(host, paths, metros, plans)
                    if error is not None:
                        raise error
                    return factory

                reconcile = MagicMock(
                    side_effect=AssertionError("moving reconciliation ran")
                )
                self.assert_transaction_failure(
                    lambda: _management().attach(
                        host,
                        paths[0],
                        get_carriage_factory=getter,
                        reconcile_station_service=reconcile,
                    ),
                    error,
                )

                getter_calls.assert_called_once_with()
                if mode == "return":
                    factory.assert_called_once_with()
                else:
                    factory.assert_not_called()
                reconcile.assert_not_called()
                _assert_snapshot(self, host, before)


class TestGM06cListCallbackTransactionSeam(_IdentityExceptionCase):
    def test_append_and_remove_callbacks_restore_the_full_validator_footprint(self):
        for operation in ("attach", "detach"):
            for mode in ("return", "ordinary", "base"):
                with self.subTest(operation=operation, mode=mode):
                    host, paths, metros, plans = _full_graph(
                        61700 + len(operation) + len(mode)
                    )
                    selected = metros[0]
                    callback_calls = MagicMock()
                    error = _fault(mode, f"{operation} callback")

                    def mutate():
                        callback_calls()
                        _mutate_full_graph(host, paths, metros, plans)

                    wrapper_type = (
                        _CallbackAppend if operation == "attach" else _CallbackRemove
                    )
                    selected.carriages = wrapper_type(selected.carriages, mutate, error)
                    before = _snapshot(host)
                    candidate = _carriage_type()()
                    factory = MagicMock(return_value=candidate)
                    getter = MagicMock(return_value=factory)
                    reconcile = MagicMock(
                        side_effect=AssertionError("moving reconciliation ran")
                    )

                    def invoke():
                        if operation == "attach":
                            return _management().attach(
                                host,
                                paths[0],
                                get_carriage_factory=getter,
                                reconcile_station_service=reconcile,
                            )
                        return _management().detach(
                            host,
                            paths[0],
                            reconcile_station_service=reconcile,
                        )

                    self.assert_transaction_failure(invoke, error)
                    callback_calls.assert_called_once_with()
                    reconcile.assert_not_called()
                    if operation == "attach":
                        getter.assert_called_once_with()
                        factory.assert_called_once_with()
                    else:
                        getter.assert_not_called()
                        factory.assert_not_called()
                    _assert_snapshot(self, host, before)


class TestGM06cMalformedFactoryOutcomes(unittest.TestCase):
    def test_every_malformed_candidate_rejects_without_partial_attachment(self):
        Carriage = _carriage_type()
        empty_id = Carriage()
        empty_id.id = ""
        boolean_id = Carriage()
        boolean_id.id = True
        shape = Carriage().shape
        candidates = (
            ("none", None),
            ("object", object()),
            ("duck", SimpleNamespace(id="duck", capacity=6, shape=shape)),
            ("zero-capacity", SimpleNamespace(id="zero", capacity=0, shape=shape)),
            (
                "boolean-capacity",
                SimpleNamespace(id="bool", capacity=True, shape=shape),
            ),
            ("empty-id", empty_id),
            ("boolean-id", boolean_id),
        )

        for index, (name, candidate) in enumerate(candidates):
            with self.subTest(name=name):
                host, paths, _, _ = _full_graph(61800 + index)
                before = _snapshot(host)
                factory = MagicMock(return_value=candidate)
                getter = MagicMock(return_value=factory)
                reconcile = MagicMock(
                    side_effect=AssertionError("malformed candidate reconciled")
                )

                self.assertFalse(
                    _management().attach(
                        host,
                        paths[0],
                        get_carriage_factory=getter,
                        reconcile_station_service=reconcile,
                    )
                )

                getter.assert_called_once_with()
                factory.assert_called_once_with()
                reconcile.assert_not_called()
                _assert_snapshot(self, host, before)


if __name__ == "__main__":
    unittest.main()
