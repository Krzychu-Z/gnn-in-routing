import json
import subprocess
import re
import numpy as np
import requests
import tensorflow as tf
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam

"""
Hyperparameters
"""
DISCOUNT = 0.97
BETA = 0.9
EPSILON = 0.01
LEARNING_RATE = 0.0003
CLIPPING_PARAM = 0.2
PERIOD_COUNT = 20         # in paper - T
MESSAGE_STEPS = 4        # in paper - K


class Agent:
    """
    Agent class

    Assumptions:
    - agent is per link
    - initial local state is simply a cell from traffic matrix
    - link neighbourhood is understood as other links connected to destination router
    - hidden initial state consists of one initial local state and link weight
    - aggregate function takes array of arrays returned by message function, performs element-wise min operation
    """
    current_weight = 10     # Default OSPF metric
    hidden_state = np.zeros(16, dtype=float)
    src_router_nr = 0
    dst_router_nr = 0

    # ML models
    message_model = Sequential()

    def __init__(self, tm, edges, eth):
        self.traffic_matrix = tm
        self.edges = edges
        self.interface = eth
        # Set initial conditions on object construction
        self.set_weight()
        self.set_source_router()
        self.set_destination_router()
        self.set_initial_hidden_state()
        # Initialise message NN model
        self.message_mlp()

    def set_weight(self):
        interface_ospf_command = "vtysh -c \"do sh ip ospf interface " + self.interface + " json\""
        try:
            interface_ospf = subprocess.run(interface_ospf_command, capture_output=True, shell=True, check=True, text=True)
            interface_conf = json.loads(interface_ospf.stdout)
            self.current_weight = int(interface_conf['interfaces'][self.interface]['cost'])
            return 0
        except Exception as e:
            print("Error occurred in set_weight: " + repr(e))
            return 255

    def set_source_router(self):
        try:
            router_id_command = "vtysh -c \"sh router-id\" | tail -n 1 | awk -F ' ' '{print $2}'"
            router_id = subprocess.run(router_id_command, capture_output=True, shell=True, check=True, text=True)
            # Router-id is as: N.N.N.N, where N is router number
            self.src_router_nr = router_id.stdout.split(".")[0]
            return 0
        except Exception as e:
            print("Error while determining source router: " + repr(e))
            return 255

    def set_destination_router(self):
        # Get neighbour router based on router name
        src_router_name = "R" + self.src_router_nr

        for each in self.edges:
            # Find pairs that concern source router
            if re.search(src_router_name, each['pair']):
                dst_router_name = each['pair'].replace(src_router_name, "")
                dst_router_key = "to_" + dst_router_name
                if each[dst_router_key] == self.interface:
                    # This is the agent's interface
                    self.dst_router_nr = int(dst_router_name.replace("R", ""))
                    break

    def set_initial_hidden_state(self):
        # Map router numbers to traffic matrix positions and return value
        if self.src_router_nr == 0:
            print("Source router number has not been established. Couldn't set initial local state.")
            return 255
        elif self.dst_router_nr == 0:
            print("Destination router number has not been established. Couldn't set initial local state.")
            return 255
        else:
            left_index = int(self.src_router_nr) - 1
            right_index = self.dst_router_nr - 1
            link_utilisation = self.traffic_matrix[left_index][right_index]
            self.hidden_state[0] = self.current_weight
            self.hidden_state[1] = link_utilisation
            return 0

    def message_mlp(self):
        # Create a 2D vector consisting of node hidden state and neighbouring hidden state
        self.message_model.add(Dense(32, activation='relu', input_shape=(2, self.hidden_state.shape[0])))
        self.message_model.add(Dense(64, activation='relu'))
        self.message_model.add(Dense(32, activation='relu'))
        self.message_model.add(Dense(self.hidden_state.shape))

        loss_fn = tf.keras.losses.MeanSquaredError
        self.message_model.compile(optimizer=Adam(learning_rate=LEARNING_RATE), loss=loss_fn, metrics=['accuracy'])

    def message(self, n_hidden_states):
        hidden_states_prepared = [np.vstack((x, self.hidden_state)) for x in n_hidden_states]
        hidden_states_trained = []

        # Mix messages separately
        for each in hidden_states_prepared:
            result = self.message_model.predict(each)
            hidden_states_trained.append(result)

        return hidden_states_trained

    def message_passing(self):
        request_string_address = "http://" + 3*(str(self.dst_router_nr) + ".") + str(self.dst_router_nr)
        request_string_purl = ":8000/api/getHiddenStates?src=" + self.src_router_nr
        request_string = request_string_address + request_string_purl
        for _ in range(MESSAGE_STEPS):
            # Get neighbouring hidden states
            neighbouring_hidden_states = []
            try:
                response = requests.get(request_string)
            except OSError as e:
                print("Error: Could not contact API (/api/getHiddenStates): " + repr(e))
            else:
                # Add hidden state to list
                if response.status_code == 200:
                    data = response.json()
                    for each in data:
                        array = np.array(data[each])
                        neighbouring_hidden_states.append(array)

            # Apply message function
            print(neighbouring_hidden_states)
            test = self.message(neighbouring_hidden_states)
            print(test)
