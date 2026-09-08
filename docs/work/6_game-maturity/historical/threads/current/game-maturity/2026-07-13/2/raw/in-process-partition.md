# In-process exact partition review

Live baseline: `test/test_mediator.py` is 1,158 lines with Git blob `a52b410258b513ded74e71a58bbea40cb1555506`, 57 `test_*` methods, `setUp`, `connect_stations`, and `_build_two_station_mediator`. The isolated suite passed 57/57. No files were edited during this read-only review.

## `test/mediator_test_support.py`

- `setUp`
- `connect_stations`
- `_build_two_station_mediator`

## `test/test_mediator_interaction.py`

- `test_react_mouse_down`
- `test_generate_distinct_path_colors_handles_non_positive_count`
- `test_constructor_does_not_initialize_render_resources`
- `test_generate_distinct_path_colors_backfills_color_collisions`
- `test_get_containing_entity`
- `test_react_mouse_up`
- `test_handle_game_over_click`
- `test_prepare_layout_makes_first_frame_controls_clickable`
- `test_compatibility_render_reuses_renderer_and_adapts_layout`
- `test_mouse_motion_no_entity_triggers_exit`
- `test_mouse_motion_over_button_triggers_hover`
- `test_speed_buttons_pause_and_resume_with_multiplier`

## `test/test_mediator_routing.py`

- `test_passengers_at_connected_stations_have_a_way_to_destination`
- `test_passengers_at_isolated_stations_have_no_way_to_destination`
- `test_get_station_for_shape_type`
- `test_skip_stations_on_same_path`
- `test_find_shared_path_returns_none`
- `test_find_travel_plan_handles_arrived_passenger`
- `test_passenger_boards_metro_using_shortest_destination_route`
- `test_passenger_boards_first_arriving_eligible_metro`

## `test/test_mediator_paths.py`

- `test_remove_path_cleans_passengers`
- `test_remove_path_recomputes_waiting_passenger_plan`
- `test_remove_path_keeps_onboard_plan_until_transfer_station`
- `test_add_station_to_path_returns_on_duplicate`
- `test_add_station_to_path_removes_loop`
- `test_add_station_to_path_starts_station_snap_blip`
- `test_end_path_on_station_aborts`
- `test_end_path_on_station_starts_station_snap_blip_when_added`

## `test/test_mediator_simulation.py`

- `test_passengers_are_added_to_stations`
- `test_is_passenger_spawn_time`
- `test_stations_spawn_with_independent_rhythms`
- `test_passengers_spawned_at_a_station_have_a_different_destination`
- `test_increment_time_paused`
- `test_increment_time_prunes_expired_snap_blips`
- `test_increment_time_scales_with_game_speed_multiplier`
- `test_update_waiting_game_over_at_passenger_max_wait_boundary`
- `test_update_waiting_game_over_respects_max_waiting_passengers`
- `test_update_waiting_ignores_metro_passengers_for_game_over`

## `test/test_mediator_passenger_flow.py`

- `test_move_passengers_covers_all_transfers`
- `test_move_passengers_increments_total_travels_per_delivery`
- `test_metro_stops_to_board_then_accelerates`
- `test_metro_skips_stop_when_no_one_can_board`
- `test_increment_time_handles_padding_segment_without_crashing`
- `test_full_metro_does_not_dwell_when_no_one_can_alight`
- `test_passengers_unload_one_by_one_every_half_second`
- `test_passengers_board_one_by_one_every_half_second`

## `test/test_mediator_progression.py`

- `test_progress_counters_keep_writable_legacy_aliases`
- `test_initial_path_button_locks_match_unlocked_lines`
- `test_update_unlocked_paths_updates_button_locks`
- `test_update_unlocked_paths_starts_button_blink`
- `test_path_purchase_prices_are_incremental_from_milestones`
- `test_try_purchase_path_button_unlocks_next_slot`
- `test_try_purchase_path_button_requires_enough_score`
- `test_path_unlock_no_longer_follows_total_travels`
- `test_initial_station_unlock_state`
- `test_station_unlock_progression_uses_travel_thresholds`
- `test_station_unlock_starts_new_station_blink`

The mapping contains every baseline test exactly once: 12 + 8 + 8 + 10 + 8 + 11 = 57. Each discovered module must import support as a module alias and directly import the other globals its own method bodies reference. Delete the original file without leaving an aggregator.
