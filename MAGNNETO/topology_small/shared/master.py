import random
import time
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
EPSILON = 0.1
DISCOUNT = 0.97
ALPHA = 0.9
T = 100

# Readout result
CURRENT_READOUT = []
READOUT_MAP = []

# Statistics
PACKET_DROP_STATS = []
PACKET_DROP_SUM = 0
PACKET_TOTAL = 0

# 0 - all routers in order, 2^n - all routers drop packets
CURRENT_GLOBAL_STATE = 0
NEXT_GLOBAL_STATE = 0
STABILISATION_START = 0

# First run -> make decision from readout
FIRST_RUN = True

WEB_PREFIX = 'https://'
CERT_PATH = '/shared/certs/cert'


def voting(index):
    global CURRENT_READOUT
    # Perform GET request
    request_string = WEB_PREFIX + 3 * (str(index) + ".") + str(index) + ":8000/api/votingEndpoint"
    resp = requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")

    CURRENT_READOUT = resp.json()


def find_packet_drop(index):
    global PACKET_DROP_STATS, PACKET_DROP_SUM, PACKET_TOTAL
    # Perform GET request
    request_string = WEB_PREFIX + 3 * (str(index) + ".") + str(index) + ":8000/api/getPacketDrop"
    result = requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")

    PACKET_DROP_STATS.append({"R" + str(index): result.json()['res']})
    print("Packet drop R" + str(index) + ": " + str(result.json()['dr']))
    PACKET_DROP_SUM += sum(result.json()['dr'])
    PACKET_TOTAL += sum(result.json()['total'])


def read_global_state(rtr_count):
    global PACKET_DROP_STATS
    new_pool = concurrent.futures.ThreadPoolExecutor(max_workers=rtr_count)
    PACKET_DROP_STATS = []

    for counter in range(rtr_count):
        new_pool.submit(find_packet_drop, counter + 1)

    new_pool.shutdown(wait=True)

    buffer_state = 0

    for drop in PACKET_DROP_STATS:
        for key, val in drop.items():
            router_id = int(key.strip("R"))
            if val:
                buffer_state += 2 ** (router_count - router_id)

    return buffer_state


# Distribute traffic matrix
router_count = traffic_matrix.send_tm()

# Obtain edge list
request_str = WEB_PREFIX + 3 * (str(1) + ".") + str(1) + ":8000/api/getEdges"
response = requests.get(request_str, verify=CERT_PATH + str(1) + ".pem")
edge_list = response.json()

# Q value table
q_value_table = np.zeros((2**router_count - 1, 2*len(edge_list)))

for large_t in range(T):
    if large_t != 0:
        # Distribute traffic matrix
        traffic_matrix.send_tm()

    # Message passing loop
    for number in range(MESSAGE_STEPS):
        print("\nIteration number: " + str(number + 1))
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

        for x in range(router_count):
            pool.submit(misc.single_agent_mp, x + 1, number)

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

    # Train readout
    pool4 = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

    for x in range(router_count):
        pool4.submit(misc.readout_workout, x + 1)

    pool4.shutdown(wait=True)

    # Check if there is any packet drop issue in the network
    CURRENT_GLOBAL_STATE = read_global_state(router_count)

    print("Read gl state: " + str(CURRENT_GLOBAL_STATE))
    print("Packet drop sum: " + str(PACKET_DROP_SUM))

    # Determine packet ratio
    ratio = (PACKET_DROP_SUM/PACKET_TOTAL)*100

    # Write results to csv
    if large_t == 0:
        f = open('results.csv', 'w')
        f.write("Large T,\tDropped packets uniform\n")
        f.write(str(PACKET_DROP_SUM) + "\t" + str(ratio) + "\n")
    else:
        f = open('results.csv', 'a')
        f.write(str(PACKET_DROP_SUM) + "\t" + str(ratio) + "\n")

    f.close()

    # Run GNNs if any router reports packet drop
    if CURRENT_GLOBAL_STATE > 0:
        # Begin stabilisation period
        print("Entered stabilisation period")
        STABILISATION_START = time.time()

        if FIRST_RUN:
            # Map readout
            READOUT_MAP = misc.readout_map(CURRENT_READOUT, edge_list)
            FIRST_RUN = False
            # Raise cost based on readout
            misc.readout_raise(CURRENT_READOUT, READOUT_MAP, edge_list)
        else:
            # Choose q-value based raise with EPSILON probability
            chance = random.random()

            if chance <= EPSILON:
                misc.q_learning_raise(q_value_table[CURRENT_GLOBAL_STATE], READOUT_MAP, edge_list)
            else:
                misc.readout_raise(CURRENT_READOUT, READOUT_MAP, edge_list)

        # Wait 10 seconds for OSPF to send Hello packets
        print("\nWaiting 10 seconds for OSPF to send Hello packets\n")
        time.sleep(10)

        # Read global state s+1
        NEXT_GLOBAL_STATE = read_global_state(router_count)
        # Update Q-values
        maximum_q = max(q_value_table[NEXT_GLOBAL_STATE])
        for action, value in enumerate(q_value_table[CURRENT_GLOBAL_STATE]):
            alpha_part = CURRENT_READOUT[action] + DISCOUNT*maximum_q - value
            q_value_table[CURRENT_GLOBAL_STATE][action] = value + ALPHA*alpha_part

        if NEXT_GLOBAL_STATE == 0:
            STABILISATION_STOP = time.time()
            period = STABILISATION_STOP - STABILISATION_START
            print("Stabilisation duration: " + str(period) + "s.")
            STABILISATION_START = 0

    PACKET_DROP_SUM = 0
