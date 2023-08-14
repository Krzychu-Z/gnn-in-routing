from flask import Flask, request
import packets
from ml.agent import Agent
import json

app = Flask(__name__)


@app.get('/api/packets')
def packet_count_api():
    return packets.packet_counter()


@app.post('/api/trafficMatrix')
def receive_tm():
    data = request.get_json()
    link_agent = Agent(data['matrix'], data['edges'], "eth0")
    error = link_agent.set_initial_local_state()
    if error == 255:
        print("Interface couldn't be mapped to a destination router!")
    else:
        print(link_agent.local_state)
    response_data = {'message': 'Traffic matrix received successfully'}
    return json.dumps(response_data), 200


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
