from __future__ import annotations

from collections.abc import Callable
from typing import Any

from input_coordinator_host import InputCoordinatorHost

Resolver = Callable[[], Any]


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
        get_path_redraw_factory: Resolver | None = None,
    ) -> None:
        entity = host.get_containing_entity(event.position)
        event_type = get_mouse_event_type()
        redraw = getattr(host, "path_redraw", None)
        creating = bool(getattr(host, "is_creating_path", False))
        creation_path = getattr(host, "path_being_created", None)
        redraw_type = (
            get_path_redraw_factory()
            if redraw is not None and get_path_redraw_factory is not None
            else None
        )
        if (
            redraw is not None
            and redraw_type is not None
            and not isinstance(redraw, redraw_type)
        ):
            self._clear_redraw(host)
            redraw = None
            if not creating and creation_path is None:
                if event.event_type == event_type.MOUSE_DOWN:
                    host.is_mouse_down = True
                elif event.event_type == event_type.MOUSE_UP:
                    host.is_mouse_down = False
                if (
                    not host.is_mouse_down
                    and entity
                    and isinstance(entity, get_button_type())
                ):
                    entity.on_hover()
                return

        if event.event_type == event_type.MOUSE_DOWN:
            was_mouse_down = bool(host.is_mouse_down)
            host.is_mouse_down = True
            if creating or creation_path is not None:
                if redraw is not None:
                    self._clear_redraw(host)
                return
            if was_mouse_down or redraw is not None:
                return
            if entity and isinstance(entity, get_station_type()):
                host.start_path_on_station(entity)
            elif entity and isinstance(entity, get_path_button_type()):
                path = getattr(entity, "path", None)
                if (
                    path is not None
                    and not bool(getattr(entity, "is_locked", False))
                    and get_path_redraw_factory is not None
                ):
                    self._clear_redraw(host)
                    host.path_redraw = get_path_redraw_factory()(path)

        elif event.event_type == event_type.MOUSE_UP:
            host.is_mouse_down = False
            if creating:
                if redraw is not None:
                    self._clear_redraw(host)
                if creation_path is None:
                    return
                if entity and isinstance(entity, get_station_type()):
                    host.end_path_on_station(entity)
                else:
                    host.abort_path_creation()
            elif creation_path is not None:
                if redraw is not None:
                    self._clear_redraw(host)
            elif redraw is None or not redraw.stations:
                if redraw is not None:
                    self._clear_redraw(host)
                self._apply_release_target(
                    host, entity, get_path_button_type(), get_speed_button_type()
                )
                if entity and isinstance(entity, get_button_type()):
                    entity.on_hover()
            else:
                station_type = get_station_type()
                if entity and isinstance(entity, station_type):
                    redraw = redraw.enter_station(entity, event.position)
                self._clear_redraw(host)
                indices = redraw.station_indices(host.stations)
                if entity and isinstance(entity, station_type) and redraw.is_valid:
                    if indices is not None:
                        try:
                            host.replace_path(redraw.path, indices, redraw.loop)
                        finally:
                            self._clear_redraw(host)
                elif entity and isinstance(entity, get_button_type()):
                    entity.on_hover()

        elif event.event_type == event_type.MOUSE_MOTION:
            if host.is_mouse_down:
                if creating or creation_path is not None:
                    if redraw is not None:
                        self._clear_redraw(host)
                    if creating and creation_path:
                        if entity and isinstance(entity, get_station_type()):
                            host.add_station_to_path(entity)
                        else:
                            creation_path.set_temporary_point(event.position)
                    return
                if redraw is not None:
                    host.path_redraw = (
                        redraw.enter_station(entity, event.position)
                        if entity and isinstance(entity, get_station_type())
                        else redraw.move_to(event.position)
                    )
            else:
                if redraw is not None:
                    self._clear_redraw(host)
                if entity and isinstance(entity, get_button_type()):
                    entity.on_hover()
                else:
                    for button in host.buttons:
                        button.on_exit()

    @staticmethod
    def _clear_redraw(host: InputCoordinatorHost) -> None:
        host.path_redraw = None
        for button in host.buttons:
            button.on_exit()

    @staticmethod
    def _apply_release_target(host, entity, path_type, speed_type) -> None:
        if entity and isinstance(entity, path_type):
            if entity.path:
                host.remove_path(entity.path)
            elif entity.is_locked:
                host.try_purchase_path_button(entity)
        elif entity and isinstance(entity, speed_type):
            host.apply_speed_action(entity.action)

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
