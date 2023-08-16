import json
import subprocess
import re
import numpy as np

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
    """
    local_state = 0
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
        self.set_initial_local_state()

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

    def set_initial_local_state(self):
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
            self.local_state = self.traffic_matrix[left_index][right_index]
            return 0

    def get_hidden_state(self):
        return self.hidden_state
