[![Demo](https://i.imgur.com/xpUow2f.png)](https://youtu.be/W5fCgqlECeI)

# python_mini_metro
This repo uses `pygame` to implement Mini Metro, a fun 2D strategic game where you try to optimize the max number of passengers your metro system can handle. Both human and program inputs are supported. One of the purposes of this implementation is to enable reinforcement learning agents to be trained on it.

# Installation
`pip install -r requirements.txt`

# How to run
## To play the game manually
* If you are running for the first time, install the requirements using `pip install -r requirements.txt`
* Activate the virtual environment by running `source myenv/bin/activate`
* Run `python src/main.py`

# Testing
`python -m unittest -v`

# 分工
- simulator : 蕭登鴻
- 複現 + 改進 (SA + other algo
- GA based : 蕭登鴻
- RL based : 林敬珣

# TODO
- 弄好api
