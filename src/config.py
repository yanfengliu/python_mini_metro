from geometry.type import ShapeType

# game
framerate = 60

# screen
screen_width = 1920
screen_height = 1080
screen_color = (255, 255, 255)

# station
num_stations = 20
initial_num_stations = 3
station_unlock_first_increment = 10
station_unlock_increment_step = 20
station_unlock_milestones = []
_total_station_unlock_travels = 0
_next_station_unlock_increment = station_unlock_first_increment
for _ in range(initial_num_stations, num_stations):
    _total_station_unlock_travels += _next_station_unlock_increment
    station_unlock_milestones.append(_total_station_unlock_travels)
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

# passenger
passenger_size = 5
passenger_color = (128, 128, 128)
passenger_spawning_start_step = 1
passenger_spawning_interval_step = 10 * framerate
passenger_display_buffer = 3 * passenger_size
passenger_max_wait_time_ms = 60_000
passenger_blink_warning_time_ms = 10_000
passenger_blink_interval_ms = 250
max_waiting_passengers = 20

# metro
num_metros = 4
metro_size = 30
metro_color = (200, 200, 200)
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

# text
score_font_size = 50
score_display_coords = (20, 20)
game_over_font_size = 120
game_over_hint_font_size = 40
game_over_text_color = (20, 20, 20)
game_over_overlay_color = (0, 0, 0, 140)
game_over_button_color = (230, 230, 230)
game_over_button_border_color = (40, 40, 40)
game_over_button_border_width = 2
game_over_button_padding_x = 30
game_over_button_padding_y = 12
game_over_button_spacing = 18
