from quart import Quart, request
import utilisation
from agent import Agent
import json

app = Quart(__name__)
agent_list = []

# Initialise agents per bidirectional link
interfaces = utilisation.get_interfaces()

for each in interfaces.stdout.splitlines():
    link_agent = Agent(each)
    agent_list.append(link_agent)

# Agent initialisation switch
first_run = True


@app.get('/api/linkUtilisation')
def packet_count_api():
    return utilisation.link_utilisation()


@app.post('/api/updateAgent')
async def receive_tm():
    global first_run
    data = await request.get_json()

    for agent in agent_list:
        matrix = data['matrix']
        agent.set_traffic_matrix(matrix)
        if first_run:
            edges = data['edges']
            agent.set_edge_list(edges)
            agent.set_destination_router()
            agent.set_initial_hidden_state()
            agent.initialise_mpnn()

    response_data = {'message': 'Traffic matrix updated successfully'}
    first_run = False

    return json.dumps(response_data)


@app.get('/api/getHiddenStates')
def get_hidden_states():
    # API gets request from src=N router
    request_router_nr = request.args.get('src')
    output = {}
    for each_agent in agent_list:
        # If agent link has a destination in requesting router - exclude this link
        if int(request_router_nr) != int(each_agent.dst_router_nr):
            output[each_agent.interface] = each_agent.hidden_state.tolist()

    return output


@app.get('/api/getEdges')
def edge_list():
    # Edge list is common for each agent
    return agent_list[0].edges


@app.get('/api/messagePass')
def mp():
    void = {}
    for each_worker in agent_list:
        each_worker.message_pass()
        void[each_worker.interface] = "successful"

    return void


@app.get('/api/updateHiddenStates')
def new_h_state():
    void = {}
    for each_new_state in agent_list:
        each_new_state.update_hidden_state()
        void[each_new_state.interface] = "successful"

    return void


@app.get('/api/getReadouts')
def get_readouts():
    output = {}
    for each_agent_readout in agent_list:
        record = each_agent_readout.readout()
        output[each_agent_readout.interface] = record.tolist()

    return output


@app.get('/api/votingEndpoint')
def vote():
    decision = []
    for each_voter in agent_list:
        decision.append(each_voter.voting_function().tolist())

    # Check if all arrays are the same (same values on the same places)
    for inner_index in range(len(decision[0])):
        column_sum = 0

        for outer_index in range(len(decision) - 1):
            column_sum += decision[outer_index][inner_index]

        # Linear combination trick: n_1 + n_2 + n_3 + ... + n_(k - 1) - (k - 1)*n_k = 0
        column_sum -= (len(decision) - 1) * decision[len(decision) - 1][inner_index]

        if column_sum != 0:
            return 200

    # Up to this point decision array should contain the same arrays
    return decision[0]


if __name__ == '__main__':
    app.run(port=8000, certfile='cert.pem', keyfile='key.pem')
