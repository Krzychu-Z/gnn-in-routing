import traffic_matrix
import requests
import concurrent.futures


PERIOD_COUNT = 20         # in paper - T
MESSAGE_STEPS = 4        # in paper - K

WEB_PREFIX = 'https://'
CERT_PATH = '/shared/certs/cert'


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
    # Perform GET request
    request_string = WEB_PREFIX + 3 * (str(index) + ".") + str(index) + ":8000/api/votingEndpoint"
    requests.get(request_string, verify=CERT_PATH + str(index) + ".pem")


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
