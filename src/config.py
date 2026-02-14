from geometry.type import ShapeType

# game
framerate = 60

# screen
screen_width = 1920
screen_height = 1080
screen_color = (255, 255, 255)

# station
num_stations = 10
station_size = 30
station_capacity = 12
station_color = (0, 0, 0)
station_shape_type_list = [
    ShapeType.RECT,
    ShapeType.CIRCLE,
    ShapeType.TRIANGLE,
    ShapeType.CROSS,
]
station_passengers_per_row = 4

# passenger
passenger_size = 5
passenger_color = (128, 128, 128)
passenger_spawning_start_step = 1
passenger_spawning_interval_step = 10 * framerate
passenger_display_buffer = 3 * passenger_size
passenger_max_wait_time_ms = 60_000
max_waiting_passengers = 20

# metro
num_metros = 4
metro_size = 30
metro_color = (200, 200, 200)
metro_capacity = 6
metro_speed_per_ms = 150 / 1000  # pixels / ms
metro_passengers_per_row = 3

# path
path_unlock_milestones = [0, 100, 250, 500]
num_paths = len(path_unlock_milestones)
path_width = 10
path_order_shift = 10

# button
button_color = (180, 180, 180)
button_size = 30

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
