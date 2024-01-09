import time
import requests
import concurrent.futures


T = 100
PACKET_DROP_SUM = 0
PACKET_TOTAL = 0


def find_packet_drop(index):
    global PACKET_DROP_SUM, PACKET_TOTAL
    # Perform GET request
    request_string = "https://" + 3 * (str(index) + ".") + str(index) + ":8000/api/getPacketDrop"
    result = requests.get(request_string, verify='/shared/certs/cert' + str(index) + ".pem")
    PACKET_DROP_SUM += sum(result.json()['dr'])
    PACKET_TOTAL += sum(result.json()['total'])


# Find router count
rtr_count = 0
while True:
    rtr_count += 1
    try:
        find_packet_drop(rtr_count)
    except Exception as e:
        print(e)
        break

    if rtr_count > 1000:
        break

# Main loop
for large_t in range(T):
    # Get packet drop
    PACKET_DROP_SUM = 0
    PACKET_TOTAL = 0

    new_pool = concurrent.futures.ThreadPoolExecutor(max_workers=rtr_count)

    for i in range(rtr_count):
        new_pool.submit(find_packet_drop, i + 1)

    new_pool.shutdown(wait=True)

    packet_percent = (PACKET_DROP_SUM/PACKET_TOTAL)*100
    print(str(PACKET_DROP_SUM) + "\t" + str(packet_percent))

    # Approx duration of T is 25 minutes
    time.sleep(15)
