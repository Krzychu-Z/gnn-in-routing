import subprocess
import json
import re
import numpy as np


def get_interfaces():
    # Fetch list of interfaces on the device without loopback and two last (dummy and PC) interfaces
    interfaces_command = "netstat -i | awk 'NR>=3 && $1 != \"lo\" {print $1}' | head -n -2"
    interfaces = subprocess.run(interfaces_command, capture_output=True, shell=True, check=True, text=True)

    return interfaces


def link_utilisation():
    interfaces = get_interfaces()

    # Output JSON
    output = {}

    # Fetch time from boot in seconds
    time_from_boot_cmd = "cat /proc/uptime | awk -F ' ' '{print $1}'"
    time_from_boot = subprocess.run(time_from_boot_cmd, shell=True, check=True, text=True, capture_output=True)
    time_from_boot = float(time_from_boot.stdout.strip())

    for each in interfaces.stdout.splitlines():
        # Fetch ip address
        interface_ip_command = "ifconfig " + each + " | grep inet | awk -F ' ' '{print $2}'"
        interface_ip = subprocess.run(interface_ip_command, shell=True, check=True, text=True, capture_output=True)

        # Fetch number of transmitted packets from this interface
        bits_tx_command = "ip -s link show dev " + each + " | sed -n 4p | awk -F ' ' '{print $1}'"
        bits_tx = subprocess.run(bits_tx_command, shell=True, check=True, text=True, capture_output=True)

        # Fetch number of received packets from this interface
        bits_rx_command = "ip -s link show dev " + each + " | sed -n 6p | awk -F ' ' '{print $1}'"
        bits_rx = subprocess.run(bits_rx_command, shell=True, check=True, text=True, capture_output=True)

        ip_data = interface_ip.stdout.strip()
        tx_data = bits_tx.stdout.strip()
        rx_data = bits_rx.stdout.strip()

        # Append JSON list
        # Formula: Link Utilization (%) = (Total Bits / (Link Capacity * Time Period)) * 100
        # Link Capacity: 1 Mbps
        output[each] = {
            "IP": ip_data,
            "TX": (int(tx_data)/(1_000_000 * time_from_boot))*100,
            "RX": (int(rx_data)/(1_000_000 * time_from_boot))*100
        }

    return json.dumps(output)


def packet_drop_detect(prev_drop_count):
    # Fetch packet drop stats - exclude interface to PC and loopback
    drop_command = "netstat -i | awk '{print $4, $8}' | tail -n +3 | head -n -2"
    drop = subprocess.run(drop_command, shell=True, check=True, text=True, capture_output=True)
    drop = drop.stdout.strip().replace("\n", " ").split()

    drop_count = [int(num) for num in drop]

    if prev_drop_count == "":
        gradient = drop_count
    else:
        previous_dr_count = np.array(prev_drop_count)
        next_dr_count = np.array(drop_count)

        gradient = np.subtract(next_dr_count, previous_dr_count)

    for diff in gradient:
        if diff > 0:
            return {'detection': True, 'new_grad': gradient}

    return {'detection': False, 'new_grad': gradient}
