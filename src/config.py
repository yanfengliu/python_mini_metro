from geometry.type import ShapeType

# game
framerate = 60

# screen
screen_width = 1920
screen_height = 1080
screen_color = (247, 245, 239)

# station
num_stations = 20
initial_num_stations = 3
station_unlock_first_increment = 10
station_unlock_increment_step = 20
station_unlock_milestones = []
_total_station_unlock_deliveries = 0
_next_station_unlock_increment = station_unlock_first_increment
for _ in range(initial_num_stations, num_stations):
    _total_station_unlock_deliveries += _next_station_unlock_increment
    station_unlock_milestones.append(_total_station_unlock_deliveries)
    _next_station_unlock_increment += station_unlock_increment_step
station_size = 30
station_capacity = 12
station_color = (0, 0, 0)
station_shape_type_list = [
    ShapeType.RECT,
    ShapeType.CIRCLE,
    ShapeType.TRIANGLE,
    ShapeType.CROSS,
]
station_unique_shape_type_list = [
    ShapeType.DIAMOND,
    ShapeType.PENTAGON,
    ShapeType.STAR,
]
station_unique_spawn_start_index = 10
station_unique_spawn_chance = 0.35
station_passengers_per_row = 4
station_snap_blip_duration_ms = 400
station_snap_blip_radius_growth = 40
station_snap_blip_width = 3

# passenger
passenger_size = 5
passenger_color = (128, 128, 128)
passenger_spawning_start_step = 1
passenger_spawning_interval_step = 15 * framerate
passenger_display_buffer = 3 * passenger_size
passenger_max_wait_time_ms = 40_000
passenger_blink_warning_time_ms = 10_000
passenger_blink_interval_ms = 250
overdue_passenger_threshold = 2
# Deprecated value alias retained for callers importing the former config name.
max_waiting_passengers = overdue_passenger_threshold

# metro
num_metros = 4
metro_size = 30
metro_color = (200, 200, 200)
metro_outline_color = (30, 30, 30)
metro_outline_width = 2
metro_capacity = 6
metro_speed_per_ms = 150 / 1000  # pixels / ms
metro_accel_time_ms = 1000
metro_decel_time_ms = 1000
metro_boarding_time_per_passenger_ms = 500
metro_passengers_per_row = 3

# path
path_unlock_milestones = [0, 90, 300, 650]
num_paths = len(path_unlock_milestones)
path_width = 10
path_order_shift = 10

# path editing handles
path_handle_hit_radius = 36
path_handle_marker_radius = 12
path_handle_endpoint_outset = 64
path_handle_lattice_step = 56
path_handle_search_rings = 12
path_handle_viewport_margin = 40
path_handle_quantization_margin = 8
path_handle_hud_exclusion = (0, 0, 840, 200)
path_handle_ring_width = 3
path_handle_outline_width = 4
path_handle_leader_width = 3
path_handle_color = (35, 35, 35)
path_handle_selected_color = (255, 255, 255)
path_handle_invalid_color = (215, 45, 45)
path_handle_removal_width = 5

# button
button_color = (180, 180, 180)
button_size = 30
unlock_blink_count = 3
unlock_blink_duration_ms = 1000

# path button
path_button_buffer = 20
path_button_dist_to_bottom = 50
path_button_start_left = 500
path_button_cross_size = 25
path_button_cross_width = 5
path_button_locked_ring_width = 5
path_button_buy_text_color = (0, 0, 0)
path_button_buy_text_disabled_color = (140, 140, 140)
path_button_buy_text_font_size = 26

# speed button
speed_button_width = 78
speed_button_height = 40
speed_button_buffer = 12
speed_button_left_padding = 28
speed_button_dist_to_bottom = 28
speed_button_text_font_size = 28
speed_button_text_color = (20, 20, 20)
speed_button_border_color = (20, 20, 20)
speed_button_active_color = (215, 215, 215)
speed_button_hover_color = (235, 235, 235)

# text
font_name = "courier"
hud_font_size = 50
hud_display_coords = (20, 20)
hud_line_spacing = 50
# Deprecated renderer configuration aliases retained for compatibility.
score_font_size = hud_font_size
score_display_coords = hud_display_coords
game_over_font_size = 120
game_over_hint_font_size = 40
game_over_title_metric_spacing = 24
game_over_metric_spacing = 12
game_over_content_button_gap = 24
game_over_content_top_margin = 20
game_over_text_color = (20, 20, 20)
game_over_overlay_color = (0, 0, 0, 140)
game_over_button_color = (230, 230, 230)
game_over_button_border_color = (40, 40, 40)
game_over_button_border_width = 2
game_over_button_padding_x = 30
game_over_button_padding_y = 12
game_over_button_spacing = 18
game_over_button_width = 300
game_over_button_height = 64
