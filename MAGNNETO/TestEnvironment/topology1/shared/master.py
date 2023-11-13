import numpy as np
import misc
import traffic_matrix
import requests
import concurrent.futures

"""
HYPERPARAMETERS
"""
PERIOD_COUNT = 20         # in paper - T
MESSAGE_STEPS = 4        # in paper - K
EPSILON = 0.01
DISCOUNT = 0.97
ALPHA = 0.9
STD_DEV_THRESHOLD = 1e-04

# Readout result
CURRENT_READOUT = []
READOUT_MAP = []

PACKET_DROP_STATS = []

# 0 - all routers in order, 2^n - all routers drop packets
CURRENT_GLOBAL_STATE = 0

# First run -> make decision from readout
FIRST_RUN = True

WEB_PREFIX = 'https://'
CERT_PATH = '/shared/certs/cert'


def voting(index):
    global CURRENT_READOUT
    # Perform GET request
    request_string = WEB_PREFIX + 3 * (str(index) + ".") + str(index) + ":8000/api/votingEndpoint"
    response = requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")

    CURRENT_READOUT = response.json()


def find_packet_drop(index):
    global PACKET_DROP_STATS
    # Perform GET request
    request_string = WEB_PREFIX + 3 * (str(index) + ".") + str(index) + ":8000/api/getPacketDrop"
    res = requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")

    if res.json():
        PACKET_DROP_STATS = {"R" + str(index): True}
    else:
        PACKET_DROP_STATS = {"R" + str(index): False}


# Obtain edge list
request_str = WEB_PREFIX + 3 * (str(1) + ".") + str(1) + ":8000/api/getEdges"
response = requests.get(request_str, verify=CERT_PATH + str(1) + ".pem")
edge_list = response.json()

# Q value table
q_value_table = np.zeros((2**len(edge_list), len(edge_list)))

# Distribute traffic matrix
router_count = traffic_matrix.send_tm()

# Message passing loop
for number in range(MESSAGE_STEPS):
    print("\nIteration number: " + str(number + 1))
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

    for x in range(router_count):
        pool.submit(misc.single_agent_mp, x + 1)

    pool.shutdown(wait=True)

    # Update hidden states after all threads close
    pool2 = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

    for x in range(router_count):
        pool2.submit(misc.update_h_states, x + 1)

    pool2.shutdown(wait=True)

# Perform voting
pool3 = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

for x in range(router_count):
    pool3.submit(voting, x + 1)

pool3.shutdown(wait=True)

# Check if there is any packet drop issue in the network
pool4 = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

for x in range(router_count):
    pool4.submit(find_packet_drop, x + 1)

pool4.shutdown(wait=True)

# Creating global state
for each in PACKET_DROP_STATS:
    for key, val in each.items():
        router_id = int(key.strip("R"))
        if val:
            CURRENT_GLOBAL_STATE += 2**(router_count - router_id)

# Run GNNs if any router reports packet drop
if CURRENT_GLOBAL_STATE > 0:
    # Update environment
    for edge in edge_list:
        indices = [index for index in edge['pair'].split('R') if index != '']
        uplink = "to_R" + indices[0] + "_avg"
        downlink = "to_R" + indices[1] + "_avg"

    # if FIRST_RUN:
        # Map readout
READOUT_MAP = misc.readout_map(CURRENT_READOUT, edge_list)
FIRST_RUN = False
        # Raise cost based on readout
misc.readout_raise(CURRENT_READOUT, READOUT_MAP, edge_list)



#https://venelinvalkov.medium.com/solving-an-mdp-with-q-learning-from-scratch-deep-reinforcement-learning-for-hackers-part-1-45d1d360c120