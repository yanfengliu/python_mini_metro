"""Dependency-light validation and dispatch for fleet player inputs."""

from __future__ import annotations

from typing import Any

from ui.carriage_button import CarriageButton
from ui.fleet_button import FleetButton

_ACTIONS = {
    "assign_locomotive": "assign_locomotive",
    "unassign_locomotive": "queue_locomotive_unassignment",
    "attach_carriage": "attach_carriage",
    "detach_carriage": "detach_carriage",
}


def _selected_path(host: Any, action: dict[str, Any]) -> Any | None:
    has_id = "path_id" in action
    has_index = "path_index" in action
    if has_id == has_index:
        return None
    paths = getattr(host, "paths", None)
    if not isinstance(paths, list):
        return None
    if has_index:
        index = action["path_index"]
        if type(index) is not int or index < 0 or index >= len(paths):
            return None
        path = paths[index]
        return path if sum(candidate is path for candidate in paths) == 1 else None
    path_id = action["path_id"]
    if type(path_id) is not str or not path_id:
        return None
    matches = tuple(path for path in paths if getattr(path, "id", None) == path_id)
    return matches[0] if len(matches) == 1 else None


class FleetInput:
    """Stateless fleet selector and mouse-release behavior."""

    __slots__ = ()

    def apply_action(
        self,
        host: Any,
        action: dict[str, Any],
        action_type: str,
    ) -> bool | None:
        method_name = _ACTIONS.get(action_type)
        if method_name is None:
            return None
        path = _selected_path(host, action)
        method = getattr(host, method_name, None)
        if path is None or not callable(method):
            return False
        return bool(method(path))

    def release(self, host: Any, entity: Any) -> bool:
        if isinstance(entity, FleetButton):
            controls = getattr(host, "fleet_buttons", ())
            action_type = (
                "assign_locomotive"
                if entity.operation == "assign"
                else "unassign_locomotive"
            )
        elif isinstance(entity, CarriageButton):
            controls = getattr(host, "carriage_buttons", ())
            action_type = (
                "attach_carriage" if entity.operation == "attach" else "detach_carriage"
            )
        else:
            return False
        try:
            path_buttons = getattr(host, "path_buttons", ())
            if (
                sum(button is entity for button in controls) != 1
                or sum(button is entity.path_button for button in path_buttons) != 1
                or entity.path_button.is_locked
            ):
                return True
            path = entity.path_button.path
            paths = getattr(host, "paths", ())
            if path is None or sum(candidate is path for candidate in paths) != 1:
                return True
            method_name = _ACTIONS[action_type]
            getattr(host, method_name)(path)
            return True
        finally:
            host.is_mouse_down = False
            host.path_redraw = None
            host.path_edit_selection = None
            for button in host.buttons:
                button.on_exit()
