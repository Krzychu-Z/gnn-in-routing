import json
import subprocess
import re
import numpy as np
import requests
import tensorflow as tf
from keras.models import Sequential
from keras.layers import Dense, Flatten
from keras.optimizers import Adam

"""
Hyperparameters
"""
DISCOUNT = 0.97
BETA = 0.9
EPSILON = 0.01
MPNN_LEARNING_RATE = 0.0003
READOUT_LEARNING_RATE = 0.001
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
    creating additional array after that it performs max operation on all arrays to create aggregation
    (when message function returns only one array, aggregation returns one array unchanged)
    - global state is defined as a list of mean traffic at each node with binning applied (accuracy to within one-tenth)
    (this data is simply transformed traffic matrix) - this reduces space complexity to simply O(n) = 11^n, where n is
    a number of nodes in the network. Furthermore, normalising to [0, 1] and binning into [0, 0.5] and (0.5, 1]
    reduces space complexity to 2^n, so that finally global state is an integer ranging from 1 to 2^n
    - global action is defined as a list of logit values for each link in the network (if value >= 0, then increase
    OSPF weight)
    """
    current_weight = 10     # Default OSPF metric
    hidden_state = np.zeros(16, dtype=float)
    src_router_nr = 0
    dst_router_nr = 0

    def __init__(self, tm, edges, eth):
        self.traffic_matrix = tm
        self.edges = edges
        self.interface = eth
        # Set initial conditions on object construction
        self.set_weight()
        self.set_source_router()
        self.set_destination_router()
        self.set_initial_hidden_state()
        # Initialise NN models
        # self.message_mlp()
        self.readout_model = self.readout_mlp()

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

    """
    Fully-connected NN models
    """
    def message_passing_mlp(self):
        message_model = Sequential()
        # Create a 2D vector consisting of node hidden state and neighbouring hidden state
        message_model.add(Dense(32, activation='relu', input_shape=(2, self.hidden_state.shape[0])))
        message_model.add(Dense(64, activation='relu'))
        message_model.add(Dense(32, activation='relu'))
        message_model.add(Dense(self.hidden_state.shape[0]/2))
        message_model.add(Flatten())

        loss_fn = tf.keras.losses.MeanSquaredError
        message_model.compile(optimizer=Adam(learning_rate=MPNN_LEARNING_RATE), loss=loss_fn, metrics=['accuracy'])

        return message_model

    def readout_mlp(self):
        readout_model = Sequential()
        # Analyse only final hidden state
        readout_model.add(Dense(32, activation='relu', input_shape=(1,)))
        readout_model.add(Dense(64, activation='relu'))
        readout_model.add(Dense(16, activation='relu'))
        readout_model.add(Dense(8, activation='relu'))
        readout_model.add(Dense(2, activation='relu'))
        # Q-value reward
        readout_model.add(Dense(1, activation='relu'))

        loss_fn = tf.keras.losses.MeanSquaredError
        readout_model.compile(optimizer=Adam(learning_rate=READOUT_LEARNING_RATE), loss=loss_fn, metrics=['accuracy'])

        return readout_model

    """
    Three agent functions mentioned in the paper
    """
    def message(self, n_hidden_states, model):
        hidden_states_prepared = [np.vstack((x, self.hidden_state)) for x in n_hidden_states]
        hidden_states_prepared = np.array(hidden_states_prepared)
        hidden_states_trained = model.predict(hidden_states_prepared)

        return hidden_states_trained

    def aggregate(self, msg_output):
        if msg_output.shape == (1, self.hidden_state.shape[0]):
            return msg_output
        else:
            min_vals = np.amin(msg_output, axis=0)
            msg_output = np.append(msg_output, min_vals.reshape(1, -1), axis=0)
            return np.amax(msg_output, axis=0)

    def update(self, aggregated, model):
        combination = np.append(self.hidden_state.reshape(1, -1), aggregated.reshape(1, -1), axis=0)
        # Wrapping with another dimension
        combination = combination[np.newaxis, :]
        new_h = model.predict(combination)

        return new_h

    def message_passing(self):
        request_string_address = "http://" + 3*(str(self.dst_router_nr) + ".") + str(self.dst_router_nr)
        request_string_purl = ":8000/api/getHiddenStates?src=" + self.src_router_nr
        request_string = request_string_address + request_string_purl

        # There was an issue while trying to make these models global
        message_model = self.message_passing_mlp()
        update_model = self.message_passing_mlp()

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
            messages_out = self.message(neighbouring_hidden_states, message_model)
            # Apply aggregation function
            big_m = self.aggregate(messages_out)
            # Apply update function
            new_hidden_state = self.update(big_m, update_model)
            new_hidden_state = np.squeeze(new_hidden_state)
            # Assign new hidden state
            self.hidden_state = new_hidden_state

    def readout(self):
        decision = self.readout_model.predict(self.hidden_state)

        return decision

