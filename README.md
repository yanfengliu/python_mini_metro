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
* View the score on the top left corner of the screen.
* The number of grey circles on top of the screen is the number of availabel metro lines left.
* Click on the colored circle at the top to cancel an established line.

# Testing
`python -m unittest -v`
