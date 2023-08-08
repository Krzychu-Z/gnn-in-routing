import requests

# For each router fetch all interface statistics
search = True
index = 1
router_stats = {}

while search:
    # Perform GET request
    request_string = "http://" + str(index) + "." + str(index) + "." + str(index) + "." + str(index) + ":8000/"
    response = requests.get(request_string)

    if response.status_code != 200:
        search = False
    else:
        # Add JSON to router statistics
        router_id = "R" + str(index)
        router_stats[router_id] = response
        index += 1

print(router_stats)
