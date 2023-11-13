"""
File for many functions used by master.py
"""
import copy
import requests


WEB_PREFIX = 'https://'
CERT_PATH = '/shared/certs/cert'


# Non-return API request functions for parallel call
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


def readout_map(readout, edge_list):
    """
    Function used to sort out which readout vector positions refer to what physical links in the network

    :param readout: array of 2*L size, where L - number of links in the network
    :param edge_list: list of dicts containing topology information
    :return: dict containing link name A to B and number indicating its index in readout
    """
    link_utils = []
    readout_copy = copy.deepcopy(readout)
    edge_list_copy = copy.deepcopy(edge_list)
    for edge in edge_list_copy:
        indices = [index for index in edge['pair'].split('R') if index != '']
        uplink = "to_R" + indices[0] + "_avg"
        downlink = "to_R" + indices[1] + "_avg"

        link_utils.append(float(edge[uplink]))
        link_utils.append(float(edge[downlink]))

    ret = {}

    for _ in range(len(readout_copy)):
        for edge in edge_list_copy:
            min_value_index1 = link_utils.index(min(link_utils))
            max_value_index2 = readout_copy.index(max(readout_copy))
            min_readout = min(readout_copy)

            indices = [index for index in edge['pair'].split('R') if index != '']
            uplink = "to_R" + indices[0] + "_avg"
            downlink = "to_R" + indices[1] + "_avg"

            if edge[uplink] == link_utils[min_value_index1]:
                directed_ids = "R" + indices[1] + "R" + indices[0]
                ret[max_value_index2] = directed_ids
                # Now duplicated comparison with minimum should not be possible
                edge[uplink] += 1
                # Utilisation is a fraction
                link_utils[min_value_index1] = 2
                readout_copy[max_value_index2] = min_readout - 1
            elif edge[downlink] == link_utils[min_value_index1]:
                directed_ids = "R" + indices[0] + "R" + indices[1]
                ret[max_value_index2] = directed_ids
                # Now duplicated comparison with minimum should not be possible
                edge[downlink] += 1
                # Utilisation is a fraction
                link_utils[min_value_index1] = 2
                readout_copy[max_value_index2] = min_readout - 1

    return ret


def readout_raise(readout, r_map, edges):
    for position, each in enumerate(readout):
        # We assume readout consists of logit values
        if each > 0:
            link_name = r_map[position]
            indices = [index for index in link_name.split('R') if index != '']
            alter_link_name = "R" + indices[0] + "R" + indices[1]
            alter_2_link_name = "R" + indices[1] + "R" + indices[0]

            for edge in edges:
                if alter_link_name in edge:
                    interface_key = "to_R" + indices[1]
                    if_raise = edge[interface_key]
                    # Send HTTP request
                    request_addr = WEB_PREFIX + 3 * (str(indices[0]) + ".") + str(indices[0])
                    request_purl = ":8000/api/raiseWeight?agent=" + if_raise
                    request_str = request_addr + request_purl
                    response = requests.get(request_str, verify=CERT_PATH + str(indices[0]) + ".pem")
                    err_code = response.json()
                    print(err_code)
                elif alter_2_link_name in edge:
                    interface_key = "to_R" + indices[0]
                    if_raise = edge[interface_key]
                    # Send HTTP request
                    request_addr = WEB_PREFIX + 3 * (str(indices[1]) + ".") + str(indices[1])
                    request_purl = ":8000/api/raiseWeight?agent=" + if_raise
                    request_str = request_addr + request_purl
                    response = requests.get(request_str, verify=CERT_PATH + str(indices[1]) + ".pem")
                    err_code = response.json()
                    print(err_code)