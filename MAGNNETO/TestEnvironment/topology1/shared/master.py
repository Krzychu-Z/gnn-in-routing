import numpy as np

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

WEB_PREFIX = 'https://'
CERT_PATH = '/shared/certs/cert'

CURRENT_REWARD = []      # Readout result

# 0 - all routers idle, 2^n - all routers equally load network
CURRENT_GLOBAL_STATE = 0


def single_agent_mp(index):
    # Perform GET request
    request_string = WEB_PREFIX + 3*(str(index)+".") + str(index) + ":8000/api/messagePass"
    response = requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")

    print("Message pass at R" + str(index))
    print("    Details: " + str(response.json()))


def update_h_states(index):
    # Perform GET request
    request_string = WEB_PREFIX + 3 * (str(index) + ".") + str(index) + ":8000/api/updateHiddenStates"
    requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")


def voting(index):
    global CURRENT_REWARD
    # Perform GET request
    request_string = WEB_PREFIX + 3 * (str(index) + ".") + str(index) + ":8000/api/votingEndpoint"
    response = requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")

    CURRENT_REWARD = response.json()


# Here main loop begins
# q_value_table = np.zeros((2**len(edge_list), len(edge_list)))
# Distribute traffic matrix
router_count = traffic_matrix.send_tm()

# Message passing loop
for number in range(MESSAGE_STEPS):
    print("\nIteration number: " + str(number + 1))
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

    for x in range(router_count):
        pool.submit(single_agent_mp, x + 1)

    pool.shutdown(wait=True)

    # Update hidden states after all threads close
    pool2 = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

    for x in range(router_count):
        pool2.submit(update_h_states, x + 1)

    pool2.shutdown(wait=True)

# Construct global RL function
pool3 = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

for x in range(router_count):
    pool3.submit(voting, x + 1)

pool3.shutdown(wait=True)

# Obtain edge list
request_string = WEB_PREFIX + 3 * (str(1) + ".") + str(1) + ":8000/api/getEdges"
response = requests.get(request_string, verify=CERT_PATH + str(1) + ".pem")

edge_list = response.json()

# Compute router-based average egress link utilisation
avg_util = {}

for router in range(1, router_count + 1):
    router_util = []

    for edge in edge_list:
        # Without empty indices
        indices = [index for index in edge['pair'].split('R') if index != '']
        # Only edges regarding our current router
        if str(router) in indices:
            indices.remove(str(router))
            egress_id = "to_R" + indices[0] + "_avg"
            router_util.append(float(edge[egress_id]))

    current_avg = np.average(router_util)
    avg_util[router] = current_avg

# Calculate standard deviation and average
avg_list = [value for value in avg_util.values()]
std_dev = np.std(avg_list)
load_avg = np.average(avg_list)

# Translate avg_util to global environment state
if std_dev <= STD_DEV_THRESHOLD:
    # Here all routers can be treated as balanced
    CURRENT_GLOBAL_STATE = 2**router_count - 1
else:
    # Binary binning
    for each in range(router_count):
        if avg_util[each + 1] >= load_avg:
            CURRENT_GLOBAL_STATE += 2**(router_count - 1 - each)

print(avg_util)
print(CURRENT_GLOBAL_STATE)
