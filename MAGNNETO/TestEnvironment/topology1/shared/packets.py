import subprocess
import json


def get_interfaces():
    # Fetch list of interfaces on the device without loopback and two last (dummy and PC) interfaces
    interfaces_command = "netstat -i | awk 'NR>=3 && $1 != \"lo\" {print $1}' | head -n -2"
    interfaces = subprocess.run(interfaces_command, capture_output=True, shell=True, check=True, text=True)

    return interfaces


def packet_counter():
    interfaces = get_interfaces()

    # Output JSON
    output = {}

    for each in interfaces.stdout.splitlines():
        # Fetch ip address
        interface_ip_command = "ifconfig " + each + " | grep inet | awk -F ' ' '{print $2}'"
        interface_ip = subprocess.run(interface_ip_command, shell=True, check=True, text=True, capture_output=True)

        # Fetch number of transmitted packets from this interface
        packets_tx_command = "ip -s link show dev " + each + " | sed -n 4p | awk -F ' ' '{print $1}'"
        packets_tx = subprocess.run(packets_tx_command, shell=True, check=True, text=True, capture_output=True)

        # Fetch number of received packets from this interface
        packets_rx_command = "ip -s link show dev eth0 | sed -n 6p | awk -F ' ' '{print $1}'"
        packets_rx = subprocess.run(packets_rx_command, shell=True, check=True, text=True, capture_output=True)

        ip_data = interface_ip.stdout.strip()
        tx_data = packets_tx.stdout.strip()
        rx_data = packets_rx.stdout.strip()

        # Append JSON list
        output[each] = {
            "IP": ip_data,
            "TX": tx_data,
            "RX": rx_data
        }

    return json.dumps(output)
