from quart import Quart, request
import utilisation
from agent import Agent
import json

app = Quart(__name__)
agent_list = []


@app.get('/api/linkUtilisation')
def packet_count_api():
    return utilisation.link_utilisation()


@app.post('/api/trafficMatrix')
async def receive_tm():
    data = await request.get_json()

    interfaces = utilisation.get_interfaces()

    for each in interfaces.stdout.splitlines():
        matrix = data['matrix']
        edges = data['edges']
        link_agent = Agent(matrix, edges, each)
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
        void[each.interface] = "successful"

    return void


@app.get('/api/getReadouts')
def get_readouts():
    output = {}
    for each in agent_list:
        record = each.readout()
        output[each.interface] = record.tolist()

    return output


@app.get('/api/votingEndpoint')
def test():
    for each in agent_list:
        each.voting_function()


if __name__ == '__main__':
    app.run(port=8000, certfile='cert.pem', keyfile='key.pem')
