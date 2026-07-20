from __future__ import annotations

from typing import Any

import input_coordinator_differential_support as support


def run_layout_case() -> dict[str, Any]:
    import mediator as mediator_module
    import rendering.game_renderer as renderer_module

    host = support.bare_mediator()
    events: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    host.path_buttons = ["path-a", "path-b"]
    host.speed_buttons = ["speed-a"]
    host.game_over_restart_rect = None
    host.game_over_exit_rect = None
    host._layout_size = None

    def late_speed(buttons: list[Any], width: int, height: int) -> None:
        support.emit(
            events,
            "layout.speed",
            buttons=list(buttons),
            height=height,
            width=width,
        )
        mediator_module.game_over_button_width = 44
        mediator_module.game_over_button_height = 12

    def early_speed(*_args: Any) -> None:
        raise AssertionError("the speed updater was captured too early")

    def path_positions(buttons: list[Any], width: int, height: int) -> None:
        support.emit(
            events,
            "layout.path",
            buttons=list(buttons),
            height=height,
            width=width,
        )
        mediator_module.update_speed_button_positions = late_speed
        mediator_module.game_over_font_size = 18

    def on_copy() -> None:
        support.emit(events, "layout.copy-effect")
        mediator_module.game_over_button_spacing = 13

    def rect_factory(x: int, y: int, width: int, height: int) -> support.TraceRect:
        support.emit(
            events,
            "layout.rect-factory",
            height=height,
            width=width,
            x=x,
            y=y,
        )
        return support.TraceRect(x, y, width, height, events, on_copy)

    with (
        support.patched(
            mediator_module,
            update_path_button_positions=path_positions,
            update_speed_button_positions=early_speed,
            game_over_font_size=3,
            game_over_button_width=10,
            game_over_button_height=6,
            game_over_button_spacing=2,
        ),
        support.patched(mediator_module.pygame, Rect=rect_factory),
    ):
        mediator_module.Mediator.prepare_layout(host, 200, 100)
    layout_state = {
        "exit": {
            "height": host.game_over_exit_rect.height,
            "top": host.game_over_exit_rect.top,
            "width": host.game_over_exit_rect.width,
        },
        "layoutSize": list(host._layout_size),
        "restart": {
            "centerx": host.game_over_restart_rect.centerx,
            "height": host.game_over_restart_rect.height,
            "top": host.game_over_restart_rect.top,
            "width": host.game_over_restart_rect.width,
        },
    }
    if layout_state != {
        "exit": {"height": 12, "top": 121, "width": 44},
        "layoutSize": [200, 100],
        "restart": {"centerx": 100, "height": 12, "top": 96, "width": 44},
    }:
        raise AssertionError("late-bound layout geometry changed")
    records.append(support.record("layout-late-bindings", events, state=layout_state))

    numeric = support.NumericWidth(17)
    numeric.events = events
    screen = support.TraceScreen("fallback", host, events, numeric, object())
    with support.patched(mediator_module, screen_width=901, screen_height=502):
        surface_size = mediator_module.Mediator.get_surface_size(host, screen)
        bool_size = mediator_module.Mediator.get_surface_size(
            host,
            support.TraceScreen("bool", host, events, True, 12.9),
        )
    surface_state = {
        "boolAndFloat": list(bool_size),
        "numericAndFallback": list(surface_size),
    }
    if surface_state != {
        "boolAndFloat": [1, 12],
        "numericAndFallback": [37, 502],
    }:
        raise AssertionError("surface fallback or numeric conversion changed")
    records.append(support.record("surface-fallback", events, state=surface_state))

    render_screen = support.TraceScreen("render", host, events, 80, 60)
    host._layout_size = (1, 2)
    host._compat_renderer = None

    def get_size(screen_arg: Any) -> tuple[int, int]:
        support.emit(events, "render.get-size", screen=screen_arg.name)
        renderer_module.GameRenderer = late_renderer_factory
        return (80, 60)

    def prepare(width: int, height: int) -> None:
        support.emit(events, "render.prepare", height=height, width=width)
        host._layout_size = (width, height)

    def early_renderer_factory() -> Any:
        raise AssertionError("renderer factory was captured before surface sizing")

    def late_renderer_factory() -> support.TraceRenderer:
        support.emit(events, "renderer.construct", renderer="compat")
        return support.TraceRenderer("compat", events)

    host.get_surface_size = get_size
    host.prepare_layout = prepare
    with support.patched(renderer_module, GameRenderer=early_renderer_factory):
        mediator_module.Mediator.render(host, render_screen, alpha=0.25)
        mediator_module.Mediator.render(host, render_screen, alpha=0.5)
        mediator_module.Mediator.render(
            host,
            render_screen,
            support.TraceRenderer("explicit", events),
            alpha=0.75,
        )
    render_state = {
        "compatCached": isinstance(host._compat_renderer, support.TraceRenderer),
        "layoutSize": list(host._layout_size),
    }
    if not render_state["compatCached"] or render_state["layoutSize"] != [80, 60]:
        raise AssertionError("compatibility renderer lifecycle changed")
    records.append(support.record("render-lifecycle", events, state=render_state))

    restart = support.TraceRect(0, 0, 20, 10, events)
    restart.centerx = 10
    restart.top = 0
    exit_rect = support.TraceRect(0, 0, 20, 10, events)
    exit_rect.centerx = 10
    exit_rect.top = 20
    host.game_over_restart_rect = restart
    host.game_over_exit_rect = exit_rect
    host.is_game_over = False
    inactive = mediator_module.Mediator.handle_game_over_click(
        host, support.TracePoint((5, 5), events)
    )
    host.is_game_over = True
    restart_result = mediator_module.Mediator.handle_game_over_click(
        host, support.TracePoint((5, 5), events)
    )
    exit_result = mediator_module.Mediator.handle_game_over_click(
        host, support.TracePoint((5, 25), events)
    )
    click_state = {
        "exit": exit_result,
        "inactive": inactive,
        "restart": restart_result,
    }
    if click_state != {"exit": "exit", "inactive": None, "restart": "restart"}:
        raise AssertionError("terminal click behavior changed")
    records.append(support.record("terminal-clicks", events, state=click_state))

    host.game_over_restart_rect = "old-restart"
    host.game_over_exit_rect = "old-exit"
    host._layout_size = (7, 8)

    def partial_path(*_args: Any) -> None:
        support.emit(events, "partial.path")

    def fail_speed(*_args: Any) -> None:
        support.emit(events, "partial.speed")
        raise RuntimeError("speed layout")

    with support.patched(
        mediator_module,
        update_path_button_positions=partial_path,
        update_speed_button_positions=fail_speed,
    ):
        failure = support.capture(
            lambda: mediator_module.Mediator.prepare_layout(host, 10, 20)
        )
    partial_state = {
        "exit": host.game_over_exit_rect,
        "layoutSize": list(host._layout_size),
        "restart": host.game_over_restart_rect,
    }
    if partial_state != {
        "exit": "old-exit",
        "layoutSize": [7, 8],
        "restart": "old-restart",
    }:
        raise AssertionError("layout failure no longer preserves partial state")
    records.append(
        support.record(
            "layout-partial-failure", events, outcome=failure, state=partial_state
        )
    )
    return {"events": events, "name": "layout-render", "records": records}
