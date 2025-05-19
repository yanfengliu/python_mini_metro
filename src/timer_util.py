from time import time

class Timer:
    def __init__(self):
        self.time = 0
    
    def start(self):
        self.time = time()

    def end(self):
        return time() - self.time