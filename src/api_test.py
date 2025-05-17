from api import StaticStationGame


game = StaticStationGame(gamespeed=100, visuals=False)

print(game.run(
    ([0, 2, 4, 6, 8], True)
))
game.mediator.gamespeed = 1
print(game.run(
    ([0, 2, 4, 6, 8], True)
))