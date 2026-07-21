"""Thin input orchestration for transient path-handle editing."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

from path_handles import (
    PathEditSelection,
    PathHandleEdit,
    hit_test_path_handles,
)


class _ConsumedHandleEdit:
    """Marker for an ambiguous handle gesture that owns its eventual release."""

    __slots__ = ()


_CONSUMED_HANDLE_EDIT = _ConsumedHandleEdit()


class PathHandleInput:
    """Coordinate handle selection and commit without owning facade state."""

    __slots__ = ()

    @staticmethod
    def clear(host: Any) -> None:
        host.path_redraw = None
        host.path_edit_selection = None
        host.is_mouse_down = False
        for button in getattr(host, "buttons", ()):
            button.on_exit()

    @staticmethod
    def selected_path(host: Any) -> Any | None:
        selection = getattr(host, "path_edit_selection", None)
        if selection is None:
            return None
        if not isinstance(selection, PathEditSelection):
            host.path_edit_selection = None
            return None
        path = selection.resolve(getattr(host, "paths", ()))
        if path is None:
            host.path_edit_selection = None
        return path

    def begin(
        self,
        host: Any,
        position: Any,
        *,
        build_handles: Callable[..., Any],
        redraw_factory: Callable[..., Any],
        viewport_size: tuple[int, int],
    ) -> bool:
        path = self.selected_path(host)
        if path is None:
            return False
        handles = build_handles(host, path, viewport_size=viewport_size)
        hit = hit_test_path_handles(handles, position)
        host.path_edit_selection = None
        if hit.handle is None and not hit.ambiguous:
            return False
        edit: Any = _CONSUMED_HANDLE_EDIT
        if hit.handle is not None:
            edit = PathHandleEdit.begin(path, hit.handle)
            if edit is None:
                edit = _CONSUMED_HANDLE_EDIT
        for button in getattr(host, "buttons", ()):
            button.on_exit()
        host.path_redraw = redraw_factory(path, handle_edit=edit)
        return True

    @staticmethod
    def move(host: Any, redraw: Any, position: Any, station: Any | None) -> bool:
        edit = getattr(redraw, "handle_edit", None)
        if edit is None:
            return False
        if isinstance(edit, PathHandleEdit):
            try:
                moved = edit.move_to(position, station)
            except (AttributeError, IndexError, TypeError, ValueError):
                PathHandleInput.clear(host)
                return True
            host.path_redraw = replace(redraw, handle_edit=moved)
        return True

    def finish(self, host: Any, redraw: Any, station: Any | None) -> bool:
        edit = getattr(redraw, "handle_edit", None)
        if edit is None:
            return False
        result = None
        if isinstance(edit, PathHandleEdit):
            try:
                result = edit.result(host.paths, host.stations, station)
            except (AttributeError, IndexError, TypeError, ValueError):
                result = None
        self.clear(host)
        if result is None:
            return True
        path, station_indices, loop = result
        try:
            host.replace_path(path, station_indices, loop)
        finally:
            self.clear(host)
        return True

    @staticmethod
    def select_redraw_path(host: Any, redraw: Any) -> None:
        path = getattr(redraw, "path", None)
        selection = None
        try:
            candidate = PathEditSelection(path)
        except TypeError:
            candidate = None
        if (
            candidate is not None
            and candidate.resolve(getattr(host, "paths", ())) is path
        ):
            selection = candidate
        host.path_edit_selection = selection
        host.path_redraw = None
        host.is_mouse_down = False
        for button in getattr(host, "buttons", ()):
            button.on_exit()

    @staticmethod
    def is_inside_viewport(host: Any, position: Any) -> bool:
        size = getattr(host, "_layout_size", None)
        try:
            x = float(position.left)
            y = float(position.top)
        except (AttributeError, TypeError, ValueError):
            try:
                x, y = (float(value) for value in position)
            except (TypeError, ValueError):
                return size is None
        if size is None:
            return x >= 0 and y >= 0
        width, height = size
        return 0 <= x < width and 0 <= y < height
