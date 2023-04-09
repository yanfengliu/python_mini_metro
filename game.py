import pygame

from city import City
from line import Line
from train import Train


class Game:
    def __init__(self, screen_width, screen_height):
        pygame.init()
        self.screen = pygame.display.set_mode((screen_width, screen_height))
        pygame.display.set_caption("Mini Metro")
        self.clock = pygame.time.Clock()
        self.running = True
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.city = City()
        self.lines = []
        self.trains = []
        self.current_line = None
        self.paused = False
        self.score = 0
        pygame.font.init()
        self.font = pygame.font.Font(None, 24)

    def run(self):
        while self.running:
            self.handle_input()
            self.update()
            self.render()
            self.clock.tick(60)
        pygame.quit()

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_p:
                    self.paused = not self.paused
            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = pygame.mouse.get_pos()
                clicked_station = self.city.station_at_position(pos)

                if event.button == 1:  # Left mouse button
                    if clicked_station:
                        if self.current_line is None:
                            self.current_line = Line(
                                "Line {}".format(len(self.lines) + 1)
                            )
                            self.current_line.add_station(clicked_station)
                        elif (
                            self.current_line.next_station(clicked_station) is not None
                        ):
                            self.current_line.add_station(clicked_station)
                            self.lines.append(self.current_line)
                            train = Train(self, self.current_line)
                            self.trains.append(train)
                            self.current_line = None
                        else:
                            self.current_line.add_station(clicked_station)
                elif event.button == 3:  # Right mouse button
                    if clicked_station:
                        for line in self.lines:
                            if line.remove_station(clicked_station):
                                break

    def update(self):
        if self.paused:
            return
        self.city.update()
        for train in self.trains:
            train.update()

    def render(self):
        self.screen.fill((255, 255, 255))
        self.city.render(self.screen)
        for train in self.trains:
            train.render(self.screen)

        # Draw user interface background
        pygame.draw.rect(
            self.screen,
            (200, 200, 200),
            pygame.Rect(0, self.screen_height - 50, self.screen_width, 50),
        )

        # Draw line information
        for i, line in enumerate(self.lines):
            line_text = "Line {}: {} stations".format(i + 1, len(line.stations))
            text_surface = self.font.render(line_text, True, (0, 0, 0))
            self.screen.blit(text_surface, (10 + i * 150, self.screen_height - 40))

        # Draw score
        score_text = "Score: {}".format(self.score)
        score_surface = self.font.render(score_text, True, (0, 0, 0))
        self.screen.blit(
            score_surface, (self.screen_width - 150, self.screen_height - 40)
        )

        pygame.display.flip()


if __name__ == "__main__":
    game = Game(800, 600)
    game.run()
