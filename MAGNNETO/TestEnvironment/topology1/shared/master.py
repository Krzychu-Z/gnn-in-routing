import traffic_matrix
import requests
import concurrent.futures


PERIOD_COUNT = 20         # in paper - T


def single_agent_mp(index):
    # Perform GET request
    request_string = "https://" + 3*(str(index)+".") + str(index) + ":8000/api/messagePass"
    response = requests.get(request_string, verify="/shared/certs/cert" + str(index) + ".pem")

    print("Message passing at R" + str(index))
    print("    Details: " + str(response.json()))


def getting_readouts(index):
    # Perform GET request
    request_string = "https://" + 3 * (str(index) + ".") + str(index) + ":8000/api/votingEndpoint"
    requests.get(request_string, verify="/shared/certs/cert" + str(index) + ".pem")


# Distribute traffic matrix
router_count = traffic_matrix.send_tm()

pool = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

for x in range(router_count):
    pool.submit(single_agent_mp, x + 1)

pool.shutdown(wait=True)

# Fetch readouts
pool2 = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

for x in range(router_count):
    pool2.submit(getting_readouts, x + 1)

pool2.shutdown(wait=True)
