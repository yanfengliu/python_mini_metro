"""Versioned, dependency-free contract for player-equivalent RL tasks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Any

CANONICAL_WIDTH = 1920
CANONICAL_HEIGHT = 1080
CANONICAL_VIEWPORT = (CANONICAL_WIDTH, CANONICAL_HEIGHT)
INITIAL_CURSOR_POSITION = (CANONICAL_WIDTH // 2, CANONICAL_HEIGHT // 2)

PROTOCOL_ID = "python-mini-metro-player-pixels"
PROTOCOL_VERSION = 1
DEFAULT_FIXED_TICKS = 6
DEFAULT_MAX_EPISODE_STEPS = 36_000

CURSOR_POLYGON_OFFSETS = (
    (0, 0),
    (2, 32),
    (10, 24),
    (17, 40),
    (24, 36),
    (16, 21),
    (30, 20),
)
CURSOR_FILL_COLOR = (250, 250, 250)
CURSOR_OUTLINE_COLOR = (20, 20, 20)
CURSOR_OUTLINE_WIDTH = 3
CURSOR_PRESSED_MARKER_OFFSET = (4, 4)
CURSOR_PRESSED_MARKER_COLOR = (220, 60, 60)
CURSOR_PRESSED_MARKER_RADIUS = 7
CURSOR_PRESSED_MARKER_WIDTH = 3


class ActionKind(IntEnum):
    """Stable player-event values; add new members only at the end."""

    NOOP = 0
    MOTION = 1
    DOWN = 2
    UP = 3
    SPACE = 4
    KEY_1 = 5
    KEY_2 = 6
    KEY_3 = 7


ACTION_LABELS = ("noop", "motion", "down", "up", "space", "1", "2", "3")


class RewardMode(str, Enum):
    """Supported base rewards, named so experiments remain comparable."""

    DELIVERIES = "deliveries"
    DISPLAY_SCORE_DELTA = "display_score_delta"


@dataclass(frozen=True, slots=True)
class RenderProfile:
    """One immutable pixel-observation size."""

    name: str
    width: int
    height: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("render profile name must be a string")
        if not self.name:
            raise ValueError("render profile name cannot be empty")
        for field_name, value in (("width", self.width), ("height", self.height)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"render profile {field_name} must be an integer")
            if value < 2:
                raise ValueError(f"render profile {field_name} must be at least 2")

    @property
    def observation_shape(self) -> tuple[int, int, int]:
        """Return channel-first RGB dimensions."""

        return (3, self.height, self.width)

    def descriptor(self) -> dict[str, Any]:
        return {"name": self.name, "width": self.width, "height": self.height}


FAST_RENDER_PROFILE = RenderProfile("fast", 192, 108)
FIDELITY_RENDER_PROFILE = RenderProfile("fidelity", 320, 180)
RENDER_PROFILES = (FAST_RENDER_PROFILE, FIDELITY_RENDER_PROFILE)
_PROFILE_BY_NAME = {profile.name: profile for profile in RENDER_PROFILES}


def resolve_render_profile(value: RenderProfile | str) -> RenderProfile:
    """Resolve only registered profiles so tasks remain spawn/replay compatible."""

    if isinstance(value, RenderProfile):
        registered = _PROFILE_BY_NAME.get(value.name)
        if registered == value:
            return registered
        raise ValueError("render_profile must be a registered RenderProfile")
    if not isinstance(value, str):
        raise TypeError("render_profile must be a RenderProfile or string")
    try:
        return _PROFILE_BY_NAME[value]
    except KeyError as error:
        choices = ", ".join(sorted(_PROFILE_BY_NAME))
        raise ValueError(f"render_profile must be one of: {choices}") from error


def validate_fixed_ticks(value: int) -> int:
    """Validate the exact number of simulation ticks per agent decision."""

    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("fixed_ticks must be an integer")
    if value <= 0:
        raise ValueError("fixed_ticks must be positive")
    return value


def _coerce_reward_mode(value: RewardMode | str) -> RewardMode:
    if isinstance(value, RewardMode):
        return value
    if not isinstance(value, str):
        raise TypeError("reward_mode must be a RewardMode or string")
    try:
        return RewardMode(value)
    except ValueError as error:
        choices = ", ".join(mode.value for mode in RewardMode)
        raise ValueError(f"reward_mode must be one of: {choices}") from error


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """All experiment choices that change action or observation semantics."""

    render_profile: RenderProfile = FAST_RENDER_PROFILE
    fixed_ticks: int = DEFAULT_FIXED_TICKS
    reward_mode: RewardMode | str = RewardMode.DELIVERIES
    max_episode_steps: int = DEFAULT_MAX_EPISODE_STEPS

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "render_profile", resolve_render_profile(self.render_profile)
        )
        object.__setattr__(self, "fixed_ticks", validate_fixed_ticks(self.fixed_ticks))
        object.__setattr__(self, "reward_mode", _coerce_reward_mode(self.reward_mode))
        if isinstance(self.max_episode_steps, bool) or not isinstance(
            self.max_episode_steps, int
        ):
            raise TypeError("max_episode_steps must be an integer")
        if self.max_episode_steps <= 0:
            raise ValueError("max_episode_steps must be positive")

    @property
    def action_nvec(self) -> tuple[int, int, int]:
        return (len(ActionKind), self.render_profile.width, self.render_profile.height)

    @property
    def observation_shape(self) -> tuple[int, int, int]:
        return self.render_profile.observation_shape

    def descriptor(self) -> dict[str, Any]:
        return task_descriptor(self)

    def canonical_json(self) -> str:
        return canonical_json(self.descriptor())

    def fingerprint(self) -> str:
        return task_fingerprint(self)


def _map_axis(index: int, source_extent: int, target_extent: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("action coordinates must be integers")
    if index < 0 or index >= source_extent:
        raise ValueError(
            f"action coordinate {index} is outside [0, {source_extent - 1}]"
        )
    numerator = index * (target_extent - 1)
    denominator = source_extent - 1
    quotient, remainder = divmod(numerator, denominator)
    if remainder * 2 >= denominator:
        quotient += 1
    return quotient


def map_action_coordinate(
    x: int,
    y: int,
    render_profile: RenderProfile = FAST_RENDER_PROFILE,
) -> tuple[int, int]:
    """Map observation-grid indices to exact canonical viewport endpoints."""

    if not isinstance(render_profile, RenderProfile):
        raise TypeError("render_profile must be a RenderProfile")
    return (
        _map_axis(x, render_profile.width, CANONICAL_WIDTH),
        _map_axis(y, render_profile.height, CANONICAL_HEIGHT),
    )


def canonical_to_action_coordinate(
    x: int,
    y: int,
    render_profile: RenderProfile = FAST_RENDER_PROFILE,
) -> tuple[int, int]:
    """Quantize canonical viewport coordinates to their nearest action bin."""

    if not isinstance(render_profile, RenderProfile):
        raise TypeError("render_profile must be a RenderProfile")
    return (
        _map_axis(x, CANONICAL_WIDTH, render_profile.width),
        _map_axis(y, CANONICAL_HEIGHT, render_profile.height),
    )


def _episode_descriptor(max_episode_steps: int | None = None) -> dict[str, Any]:
    descriptor: dict[str, Any] = {
        "terminated_when": "game_over",
        "truncated_when": "configured_horizon_reached_without_game_over",
        "simultaneous_precedence": "terminated",
        "reset_required_after_end": True,
    }
    if max_episode_steps is not None:
        descriptor["max_episode_steps"] = max_episode_steps
    return descriptor


def protocol_descriptor() -> dict[str, Any]:
    """Return a fresh, JSON-compatible descriptor of the stable protocol."""

    return {
        "id": PROTOCOL_ID,
        "version": PROTOCOL_VERSION,
        "canonical_viewport": [CANONICAL_WIDTH, CANONICAL_HEIGHT],
        "actions": {
            "kind_axis": "append_only",
            "kinds": [
                {"label": ACTION_LABELS[kind.value], "value": kind.value}
                for kind in ActionKind
            ],
            "pointer_kinds": ["motion", "down", "up"],
            "ignored_coordinate_kinds": ["noop", "space", "1", "2", "3"],
            "coordinate_mapping": {
                "source": "render_profile_pixel_indices",
                "target": "canonical_viewport_pixel_indices",
                "method": "nearest_endpoint_integer",
                "tie_break": "half_up",
            },
        },
        "observation": {
            "kind": "rgb_pixels",
            "channel_order": "CHW",
            "dtype": "uint8",
            "bounds": [0, 255],
            "render_alpha": 1.0,
            "render_profiles": [profile.descriptor() for profile in RENDER_PROFILES],
        },
        "cursor": {
            "included_in_observation": True,
            "initial_canonical_position": list(INITIAL_CURSOR_POSITION),
            "moves_on": ["motion", "down", "up"],
            "persists_on": ["noop", "space", "1", "2", "3"],
            "pressed_state": "down_until_up",
            "composite_order": "after_game_frame_before_profile_resize",
            "shape": {
                "polygon_offsets": [list(point) for point in CURSOR_POLYGON_OFFSETS],
                "fill_rgb": list(CURSOR_FILL_COLOR),
                "outline_rgb": list(CURSOR_OUTLINE_COLOR),
                "outline_width": CURSOR_OUTLINE_WIDTH,
            },
            "pressed_marker": {
                "offset": list(CURSOR_PRESSED_MARKER_OFFSET),
                "rgb": list(CURSOR_PRESSED_MARKER_COLOR),
                "radius": CURSOR_PRESSED_MARKER_RADIUS,
                "width": CURSOR_PRESSED_MARKER_WIDTH,
            },
        },
        "transition": {
            "action_order": (
                "pointer_motion_if_changed_then_action_event_then_fixed_ticks"
            ),
            "max_raw_events_per_action": 2,
            "fixed_ticks_default": DEFAULT_FIXED_TICKS,
            "wall_clock_used": False,
        },
        "reward_modes": [mode.value for mode in RewardMode],
        "info": {
            "policy_boundary": "pixels_only_info_contains_no_live_game_state",
            "transition_keys": [
                "protocol_fingerprint",
                "task_fingerprint",
                "reward_mode",
                "render_profile",
                "decision",
                "cursor",
                "pointer_down",
                "termination_reason",
            ],
            "terminal_game_episode_keys": [
                "deliveries",
                "display_score",
                "seed",
                "simulation_time_ms",
            ],
            "terminal_metrics_available": "after_last_action_only",
        },
        "episode": _episode_descriptor(),
    }


def task_descriptor(spec: TaskSpec | None = None) -> dict[str, Any]:
    """Describe one concrete action/observation/reward task."""

    selected = spec if spec is not None else TaskSpec()
    if not isinstance(selected, TaskSpec):
        raise TypeError("spec must be a TaskSpec")
    profile = selected.render_profile
    reward_mode = _coerce_reward_mode(selected.reward_mode)
    return {
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "protocol_fingerprint": protocol_fingerprint(),
        "render_profile": profile.descriptor(),
        "fixed_ticks": selected.fixed_ticks,
        "reward_mode": reward_mode.value,
        "action_space": {
            "type": "multidiscrete",
            "nvec": list(selected.action_nvec),
            "dtype": "int64",
        },
        "observation_space": {
            "type": "box",
            "shape": list(selected.observation_shape),
            "channel_order": "CHW",
            "dtype": "uint8",
            "bounds": [0, 255],
        },
        "episode": _episode_descriptor(selected.max_episode_steps),
    }


def canonical_json(value: Any) -> str:
    """Encode JSON deterministically for manifests and fingerprints."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _fingerprint(value: Any) -> str:
    encoded = canonical_json(value).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def protocol_fingerprint() -> str:
    return _fingerprint(protocol_descriptor())


def task_fingerprint(spec: TaskSpec | None = None) -> str:
    return _fingerprint(task_descriptor(spec))
