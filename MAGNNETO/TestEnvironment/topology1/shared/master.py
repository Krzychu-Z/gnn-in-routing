import traffic_matrix
import requests
import concurrent.futures
import time


def single_agent_mp(index):
    # Perform GET request
    request_string = "https://" + 3*(str(index)+".") + str(index) + ":8000/api/messagePass"
    response = requests.get(request_string, verify='key.pem')

    print("Message passing at R" + str(index))
    print("    Details: " + str(response.json()))


start = time.time()
# Distribute traffic matrix
router_count = traffic_matrix.send_tm()

pool = concurrent.futures.ThreadPoolExecutor(max_workers=router_count)

for x in range(router_count - 1):
    pool.submit(single_agent_mp, x + 1)

pool.shutdown(wait=True)
stop = time.time()

print(str(stop - start) + " sec.")
