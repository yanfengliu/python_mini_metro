"""Gymnasium environment exposing only player-visible pixels and player inputs."""

from __future__ import annotations

from typing import Any

import gymnasium as gym
import numpy as np
import pygame
from gymnasium import spaces

from config import screen_color
from event.convert import convert_pygame_event
from game_session import GameSession
from mediator import Mediator
from rendering.game_renderer import GameRenderer
from rl.protocol import (
    CANONICAL_HEIGHT,
    CANONICAL_WIDTH,
    CURSOR_FILL_COLOR,
    CURSOR_OUTLINE_COLOR,
    CURSOR_OUTLINE_WIDTH,
    CURSOR_POLYGON_OFFSETS,
    CURSOR_PRESSED_MARKER_COLOR,
    CURSOR_PRESSED_MARKER_OFFSET,
    CURSOR_PRESSED_MARKER_RADIUS,
    CURSOR_PRESSED_MARKER_WIDTH,
    DEFAULT_FIXED_TICKS,
    DEFAULT_MAX_EPISODE_STEPS,
    FAST_RENDER_PROFILE,
    INITIAL_CURSOR_POSITION,
    ActionKind,
    RenderProfile,
    RewardMode,
    TaskSpec,
    map_action_coordinate,
    protocol_fingerprint,
    resolve_render_profile,
    task_fingerprint,
)

_KEY_BY_ACTION = {
    ActionKind.SPACE: pygame.K_SPACE,
    ActionKind.KEY_1: pygame.K_1,
    ActionKind.KEY_2: pygame.K_2,
    ActionKind.KEY_3: pygame.K_3,
}


class PlayerPixelEnv(gym.Env[np.ndarray, np.ndarray]):
    """Train through the same pixel and input boundary used by a human player."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 10}

    def __init__(
        self,
        *,
        render_mode: str | None = None,
        render_profile: RenderProfile | str = FAST_RENDER_PROFILE,
        fixed_ticks: int = DEFAULT_FIXED_TICKS,
        reward_mode: RewardMode | str = RewardMode.DELIVERIES,
        max_episode_steps: int = DEFAULT_MAX_EPISODE_STEPS,
    ) -> None:
        super().__init__()
        if render_mode not in (None, "rgb_array"):
            raise ValueError("render_mode must be None or 'rgb_array'")
        profile = resolve_render_profile(render_profile)
        self.task_spec = TaskSpec(profile, fixed_ticks, reward_mode, max_episode_steps)
        self.metadata = {
            **type(self).metadata,
            "render_fps": 60.0 / self.task_spec.fixed_ticks,
        }
        self.render_mode = render_mode
        self.max_episode_steps = self.task_spec.max_episode_steps
        self.observation_space = spaces.Box(
            low=0,
            high=255,
            shape=self.task_spec.observation_shape,
            dtype=np.uint8,
        )
        self.action_space = spaces.MultiDiscrete(
            np.asarray(self.task_spec.action_nvec, dtype=np.int64)
        )

        self._mediator: Mediator | None = None
        self._renderer: GameRenderer | None = None
        self._session: GameSession | None = None
        self._canonical_surface: pygame.Surface | None = None
        self._observation_surface: pygame.Surface | None = None
        self._last_observation: np.ndarray | None = None
        self._cursor = INITIAL_CURSOR_POSITION
        self._pointer_down = False
        self._decision = 0
        self._seed: int | None = None
        self._last_deliveries = 0
        self._last_line_credits = 0
        self._episode_ended = False

    def _require_mediator(self) -> Mediator:
        if self._mediator is None:
            raise RuntimeError("environment must be reset before use")
        return self._mediator

    @property
    def protocol_fingerprint(self) -> str:
        return protocol_fingerprint()

    @property
    def task_fingerprint(self) -> str:
        return task_fingerprint(self.task_spec)

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        del options
        actual_seed = (
            int(seed)
            if seed is not None
            else int(self.np_random.integers(0, 2**32, dtype=np.uint64))
        )
        self._ensure_surfaces()
        self._mediator = Mediator(seed=actual_seed)
        self._renderer = GameRenderer()
        self._session = GameSession(self._mediator, step_observer=self._renderer)
        assert self._canonical_surface is not None
        self._session.prepare_layout(self._canonical_surface)
        self._cursor = INITIAL_CURSOR_POSITION
        self._pointer_down = False
        self._decision = 0
        self._seed = actual_seed
        self._last_deliveries = self._mediator.deliveries
        self._last_line_credits = self._mediator.line_credits
        self._episode_ended = False
        observation = self._observe()
        return observation, self._info(terminated=False, truncated=False)

    def step(
        self, action: np.ndarray
    ) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        if self._episode_ended:
            raise RuntimeError("episode has ended; call reset before step")
        if self._session is None:
            raise RuntimeError("environment must be reset before step")
        object_action = np.asarray(action, dtype=object)
        if any(isinstance(value, (bool, np.bool_)) for value in object_action.flat):
            raise ValueError("action values must be integers, not booleans")
        unvalidated_action = np.asarray(action)
        if not np.issubdtype(unvalidated_action.dtype, np.integer):
            raise ValueError("action values must be integers")
        if not self.action_space.contains(unvalidated_action):
            raise ValueError(f"action is outside {self.action_space}: {action!r}")
        action_value = np.asarray(unvalidated_action, dtype=np.int64)
        kind = ActionKind(int(action_value[0]))
        mediator = self._require_mediator()
        self._dispatch_action(kind, int(action_value[1]), int(action_value[2]))
        self._session.advance_exact(self.task_spec.fixed_ticks)
        self._decision += 1

        deliveries = mediator.deliveries
        line_credits = mediator.line_credits
        deliveries_delta = deliveries - self._last_deliveries
        line_credits_delta = line_credits - self._last_line_credits
        self._last_deliveries = deliveries
        self._last_line_credits = line_credits
        reward = (
            float(deliveries_delta)
            if self.task_spec.reward_mode is RewardMode.DELIVERIES
            else float(line_credits_delta)
        )
        terminated = bool(mediator.is_game_over)
        truncated = self._decision >= self.max_episode_steps and not terminated
        self._episode_ended = terminated or truncated
        observation = self._observe()
        info = self._info(terminated=terminated, truncated=truncated)
        return observation, reward, terminated, truncated, info

    def render(self) -> np.ndarray | None:
        if self.render_mode != "rgb_array":
            return None
        if self._mediator is None or self._canonical_surface is None:
            raise RuntimeError("environment must be reset before render")
        if self._last_observation is None:
            self._observe()
        canonical_whc = pygame.surfarray.array3d(self._canonical_surface)
        return np.ascontiguousarray(canonical_whc.transpose(1, 0, 2), dtype=np.uint8)

    def close(self) -> None:
        self._mediator = None
        self._renderer = None
        self._session = None
        self._canonical_surface = None
        self._observation_surface = None
        self._last_observation = None
        self._episode_ended = True

    def _ensure_surfaces(self) -> None:
        if self._canonical_surface is None:
            self._canonical_surface = pygame.Surface(
                (CANONICAL_WIDTH, CANONICAL_HEIGHT), pygame.SRCALPHA, 32
            )
        profile = self.task_spec.render_profile
        if (
            self._observation_surface is None
            or self._observation_surface.get_size() != (profile.width, profile.height)
        ):
            self._observation_surface = pygame.Surface(
                (profile.width, profile.height), pygame.SRCALPHA, 32
            )

    def _dispatch_action(self, kind: ActionKind, x: int, y: int) -> int:
        if self._session is None:
            raise RuntimeError("environment must be reset before input")
        if kind is ActionKind.NOOP:
            return 0
        key = _KEY_BY_ACTION.get(kind)
        if key is not None:
            event = pygame.event.Event(pygame.KEYUP, key=key)
            converted = convert_pygame_event(event)
            self._session.dispatch(converted)
            return 1

        position = map_action_coordinate(x, y, self.task_spec.render_profile)
        event_count = 0
        if position != self._cursor:
            self._dispatch_mouse(pygame.MOUSEMOTION, position)
            self._cursor = position
            event_count += 1
        if kind is ActionKind.MOTION:
            return event_count
        if kind is ActionKind.DOWN:
            if self._pointer_down:
                return event_count
            self._dispatch_mouse(pygame.MOUSEBUTTONDOWN, position)
            self._pointer_down = True
            return event_count + 1
        if kind is ActionKind.UP:
            if not self._pointer_down:
                return event_count
            self._dispatch_mouse(pygame.MOUSEBUTTONUP, position)
            self._pointer_down = False
            return event_count + 1
        raise AssertionError(f"unhandled action kind: {kind}")

    def _dispatch_mouse(self, event_type: int, position: tuple[int, int]) -> None:
        assert self._session is not None
        attributes: dict[str, Any] = {"pos": position}
        if event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            attributes["button"] = 1
        event = pygame.event.Event(event_type, attributes)
        converted = convert_pygame_event(event, mouse_position=position)
        self._session.dispatch(converted)

    def _observe(self) -> np.ndarray:
        if self._renderer is None or self._mediator is None:
            raise RuntimeError("environment must be reset before observation")
        self._ensure_surfaces()
        assert self._canonical_surface is not None
        assert self._observation_surface is not None
        self._canonical_surface.fill(screen_color)
        self._renderer.draw(self._canonical_surface, self._mediator, alpha=1.0)
        self._draw_cursor(self._canonical_surface)
        pygame.transform.smoothscale(
            self._canonical_surface,
            self._observation_surface.get_size(),
            self._observation_surface,
        )
        observation_whc = pygame.surfarray.array3d(self._observation_surface)
        self._last_observation = np.ascontiguousarray(
            observation_whc.transpose(2, 1, 0), dtype=np.uint8
        )
        return self._last_observation.copy()

    def _draw_cursor(self, surface: pygame.Surface) -> None:
        x, y = self._cursor
        points = tuple(
            (x + offset_x, y + offset_y)
            for offset_x, offset_y in CURSOR_POLYGON_OFFSETS
        )
        pygame.draw.polygon(surface, CURSOR_FILL_COLOR, points)
        pygame.draw.lines(
            surface, CURSOR_OUTLINE_COLOR, True, points, CURSOR_OUTLINE_WIDTH
        )
        if self._pointer_down:
            marker_x = x + CURSOR_PRESSED_MARKER_OFFSET[0]
            marker_y = y + CURSOR_PRESSED_MARKER_OFFSET[1]
            pygame.draw.circle(
                surface,
                CURSOR_PRESSED_MARKER_COLOR,
                (marker_x, marker_y),
                CURSOR_PRESSED_MARKER_RADIUS,
                CURSOR_PRESSED_MARKER_WIDTH,
            )

    def _info(
        self,
        *,
        terminated: bool,
        truncated: bool,
    ) -> dict[str, Any]:
        reason = "game_over" if terminated else "horizon" if truncated else None
        info: dict[str, Any] = {
            "protocol_fingerprint": self.protocol_fingerprint,
            "task_fingerprint": self.task_fingerprint,
            "reward_mode": self.task_spec.reward_mode.value,
            "render_profile": self.task_spec.render_profile.name,
            "decision": self._decision,
            "cursor": self._cursor,
            "pointer_down": self._pointer_down,
            "termination_reason": reason,
        }
        if terminated or truncated:
            mediator = self._require_mediator()
            info["game_episode"] = {
                "deliveries": mediator.deliveries,
                "display_score": mediator.line_credits,
                "seed": self._seed,
                "simulation_time_ms": mediator.time_ms,
            }
        return info
