"""
File for many functions used by master.py
"""
import copy
import numpy as np
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


def router_avg_util(rtr_count, edges):
    """
    Compute router-based average egress link utilisation

    :param rtr_count: number of routers in the network
    :param edges: list of links in the network
    :return: router-based statistics
    """
    avg_util = {}

    for router in range(1, rtr_count + 1):
        router_util = []

        for edge in edges:
            # Without empty indices
            indices = [index for index in edge['pair'].split('R') if index != '']
            # Only edges regarding our current router
            if str(router) in indices:
                indices.remove(str(router))
                egress_id = "to_R" + indices[0] + "_avg"
                router_util.append(float(edge[egress_id]))

        current_avg = np.average(router_util)
        avg_util[router] = current_avg

    return avg_util


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

    ret = []

    for _ in range(len(readout_copy)):
        for edge in edge_list_copy:
            min_value_index1 = link_utils.index(min(link_utils))
            max_value_index2 = readout_copy.index(max(readout_copy))
            min_readout = min(readout_copy)

            indices = [index for index in edge['pair'].split('R') if index != '']
            uplink = "to_R" + indices[0] + "_avg"
            downlink = "to_R" + indices[1] + "_avg"

            if edge[uplink] == link_utils[min_value_index1]:
                match = {}
                directed_ids = "R" + indices[1] + "R" + indices[0]
                match[directed_ids] = max_value_index2
                ret.append(match)
                # Now duplicated comparison with minimum should not be possible
                edge[uplink] += 1
                # Utilisation is a fraction
                link_utils[min_value_index1] = 2
                readout_copy[max_value_index2] = min_readout - 1
            elif edge[downlink] == link_utils[min_value_index1]:
                match = {}
                directed_ids = "R" + indices[0] + "R" + indices[1]
                match[directed_ids] = max_value_index2
                ret.append(match)
                # Now duplicated comparison with minimum should not be possible
                edge[downlink] += 1
                # Utilisation is a fraction
                link_utils[min_value_index1] = 2
                readout_copy[max_value_index2] = min_readout - 1

    return ret
