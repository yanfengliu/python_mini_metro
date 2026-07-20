from types import SimpleNamespace


class RecordingProgression:
    def __init__(self, name, events, *, unlocked=1, price=5):
        self.name = name
        self.events = events
        self.unlocked_num_paths = unlocked
        self.price = price
        self.purchases = []

    def set_unlocked_num_paths(self, value):
        self.events.append(("set-unlocked", self.name, value))
        return self.unlocked_num_paths, value

    def can_purchase_resolved_path_button_idx(
        self, button_idx, *, next_button_idx, price
    ):
        self.events.append(
            ("can-purchase", self.name, button_idx, next_button_idx, price)
        )
        return next_button_idx == button_idx and price == self.price

    def record_path_purchase(self, price):
        self.events.append(("purchase", self.name, price))
        self.purchases.append(price)


class RecordingButton:
    def __init__(self, name, events, *, locked=False, path=None, action=None):
        self.name = name
        self.events = events
        self.is_locked = locked
        self.path = path
        self.action = action

    def set_locked(self, locked):
        self.events.append(("locked", self.name, locked))
        self.is_locked = locked

    def start_unlock_blink(self, time_ms):
        self.events.append(("blink", self.name, time_ms))

    def contains(self, position):
        self.events.append(("contains", self.name, position))
        return False

    def on_hover(self):
        self.events.append(("hover", self.name))

    def on_exit(self):
        self.events.append(("exit", self.name))


class RecordingRect:
    def __init__(self, width, height, events):
        self.width = width
        self.height = height
        self.events = events
        self._centerx = 0
        self._top = 0

    @property
    def centerx(self):
        return self._centerx

    @centerx.setter
    def centerx(self, value):
        self.events.append(("centerx", value))
        self._centerx = value

    @property
    def top(self):
        return self._top

    @top.setter
    def top(self, value):
        self.events.append(("top", value))
        self._top = value

    @property
    def bottom(self):
        return self._top + self.height

    def copy(self):
        self.events.append("copy")
        copied = RecordingRect(self.width, self.height, self.events)
        copied._centerx = self._centerx
        copied._top = self._top
        return copied

    def collidepoint(self, point):
        self.events.append(("collide", point))
        x, y = point
        return (
            self.centerx - self.width // 2
            <= x
            < self.centerx - self.width // 2 + self.width
            and self.top <= y < self.bottom
        )


class RecordingRenderer:
    def __init__(self, events):
        self.events = events

    def draw(self, screen, host, *, alpha):
        self.events.append(("draw", screen, host, alpha))


class Point:
    def __init__(self, value, events):
        self.value = value
        self.events = events

    def to_tuple(self):
        self.events.append(("point", self.value))
        return self.value


class Host:
    def __init__(self, events):
        self.events = events
        self._progression = RecordingProgression("default", events)
        self.path_buttons = []
        self.speed_buttons = []
        self.buttons = []
        self.stations = []
        self.game_over_restart_rect = None
        self.game_over_exit_rect = None
        self._layout_size = None
        self._compat_renderer = None
        self.time_ms = 0
        self.is_game_over = False
        self.is_mouse_down = False
        self.is_creating_path = False
        self.path_being_created = None
        self.is_paused = False
        self.game_speed_multiplier = 1

    @property
    def unlocked_num_paths(self):
        return self._progression.unlocked_num_paths

    @unlocked_num_paths.setter
    def unlocked_num_paths(self, value):
        self._progression.unlocked_num_paths = value

    def get_unlocked_num_paths(self):
        return self._progression.unlocked_num_paths

    def update_path_button_lock_states(self):
        self.events.append("update-locks")

    def get_next_path_button_idx_to_purchase(self):
        return self.unlocked_num_paths

    def get_purchase_price_for_path_button_idx(self, _button_idx):
        return self._progression.price

    def can_purchase_path_button_idx(self, button_idx):
        next_button_idx = self.get_next_path_button_idx_to_purchase()
        if next_button_idx is None or next_button_idx != button_idx:
            return False
        return self._progression.can_purchase_resolved_path_button_idx(
            button_idx,
            next_button_idx=next_button_idx,
            price=self.get_purchase_price_for_path_button_idx(button_idx),
        )

    def update_unlocked_num_paths(self):
        self.events.append("update-unlocked")

    def try_purchase_path_button(self, button):
        self.events.append(("try-button", button))
        return True

    def try_purchase_path_button_by_index(self, button_idx=None):
        self.events.append(("try-index", button_idx))
        return True

    def increment_time(self, dt_ms):
        self.events.append(("time", dt_ms))

    def get_surface_size(self, screen):
        return screen.get_width(), screen.get_height()

    def prepare_layout(self, width, height):
        self.events.append(("prepare", width, height))
        self._layout_size = (width, height)

    def get_containing_entity(self, _position):
        return None

    def start_path_on_station(self, station):
        self.events.append(("start", station))

    def end_path_on_station(self, station):
        self.events.append(("end", station))

    def abort_path_creation(self):
        self.events.append("abort")

    def remove_path(self, path):
        self.events.append(("remove", path))

    def apply_speed_action(self, action):
        self.events.append(("speed-action", action))

    def set_paused(self, paused):
        self.events.append(("paused", paused))
        self.is_paused = paused

    def set_game_speed(self, speed):
        self.events.append(("speed", speed))
        self.game_speed_multiplier = speed

    def create_path_from_station_indices(self, stations, loop=False):
        self.events.append(("create", stations, loop))
        return object()

    def remove_path_by_id(self, path_id):
        self.events.append(("remove-id", path_id))
        return True

    def remove_path_by_index(self, path_index):
        self.events.append(("remove-index", path_index))
        return True


def event(event_type, position=None, key=None):
    return SimpleNamespace(event_type=event_type, position=position, key=key)
