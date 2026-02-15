[![Demo](https://i.imgur.com/xpUow2f.png)](https://youtu.be/W5fCgqlECeI)

# python_mini_metro
This repo uses `pygame-ce` to implement Mini Metro, a fun 2D strategic game where you try to optimize the max number of passengers your metro system can handle. Both human and program inputs are supported. One of the purposes of this implementation is to enable reinforcement learning agents to be trained on it.

# Installation
`pip install -r requirements.txt`

# How to run
## To play the game manually
* If you are running for the first time, install the requirements using `pip install -r requirements.txt`
* Activate the virtual environment by running `conda activate py313`
* Run `python src/main.py`
* Hold down the mouse left button on a station and drag onto other stations to create a path for the metro.
* Press SPACE to pause / unpause the game.
* Press `1`, `2`, or `3` to set game speed to 1x, 2x, or 4x.
* View the score on the top left corner of the screen.
* The number of grey circles on top of the screen is the number of availabel metro lines left.
* Click on the colored circle at the top to cancel an established line.

# Programmatic play
Use the Gym-like environment in `src/env.py`:

```
from env import MiniMetroEnv

env = MiniMetroEnv(dt_ms=16)
obs = env.reset(seed=42)
obs, reward, done, info = env.step(
    {"type": "create_path", "stations": [0, 1, 2], "loop": False}
)
obs, reward, done, info = env.step({"type": "remove_path", "path_index": 0})
```

# Testing
`python -m unittest -v`
