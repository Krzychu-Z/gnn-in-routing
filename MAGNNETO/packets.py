import subprocess
import json
from flask import Flask

app = Flask(__name__)

# Fetch list of interfaces on the device without loopback interface
interfaces_command = "netstat -i | awk 'NR>=3 && $1 != \"lo\" {print $1}'"
interfaces = subprocess.run(interfaces_command, capture_output=True, shell=True, check=True, text=True)

# Output JSON

output = {}

for each in interfaces.stdout.splitlines():
    # Fetch number of transmitted packets from this interface
    packets_tx_command = "ip -s link show dev " + each + " | sed -n 4p | awk -F ' ' '{print $1}'"
    packets_tx = subprocess.run(packets_tx_command, shell=True, check=True, text=True, capture_output=True)

    # Fetch number of received packets from this interface
    packets_rx_command = "ip -s link show dev eth0 | sed -n 6p | awk -F ' ' '{print $1}'"
    packets_rx = subprocess.run(packets_tx_command, shell=True, check=True, text=True, capture_output=True)

    tx_data = packets_tx.stdout.strip()
    rx_data = packets_rx.stdout.strip()

    # Append JSON list
    output[each] = {
        "TX": tx_data,
        "RX": rx_data
    }


json_output = json.dumps(output)


@app.route('/')
def packet_count():
    return json_output


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
