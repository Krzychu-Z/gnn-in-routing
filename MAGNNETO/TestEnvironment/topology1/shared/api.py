from flask import Flask, request
import packets
from agent import Agent
import json

app = Flask(__name__)
agent_list = []


@app.get('/api/packets')
def packet_count_api():
    return packets.packet_counter()


@app.post('/api/trafficMatrix')
def receive_tm():
    data = request.get_json()
    interfaces = packets.get_interfaces()

    for each in interfaces.stdout.splitlines():
        link_agent = Agent(data['matrix'], data['edges'], each)
        agent_list.append(link_agent)

    response_data = {'message': 'Traffic matrix received successfully'}

    return json.dumps(response_data)


@app.get('/api/getHiddenStates')
def get_hidden_states():
    # API gets request from src=N router
    request_router_nr = request.args.get('src')
    output = {}
    for each in agent_list:
        # If agent link has a destination in requesting router - exclude this link
        if int(request_router_nr) != int(each.dst_router_nr):
            output[each.interface] = each.hidden_state.tolist()

    return output


@app.get('/api/messagePass')
def mp():
    void = {}
    for each in agent_list:
        each.message_passing()

    return void


@app.get('/api/getReadouts')
def get_readouts():
    output = {}
    for each in agent_list:
        record = each.readout()
        output[each.interface] = record

    return output


@app.get('/api/testEndpoint')
def test():
    for each in agent_list:
        print("Voting from this agent: " + str(each.interface))
        print(each.voting_function())


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
