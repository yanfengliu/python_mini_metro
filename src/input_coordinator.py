from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

Resolver = Callable[[], Any]


class InputCoordinatorHost(Protocol):
    """Mutable facade surface used only for one input or layout transition."""

    _progression: Any
    path_buttons: list[Any]
    speed_buttons: list[Any]
    buttons: list[Any]
    stations: list[Any]
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


class InputCoordinator:
    """Stateless player-input and layout algorithms over canonical facade state."""

    __slots__ = ()

    def prepare_layout(
        self,
        host: InputCoordinatorHost,
        width: int,
        height: int,
        *,
        get_update_path_button_positions: Resolver,
        get_update_speed_button_positions: Resolver,
        get_game_over_font_size: Resolver,
        get_rect_factory: Resolver,
        get_game_over_button_width: Resolver,
        get_game_over_button_height: Resolver,
        get_game_over_button_spacing: Resolver,
    ) -> None:
        get_update_path_button_positions()(host.path_buttons, width, height)
        get_update_speed_button_positions()(host.speed_buttons, width, height)
        start_top = height // 2 + get_game_over_font_size() // 3 + 40
        restart_rect = get_rect_factory()(
            0,
            0,
            get_game_over_button_width(),
            get_game_over_button_height(),
        )
        restart_rect.centerx = width // 2
        restart_rect.top = start_top
        exit_rect = restart_rect.copy()
        exit_rect.top = restart_rect.bottom + get_game_over_button_spacing()
        host.game_over_restart_rect = restart_rect
        host.game_over_exit_rect = exit_rect
        host._layout_size = (width, height)

    def update_unlocked_num_paths(self, host: InputCoordinatorHost) -> None:
        (
            previous_unlocked_num_paths,
            host.unlocked_num_paths,
        ) = host._progression.set_unlocked_num_paths(host.get_unlocked_num_paths())
        if host.unlocked_num_paths > previous_unlocked_num_paths:
            for path_button_idx in range(
                previous_unlocked_num_paths, host.unlocked_num_paths
            ):
                host.path_buttons[path_button_idx].start_unlock_blink(host.time_ms)
        host.update_path_button_lock_states()

    def update_path_button_lock_states(self, host: InputCoordinatorHost) -> None:
        for idx, button in enumerate(host.path_buttons):
            button.set_locked(idx >= host.unlocked_num_paths)

    def can_purchase_path_button_idx(
        self, host: InputCoordinatorHost, button_idx: int
    ) -> bool:
        next_button_idx = host.get_next_path_button_idx_to_purchase()
        if next_button_idx is None or next_button_idx != button_idx:
            return False
        return host._progression.can_purchase_resolved_path_button_idx(
            button_idx,
            next_button_idx=next_button_idx,
            price=host.get_purchase_price_for_path_button_idx(button_idx),
        )

    def try_purchase_path_button(self, host: InputCoordinatorHost, button: Any) -> bool:
        if not button.is_locked:
            return False
        try:
            button_idx = host.path_buttons.index(button)
        except ValueError:
            return False
        if not host.can_purchase_path_button_idx(button_idx):
            return False
        price = host.get_purchase_price_for_path_button_idx(button_idx)
        if price is None:
            return False
        host._progression.record_path_purchase(price)
        host.update_unlocked_num_paths()
        return True

    def try_purchase_path_button_by_index(
        self, host: InputCoordinatorHost, button_idx: int | None = None
    ) -> bool:
        if button_idx is None:
            button_idx = host.get_next_path_button_idx_to_purchase()
        if button_idx is None:
            return False
        if button_idx < 0 or button_idx >= len(host.path_buttons):
            return False
        return host.try_purchase_path_button(host.path_buttons[button_idx])

    def step_time(self, host: InputCoordinatorHost, dt_ms: int) -> None:
        host.increment_time(dt_ms)

    def get_surface_size(
        self,
        host: InputCoordinatorHost,
        screen: Any,
        *,
        get_screen_width: Resolver,
        get_screen_height: Resolver,
    ) -> tuple[int, int]:
        width = get_screen_width()
        height = get_screen_height()
        maybe_width = screen.get_width()
        maybe_height = screen.get_height()
        if isinstance(maybe_width, (int, float)):
            width = int(maybe_width)
        if isinstance(maybe_height, (int, float)):
            height = int(maybe_height)
        return (width, height)

    def render(
        self,
        host: InputCoordinatorHost,
        screen: Any,
        renderer: object | None = None,
        alpha: float = 1.0,
        *,
        get_renderer_factory: Resolver,
    ) -> None:
        size = host.get_surface_size(screen)
        if host._layout_size != size:
            host.prepare_layout(*size)
        if renderer is None and host._compat_renderer is None:
            host._compat_renderer = get_renderer_factory()()
        if renderer is None:
            renderer = host._compat_renderer
        assert renderer is not None
        draw = getattr(renderer, "draw")
        draw(screen, host, alpha=alpha)

    def handle_game_over_click(
        self, host: InputCoordinatorHost, position: Any
    ) -> str | None:
        if not host.is_game_over:
            return None
        if host.game_over_restart_rect and host.game_over_restart_rect.collidepoint(
            position.to_tuple()
        ):
            return "restart"
        if host.game_over_exit_rect and host.game_over_exit_rect.collidepoint(
            position.to_tuple()
        ):
            return "exit"
        return None

    def react_mouse_event(
        self,
        host: InputCoordinatorHost,
        event: Any,
        *,
        get_mouse_event_type: Resolver,
        get_station_type: Resolver,
        get_path_button_type: Resolver,
        get_speed_button_type: Resolver,
        get_button_type: Resolver,
    ) -> None:
        entity = host.get_containing_entity(event.position)

        if event.event_type == get_mouse_event_type().MOUSE_DOWN:
            host.is_mouse_down = True
            if entity:
                if isinstance(entity, get_station_type()):
                    host.start_path_on_station(entity)

        elif event.event_type == get_mouse_event_type().MOUSE_UP:
            host.is_mouse_down = False
            if host.is_creating_path:
                assert host.path_being_created is not None
                if entity and isinstance(entity, get_station_type()):
                    host.end_path_on_station(entity)
                else:
                    host.abort_path_creation()
            else:
                if entity and isinstance(entity, get_path_button_type()):
                    if entity.path:
                        host.remove_path(entity.path)
                    elif entity.is_locked:
                        host.try_purchase_path_button(entity)
                elif entity and isinstance(entity, get_speed_button_type()):
                    host.apply_speed_action(entity.action)

        elif event.event_type == get_mouse_event_type().MOUSE_MOTION:
            if host.is_mouse_down:
                if host.is_creating_path and host.path_being_created:
                    if entity and isinstance(entity, get_station_type()):
                        host.add_station_to_path(entity)
                    else:
                        host.path_being_created.set_temporary_point(event.position)
            else:
                if entity and isinstance(entity, get_button_type()):
                    entity.on_hover()
                else:
                    for button in host.buttons:
                        button.on_exit()

    def react_keyboard_event(
        self,
        host: InputCoordinatorHost,
        event: Any,
        *,
        get_keyboard_event_type: Resolver,
        get_pause_key: Resolver,
        get_speed_1_key: Resolver,
        get_speed_2_key: Resolver,
        get_speed_4_key: Resolver,
    ) -> None:
        if event.event_type == get_keyboard_event_type().KEY_UP:
            if event.key == get_pause_key():
                host.is_paused = not host.is_paused
            elif event.key == get_speed_1_key():
                host.set_game_speed(1)
            elif event.key == get_speed_2_key():
                host.set_game_speed(2)
            elif event.key == get_speed_4_key():
                host.set_game_speed(4)

    def react(
        self,
        host: InputCoordinatorHost,
        event: Any,
        *,
        get_mouse_event_class: Resolver,
        get_keyboard_event_class: Resolver,
    ) -> None:
        if isinstance(event, get_mouse_event_class()):
            host.react_mouse_event(event)
        elif isinstance(event, get_keyboard_event_class()):
            host.react_keyboard_event(event)

    def get_containing_entity(
        self, host: InputCoordinatorHost, position: Any
    ) -> Any | None:
        for station in host.stations:
            if station.contains(position):
                return station
        for button in host.buttons:
            if button.contains(position):
                return button
        return None

    def set_paused(self, host: InputCoordinatorHost, paused: bool) -> None:
        host.is_paused = paused

    def set_game_speed(self, host: InputCoordinatorHost, speed_multiplier: int) -> None:
        host.game_speed_multiplier = speed_multiplier

    def apply_speed_action(self, host: InputCoordinatorHost, action: Any) -> None:
        if action == "pause":
            host.set_paused(True)
            return
        if action == "speed_1":
            host.set_game_speed(1)
        elif action == "speed_2":
            host.set_game_speed(2)
        elif action == "speed_4":
            host.set_game_speed(4)
        host.set_paused(False)

    def is_speed_button_active(self, host: InputCoordinatorHost, action: Any) -> bool:
        if action == "pause":
            return host.is_paused
        if host.is_paused:
            return False
        if action == "speed_1":
            return host.game_speed_multiplier == 1
        if action == "speed_2":
            return host.game_speed_multiplier == 2
        if action == "speed_4":
            return host.game_speed_multiplier == 4
        return False

    def apply_action(self, host: InputCoordinatorHost, action: object) -> bool:
        if host.is_game_over:
            return False
        if not isinstance(action, dict):
            return False
        action_type = action.get("type")
        if not isinstance(action_type, str):
            return False
        if action_type == "create_path":
            stations = action.get("stations", [])
            loop = action.get("loop", False)
            if type(loop) is not bool:
                return False
            return host.create_path_from_station_indices(stations, loop) is not None
        if action_type == "buy_line":
            button_idx = action.get("path_index")
            if button_idx is not None and type(button_idx) is not int:
                return False
            return host.try_purchase_path_button_by_index(button_idx)
        if action_type == "remove_path":
            if "path_id" in action:
                return host.remove_path_by_id(action["path_id"])
            if "path_index" in action:
                return host.remove_path_by_index(action["path_index"])
            return False
        if action_type == "replace_path":
            has_path_id = "path_id" in action
            has_path_index = "path_index" in action
            if has_path_id == has_path_index:
                return False

            stations = action.get("stations")
            if (
                type(stations) is not list
                or len(stations) < 2
                or any(
                    type(station_index) is not int
                    or station_index < 0
                    or station_index >= len(host.stations)
                    for station_index in stations
                )
            ):
                return False

            loop = action.get("loop", False)
            if type(loop) is not bool:
                return False

            if has_path_id:
                path_id = action["path_id"]
                if type(path_id) is not str or not path_id:
                    return False
                return host.replace_path_by_id(path_id, stations, loop)

            path_index = action["path_index"]
            if type(path_index) is not int:
                return False
            return host.replace_path_by_index(path_index, stations, loop)
        if action_type == "pause":
            host.set_paused(True)
            return True
        if action_type == "resume":
            host.set_paused(False)
            return True
        if action_type == "noop":
            return True
        return False
