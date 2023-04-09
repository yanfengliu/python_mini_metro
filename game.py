import pygame

from city import City
from line import Line
from train import Train


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
        # Inside the Game class constructor
        self.new_passenger_event = pygame.USEREVENT + 2
        pygame.time.set_timer(
            self.new_passenger_event, 1000
        )  # Set timer to trigger every 1 second (1000 milliseconds)

        self.lines = []
        self.trains = []

        # Create a sample line and train (You can replace this with a more sophisticated logic later)
        line = Line("Line 1")
        self.lines.append(line)
        train = Train(line)
        self.trains.append(train)

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

            if event.type == self.new_passenger_event:
                new_passenger = self.city.generate_passenger()
                if new_passenger:
                    print("New passenger created:", new_passenger.destination_type)

            if event.type == self.new_station_event:
                new_station = self.city.generate_station()
                if new_station:
                    print(
                        "New station created:",
                        new_station.station_type,
                        new_station.position,
                    )
                    if len(self.lines[0].stations) < self.city.max_stations:
                        self.lines[0].add_station(new_station)

            # Handle other input events here (e.g., mouse clicks, keyboard input, etc.)

    def update(self):
        # Update game state here (e.g., move trains, generate new passengers, etc.)
        for train in self.trains:
            train.move()

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

        # Draw lines
        for line in self.lines:
            for i in range(len(line.stations) - 1):
                start_pos = line.stations[i].position
                end_pos = line.stations[i + 1].position
                pygame.draw.line(self.screen, (0, 0, 255), start_pos, end_pos, 3)

        # Draw trains
        for train in self.trains:
            if train.current_station:
                pos = train.current_station.position
                pygame.draw.rect(
                    self.screen,
                    (255, 0, 0),
                    pygame.Rect(pos[0] - 5, pos[1] - 5, 10, 10),
                )

        pygame.display.flip()
