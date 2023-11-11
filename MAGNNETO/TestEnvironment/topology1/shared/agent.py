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
Learning rates
"""
MPNN_LEARNING_RATE = 0.0003
READOUT_LEARNING_RATE = 0.001


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
    buffer_state = np.zeros(16, dtype=float)
    src_router_nr = 0
    dst_router_nr = 0
    current_readout = []

    def __init__(self, eth):
        self.traffic_matrix = []
        self.edges = []
        self.interface = eth
        # Set initial conditions on object construction
        self.get_weight()
        self.set_source_router()
        # Initialise NN models
        self.message_model = None
        self.update_model = None
        self.readout_model = None

    def get_weight(self):
        interface_ospf_command = "vtysh -c \"do sh ip ospf interface " + self.interface + " json\""
        try:
            interface_ospf = subprocess.run(interface_ospf_command, capture_output=True, shell=True, check=True, text=True)
            interface_conf = json.loads(interface_ospf.stdout)
            self.current_weight = int(interface_conf['interfaces'][self.interface]['cost'])
            return 0
        except Exception as e:
            print("Error occurred in get_weight: " + repr(e))
            return 255

    def raise_weight(self):
        raise_weight_command = "vtysh -c \"int " + self.interface + "\n ip ospf cost " + str(self.current_weight+1) + "\""
        try:
            raise_weight_ret = subprocess.run(raise_weight_command, capture_output=True, shell=True, check=True, text=True)
            if raise_weight_ret.stderr:
                print("Raise weight error: " + str(raise_weight_ret.stderr))
            else:
                # Update weight after changing it
                self.get_weight()
            return raise_weight_ret.stderr
        except Exception as e:
            print("Non-vtysh error occurred in set_weight: " + repr(e))
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
        self.hidden_state = np.zeros(16, dtype=float)

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

    def set_traffic_matrix(self, tm):
        self.traffic_matrix = tm

    def set_edge_list(self, edges):
        self.edges = edges

    # Edge list is needed to initialise readout MPNN
    def initialise_mpnn(self):
        self.message_model = self.message_passing_mlp()
        self.update_model = self.message_passing_mlp()
        self.readout_model = self.readout_mlp()

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
        readout_model.add(Dense(32, activation='relu', input_shape=(16,)))
        readout_model.add(Dense(32*len(self.edges), activation='relu'))
        readout_model.add(Dense(8*len(self.edges), activation='relu'))
        readout_model.add(Dense(4*len(self.edges), activation='relu'))
        # logit list for each link uplink and downlink
        readout_model.add(Dense(2*len(self.edges), activation=None))

        loss_fn = tf.keras.losses.MeanSquaredError
        readout_model.compile(optimizer=Adam(learning_rate=READOUT_LEARNING_RATE), loss=loss_fn, metrics=['accuracy'])

        return readout_model

    """
    Three agent functions mentioned in the paper
    """
    def message(self, n_hidden_states, model):
        hidden_states_prepared = [np.vstack((x, self.hidden_state)) for x in n_hidden_states]
        hidden_states_prepared = np.array(hidden_states_prepared)
        hidden_states_trained = model.predict(hidden_states_prepared, verbose=0)

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
        new_h = model.predict(combination, verbose=0)

        return new_h

    def message_pass(self):
        request_string_address = "https://" + 3*(str(self.dst_router_nr) + ".") + str(self.dst_router_nr)
        request_string_purl = ":8000/api/getHiddenStates?src=" + self.src_router_nr
        request_string = request_string_address + request_string_purl

        # Get neighbouring hidden states
        neighbouring_hidden_states = []
        try:
            response = requests.get(request_string, verify="/shared/certs/cert" + str(self.dst_router_nr) + ".pem")
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
        messages_out = self.message(neighbouring_hidden_states, self.message_model)
        # Apply aggregation function
        big_m = self.aggregate(messages_out)
        # Apply update function
        new_hidden_state = self.update(big_m, self.update_model)
        new_hidden_state = np.squeeze(new_hidden_state)
        # Buffer new hidden state
        self.buffer_state = new_hidden_state

    # This blocks other agents to read (k + 1) hidden state
    def update_hidden_state(self):
        self.hidden_state = self.buffer_state

    def readout(self):
        hidden_state_correct = self.hidden_state[np.newaxis, :]
        decision = self.readout_model.predict(hidden_state_correct, verbose=0)

        return decision

    def voting_function(self):
        search = True
        index = 1
        readouts = {}

        while search:
            # Perform GET request
            request_string = "https://" + str(index) + "." + str(index) + "." + str(index) + "." + str(
                index) + ":8000/api/getReadouts"
            try:
                response = requests.get(request_string, verify="/shared/certs/cert" + str(index) + ".pem")
            except OSError:
                search = False
            else:
                # Add JSON to router statistics
                if response.status_code == 200:
                    router_id = "R" + str(index)
                    readouts[router_id] = response.json()
                    index += 1

        vote_poll = []
        initial_iteration = True
        for router in readouts:
            for interface in readouts[router]:
                if initial_iteration:
                    vote_poll = np.array(readouts[router][interface])
                    initial_iteration = False
                else:
                    vote_poll = np.append(vote_poll, np.array(readouts[router][interface]), axis=0)

        result = np.average(vote_poll, axis=0)
        self.current_readout = result

        return result
