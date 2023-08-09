import requests
import numpy as np

# For each router fetch all interface statistics
search = True
index = 1
router_stats = {}

while search:
    # Perform GET request
    request_string = "http://" + str(index) + "." + str(index) + "." + str(index) + "." + str(index) + ":8000/"
    try:
        response = requests.get(request_string)
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
                    link_data = {'pair': buffer['device_name'] + router}
                    to_buffer_string = "to_" + buffer['device_name'] + "_avg"
                    to_router_string = "to_" + router + "_avg"
                    link_data[to_buffer_string] = (int(buffer['RX']) + int(router_stats[router][interface]['TX']))/2
                    link_data[to_router_string] = (int(buffer['TX']) + int(router_stats[router][interface]['RX']))/2
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

# Creating actual traffic matrix
# Traffic direction goes as: columns to rows
traffic_matrix = np.zeros((router_count, router_count), dtype=float)

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

print(traffic_matrix)
traffic_matrix /= maximum
print(traffic_matrix)
