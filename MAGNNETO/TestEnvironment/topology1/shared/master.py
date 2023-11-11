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

# 0 - all routers idle, 2^n - all routers equally load network
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

# Compute router-based average egress link utilisation
avg_util = misc.router_avg_util(router_count, edge_list)

# Calculate standard deviation and average
avg_list = [value for value in avg_util.values()]
std_dev = np.std(avg_list)
load_avg = np.average(avg_list)

# Translate avg_util to global environment state
if std_dev <= STD_DEV_THRESHOLD:
    # Here all routers can be treated as balanced
    # And we do not change weights in network
    CURRENT_GLOBAL_STATE = 2**router_count - 1
else:
    # Binary binning
    for each in range(router_count):
        if avg_util[each + 1] >= load_avg:
            CURRENT_GLOBAL_STATE += 2**(router_count - 1 - each)

    # Update environment
    for edge in edge_list:
        indices = [index for index in edge['pair'].split('R') if index != '']
        uplink = "to_R" + indices[0] + "_avg"
        downlink = "to_R" + indices[1] + "_avg"

print(CURRENT_GLOBAL_STATE)

    # if FIRST_RUN:
        # for agent_val in CURRENT_READOUT:


#https://venelinvalkov.medium.com/solving-an-mdp-with-q-learning-from-scratch-deep-reinforcement-learning-for-hackers-part-1-45d1d360c120