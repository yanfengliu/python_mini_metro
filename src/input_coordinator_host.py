"""Structural facade contract for stateless input coordination."""

from typing import Any, Protocol


class InputCoordinatorHost(Protocol):
    """Mutable facade surface used only for one input or layout transition."""

    _progression: Any
    path_buttons: list[Any]
    speed_buttons: list[Any]
    buttons: list[Any]
    stations: list[Any]
    paths: list[Any]
    game_over_restart_rect: Any | None
    game_over_exit_rect: Any | None
    _layout_size: tuple[int, int] | None
    _compat_renderer: Any | None
    time_ms: int
    unlocked_num_paths: int
    is_game_over: bool
    is_mouse_down: bool
    is_creating_path: bool
    path_being_created: Any | None
    path_redraw: Any | None
    path_edit_selection: Any | None
    is_paused: bool
    game_speed_multiplier: int

    def get_unlocked_num_paths(self) -> int: ...

    def update_path_button_lock_states(self) -> None: ...

    def get_next_path_button_idx_to_purchase(self) -> int | None: ...

    def get_purchase_price_for_path_button_idx(self, button_idx: int) -> int | None: ...

    def can_purchase_path_button_idx(self, button_idx: int) -> bool: ...

    def update_unlocked_num_paths(self) -> None: ...

    def try_purchase_path_button(self, button: Any) -> bool: ...

    def try_purchase_path_button_by_index(
        self, button_idx: int | None = None
    ) -> bool: ...

    def replace_path_by_id(
        self, path_id: str, station_indices: list[int], loop: bool = False
    ) -> bool: ...

    def replace_path_by_index(
        self, path_index: int, station_indices: list[int], loop: bool = False
    ) -> bool: ...

    def replace_path(
        self, path: Any, station_indices: list[int], loop: bool = False
    ) -> bool: ...

    def increment_time(self, dt_ms: int) -> None: ...

    def get_surface_size(self, screen: Any) -> tuple[int, int]: ...

    def prepare_layout(self, width: int, height: int) -> None: ...

    def get_containing_entity(self, position: Any) -> Any | None: ...

    def start_path_on_station(self, station: Any) -> None: ...

    def add_station_to_path(self, station: Any) -> None: ...

    def end_path_on_station(self, station: Any) -> None: ...

    def abort_path_creation(self) -> None: ...

    def remove_path(self, path: Any) -> None: ...

    def apply_speed_action(self, action: Any) -> None: ...

    def set_paused(self, paused: bool) -> None: ...

    def set_game_speed(self, speed_multiplier: int) -> None: ...

    def create_path_from_station_indices(
        self, station_indices: list[int], loop: bool = False
    ) -> Any | None: ...

    def remove_path_by_id(self, path_id: str) -> bool: ...

    def remove_path_by_index(self, path_index: int) -> bool: ...

    def react_mouse_event(self, event: Any) -> None: ...

    def react_keyboard_event(self, event: Any) -> None: ...
