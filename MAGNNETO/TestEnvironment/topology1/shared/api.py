from flask import Flask, request
import packets
import json

app = Flask(__name__)


@app.get('/api/packets')
def packet_count_api():
    return packets.packet_counter()


@app.post('/api/trafficMatrix')
def receive_tm():
    data = request.get_json()
    print(data)
    response_data = {'message': 'Traffic matrix received successfully'}
    return json.dumps(response_data), 200


if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=8000)
