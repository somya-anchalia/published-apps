import json
import os
from qpylib import qpylib

class StateSerializer:
    def __init__(self, polltype):
        self.polltype = polltype
        filename = '{0}.state.json'.format(self.polltype)
        state_directory = qpylib.get_store_path() + '/malop_polling_states'
        if not os.path.exists(state_directory):
            os.makedirs(state_directory)
        self.state_filename = os.path.join(state_directory, filename)
        return
    
    def get_state(self):
        state = None
        if os.path.exists(self.state_filename):
            with open(self.state_filename) as state_file:
                state = json.load(state_file)
        return state
    
    def save_state(self, state):
        with open(self.state_filename, 'w') as state_file:
            json.dump(state, state_file)
        return