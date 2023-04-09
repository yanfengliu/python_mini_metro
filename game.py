import pygame

from city import City


class Game:
    def __init__(self, screen_width, screen_height):
        pygame.init()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Mini Metro")
        self.clock = pygame.time.Clock()

        self.city = City(
            self, station_types=["circle", "triangle", "square"], max_stations=20
        )
        self.new_station_event = pygame.USEREVENT + 1
        pygame.time.set_timer(
            self.new_station_event, 5000
        )  # Set timer to trigger every 5 seconds (5000 milliseconds)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == self.new_station_event:
                new_station = self.city.generate_station()
                if new_station:
                    print(
                        "New station created:",
                        new_station.station_type,
                        new_station.position,
                    )

            # Handle other input events here (e.g., mouse clicks, keyboard input, etc.)

    def update(self):
        # Update game state here (e.g., move trains, generate new passengers, etc.)
        pass

    def render(self):
        self.screen.fill((255, 255, 255))  # Fill the screen with white background

        # Draw stations
        for station in self.city.stations:
            color = (0, 0, 0)
            position = (int(station.position[0]), int(station.position[1]))
            if station.station_type == "circle":
                pygame.draw.circle(self.screen, color, position, 10)
            elif station.station_type == "triangle":
                points = [
                    (position[0], position[1] - 10),
                    (position[0] - 10, position[1] + 10),
                    (position[0] + 10, position[1] + 10),
                ]
                pygame.draw.polygon(self.screen, color, points)
            elif station.station_type == "square":
                pygame.draw.rect(
                    self.screen,
                    color,
                    pygame.Rect(position[0] - 10, position[1] - 10, 20, 20),
                )

        pygame.display.flip()
