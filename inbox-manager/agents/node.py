class Node:
    def __init__(self, state):
        self.state = state

    def update_state(self, key, value):
        self.state = {**self.state, key: value}

    def get_state(self):
        return self.state

    