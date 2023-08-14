import json
import subprocess
import re

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

    def __init__(self, tm, edges, eth):
        self.traffic_matrix = tm
        self.edges = edges
        self.interface = eth

    def get_weight(self):
        interface_ospf_command = "vtysh -c \"do sh ip ospf interface " + self.interface + " json\""
        interface_ospf = subprocess.run(interface_ospf_command, capture_output=True, shell=True, check=True, text=True)

        interface_conf = json.loads(interface_ospf.stdout)
        return int(interface_conf['interfaces'][self.interface]['cost'])

    def set_initial_local_state(self):
        # Get source router number
        dst_router_nr = 0
        router_id_command = "vtysh -c \"sh router-id\" | tail -n 1 | awk -F ' ' '{print $2}'"
        router_id = subprocess.run(router_id_command, capture_output=True, shell=True, check=True, text=True)
        # Router-id is as: N.N.N.N, where N is router number
        src_router_nr = router_id.stdout.split(".")[0]
        src_router_name = "R" + src_router_nr
        # Get neighbour router based on interface
        for each in self.edges:
            # Find pairs that concern source router
            if re.search(src_router_name, each['pair']):
                dst_router_name = each['pair'].replace(src_router_name, "")
                dst_router_key = "to_" + dst_router_name
                if each[dst_router_key] == self.interface:
                    # This is the agent's interface
                    dst_router_nr = int(dst_router_name.replace("R", ""))
                    break

        # Map router numbers to traffic matrix positions and return value
        if dst_router_nr == 0:
            # Error code!
            return 255
        else:
            left_index = int(src_router_nr) - 1
            right_index = dst_router_nr - 1
            self.local_state = self.traffic_matrix[left_index][right_index]
            return 0
