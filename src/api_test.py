from api import StaticStationGame

from timer import Timer

timer = Timer()
game = StaticStationGame(gamespeed=50, visuals=True)

timer.start()

print(game.run(
    ([0, 2, 4, 6, 8], True),
    ([0, 1, 3, 5, 7], True),
    ([1, 3, 7, 9, 5], True)
))

print("v=True, Time taken:", timer.end())

game.visuals = False

timer.start()

print(game.run(
    ([0, 2, 4, 6, 8], True),
    ([0, 1, 3, 5, 7], True),
    ([1, 3, 7, 9, 5], True)
))

print("v=False, Time taken:", timer.end())