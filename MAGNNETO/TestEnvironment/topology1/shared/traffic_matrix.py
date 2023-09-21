import json
import requests
import numpy as np


# For each router fetch all interface statistics
search = True
index = 1
router_stats = {}

while search:
    # Perform GET request
    request_string = "https://" + 3*(str(index)+".") + str(index) + ":8000/api/packets"
    try:
        response = requests.get(request_string, verify="/shared/certs/cert" + str(index) + ".pem")
    except OSError:
        search = False
    else:
        # Add JSON to router statistics
        if response.status_code == 200:
            router_id = "R" + str(index)
            router_stats[router_id] = response.json()
            index += 1


edges = []
buffer = {}
router_count = len(router_stats)
# Creating actual traffic matrix
# Traffic direction goes as: columns to rows
traffic_matrix = np.zeros((router_count, router_count), dtype=float)


# Match IP addresses in links
break_out_flag = False
while router_stats:
    for router in router_stats:
        for interface in router_stats[router]:
            # Refill buffer
            if not buffer:
                buffer = router_stats[router][interface]
                buffer['device_name'] = router
                buffer['interface_name'] = interface
                ip_address = router_stats[router][interface]['IP']
                buffer['network'] = '.'.join(ip_address.rsplit('.', 1)[:-1])
            # Comparison phase
            else:
                current_ip = router_stats[router][interface]['IP']
                current_network = '.'.join(current_ip.rsplit('.', 1)[:-1])
                # Same network!
                if current_network == buffer['network']:
                    # Data for edge analysis (interfaces)
                    link_data = {'pair': buffer['device_name'] + router}
                    to_buffer_name = "to_" + buffer['device_name']
                    to_router_name = "to_" + router
                    link_data[to_buffer_name] = interface
                    link_data[to_router_name] = buffer['interface_name']

                    # Data for traffic matrix analysis
                    to_buffer_avg = "to_" + buffer['device_name'] + "_avg"
                    to_router_avg = "to_" + router + "_avg"
                    link_data[to_buffer_avg] = (int(buffer['RX']) + int(router_stats[router][interface]['TX']))/2
                    link_data[to_router_avg] = (int(buffer['TX']) + int(router_stats[router][interface]['RX']))/2
                    edges.append(link_data)
                    # Remove linked interface's keys (2 keys)
                    del router_stats[router][interface]
                    del router_stats[buffer['device_name']][buffer['interface_name']]
                    # Clear buffer
                    buffer = {}
                    break_out_flag = True
                    break

        if break_out_flag:
            break_out_flag = False
            break

    # This removes empty router dicts
    router_stats = {k: v for k, v in router_stats.items() if v}


for edge in edges:
    indices = [index for index in edge['pair'].split('R') if index != '']
    first_direction = "to_R" + indices[0] + "_avg"
    second_direction = "to_R" + indices[1] + "_avg"
    indices[0] = int(indices[0]) - 1
    indices[1] = int(indices[1]) - 1
    traffic_matrix[indices[1]][indices[0]] = edge[first_direction]
    traffic_matrix[indices[0]][indices[1]] = edge[second_direction]

# Max Normalisation - we need to maintain zero values as they denote that a direct link between X and Y does not exist
maximum = np.max(traffic_matrix)

traffic_matrix /= maximum


def send_tm():
    # Send the matrix to each distributed agent
    # For each router fetch all interface statistic
    search_send = True
    index_send = 1

    while search_send:
        # Perform GET request
        request_send = "https://" + 3*(str(index_send)+".") + str(index_send) + ":8000/api/trafficMatrix"
        try:
            data = {'matrix': traffic_matrix.tolist(), 'edges': edges}
            res = requests.post(request_send, data=json.dumps(data), headers={"Content-Type": "application/json"},
                                verify='key.pem')
        except OSError:
            search_send = False
        else:
            # Add JSON to router statistics
            if res.status_code == 200:
                print("Response from " + 3*(str(index_send)+".") + str(index_send) + ": " + str(res.json()))
                index_send += 1

    return index_send
