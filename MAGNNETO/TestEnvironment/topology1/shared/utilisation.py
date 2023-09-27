import subprocess
import json


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
    time_from_boot = time_from_boot.stdout.strip()

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
            "TX": (int(tx_data)/(1_000_000 * float(time_from_boot)))*100,
            "RX": (int(rx_data)/(1_000_000 * float(time_from_boot)))*100
        }

    return json.dumps(output)
