from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime_tree_sha256(source_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(source_root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def source_hashes(paths: tuple[Path, ...]) -> dict[str, str]:
    return {path.name: sha256(path.read_bytes()) for path in paths}


@contextmanager
def patched(owner: Any, **replacements: Any) -> Iterator[None]:
    previous = {name: getattr(owner, name) for name in replacements}
    for name, value in replacements.items():
        setattr(owner, name, value)
    try:
        yield
    finally:
        for name, value in previous.items():
            setattr(owner, name, value)


def emit(events: list[dict[str, Any]], event_name: str, **values: Any) -> None:
    events.append({"event": event_name, **values})


def record(
    label: str,
    events: list[dict[str, Any]],
    *,
    outcome: Any = None,
    state: Any = None,
) -> dict[str, Any]:
    return {
        "eventCursor": len(events),
        "label": label,
        "outcome": outcome,
        "state": state,
    }


def capture(call: Any) -> dict[str, Any]:
    try:
        return {"returned": call()}
    except Exception as error:  # noqa: BLE001 - exception identity is evidence
        return {
            "exception": {
                "message": str(error),
                "type": type(error).__name__,
            }
        }


def bare_mediator() -> Any:
    import mediator as mediator_module

    host = mediator_module.Mediator.__new__(mediator_module.Mediator)
    coordinator = getattr(mediator_module, "InputCoordinator", None)
    if coordinator is not None:
        host._input = coordinator()
    return host


class TraceRect:
    def __init__(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        events: list[dict[str, Any]],
        on_copy: Any = None,
    ):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.events = events
        self.on_copy = on_copy
        self._centerx = 0
        self._top = 0

    @property
    def centerx(self) -> int:
        return self._centerx

    @centerx.setter
    def centerx(self, value: int) -> None:
        emit(self.events, "rect.centerx", value=value)
        self._centerx = value

    @property
    def top(self) -> int:
        return self._top

    @top.setter
    def top(self, value: int) -> None:
        emit(self.events, "rect.top", value=value)
        self._top = value

    @property
    def bottom(self) -> int:
        return self._top + self.height

    def copy(self) -> TraceRect:
        emit(self.events, "rect.copy", top=self.top)
        if self.on_copy is not None:
            self.on_copy()
        result = TraceRect(
            self.x,
            self.y,
            self.width,
            self.height,
            self.events,
            self.on_copy,
        )
        result._centerx = self._centerx
        result._top = self._top
        return result

    def collidepoint(self, point: tuple[int, int]) -> bool:
        emit(self.events, "rect.collide", point=list(point), top=self.top)
        left = self.centerx - self.width // 2
        return (
            left <= point[0] < left + self.width and self.top <= point[1] < self.bottom
        )


class TracePoint:
    def __init__(self, point: tuple[int, int], events: list[dict[str, Any]]):
        self.point = point
        self.events = events

    def to_tuple(self) -> tuple[int, int]:
        emit(self.events, "point.to-tuple", point=list(self.point))
        return self.point


class TraceRenderer:
    def __init__(self, name: str, events: list[dict[str, Any]]):
        self.name = name
        self.events = events

    def draw(self, screen: Any, host: Any, *, alpha: float) -> None:
        emit(
            self.events,
            "renderer.draw",
            alpha=alpha,
            renderer=self.name,
            screen=screen.name,
            sameHost=host is screen.host,
        )


class TraceScreen:
    def __init__(
        self,
        name: str,
        host: Any,
        events: list[dict[str, Any]],
        width: Any,
        height: Any,
    ):
        self.name = name
        self.host = host
        self.events = events
        self.width = width
        self.height = height

    def get_width(self) -> Any:
        emit(self.events, "screen.width", screen=self.name)
        return self.width

    def get_height(self) -> Any:
        emit(self.events, "screen.height", screen=self.name)
        return self.height


class NumericWidth(int):
    events: list[dict[str, Any]]

    def __int__(self) -> int:
        emit(self.events, "numeric.int", original=int.__int__(self))
        return 37


class TraceProgression:
    def __init__(
        self,
        name: str,
        events: list[dict[str, Any]],
        *,
        previous: int,
        price: int,
    ):
        self.name = name
        self.events = events
        self.previous = previous
        self.price = price

    def set_unlocked_num_paths(self, value: int) -> tuple[int, int]:
        emit(self.events, "progression.set", name=self.name, value=value)
        return self.previous, value

    def can_purchase_resolved_path_button_idx(
        self, button_idx: int, *, next_button_idx: int, price: int | None
    ) -> bool:
        emit(
            self.events,
            "progression.can",
            button=button_idx,
            name=self.name,
            next=next_button_idx,
            price=price,
        )
        return self.name == "old" and price == self.price

    def record_path_purchase(self, price: int) -> None:
        emit(self.events, "progression.purchase", name=self.name, price=price)


class TraceButton:
    def __init__(
        self,
        name: str,
        events: list[dict[str, Any]],
        *,
        locked: bool = False,
        path: Any = None,
        action: str | None = None,
        contains: bool = False,
    ):
        self.name = name
        self.events = events
        self.is_locked = locked
        self.path = path
        self.action = action
        self.contains_result = contains

    def set_locked(self, value: bool) -> None:
        emit(self.events, "button.lock", button=self.name, value=value)
        self.is_locked = value

    def start_unlock_blink(self, time_ms: int) -> None:
        emit(self.events, "button.blink", button=self.name, time=time_ms)

    def contains(self, position: Any) -> bool:
        emit(self.events, "button.contains", button=self.name, position=position)
        return self.contains_result

    def on_hover(self) -> None:
        emit(self.events, "button.hover", button=self.name)

    def on_exit(self) -> None:
        emit(self.events, "button.exit", button=self.name)


class TraceStation:
    def __init__(
        self, name: str, events: list[dict[str, Any]], *, contains: bool = False
    ):
        self.name = name
        self.events = events
        self.contains_result = contains

    def contains(self, position: Any) -> bool:
        emit(self.events, "station.contains", position=position, station=self.name)
        return self.contains_result


class TraceDraft:
    def __init__(self, events: list[dict[str, Any]]):
        self.events = events

    def set_temporary_point(self, position: Any) -> None:
        emit(self.events, "draft.temporary", position=position)
