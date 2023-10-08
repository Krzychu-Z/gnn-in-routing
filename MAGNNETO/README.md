# MAGNNETO MARL MPNN framework

MAGNNETO is a distributed Multi Agent Reinforcement Learning system
utilizing Message Passing Neural Network (a special type of Graph Neural Network)
in Traffic Engineering in Computer Networking task. It has been published
in IEEExplore in this paper https://ieeexplore.ieee.org/abstract/document/10013773/ 
(Bernárdez, Guillermo, et al. "MAGNNETO: A Graph Neural Network-Based Multi-Agent System for Traffic Engineering." IEEE Transactions on Cognitive Communications and Networking 9.2 (2023): 494-506.).
The owner of this repository is not an author of MAGNNETO nor does he wish to use this code in any other way than to review the aforementioned paper.


## Test environment deployment
Test environment is deployed using Kathara (www.kathara.org) framework in Docker.
Below an instruction on how to set it all up and running has been placed.

### STEP 1. - Build custom kathara images (assuming your Docker does not store any kathara image)
```
$ pwd
.../gnn-in-routing/MAGNNETO/TestEnvironment
$ docker build -t kathara/frr -f Dockerfile.FRR .
$ docker build -t kathara/base -f Dockerfile.Base .
```
### STEP 2. - Run Kathara Lab
```
$ cd topology1
$ kathara lstart
```

### STEP 3. - Watch framework execution in debug mode (currently the only one)
In first terminal window (master PC)
```
$ docker exec -it katha (TAB)
$ docker exec -it kathara_...pc[x] (TAB)
$ docker exec -it kathara_...pc[x]... /bin/bash

(Container name will remain same after restarting)

(Activate venv)
root@pcx:/# . venv/bin/activate
(venv) root@pcx:/# cd shared/

(After you've turned on Hypercorn server on one router in second terminal shell)
(venv) root@pcx:/shared# python3 master.py
```
In second terminal window (RX server debug)
```
$ docker exec -it katha (TAB)
$ docker exec -it kathara_...r[x] (TAB)
$ docker exec -it kathara_...r[x]... /bin/bash

(Container name will remain same after restarting)

(Activate venv)
root@rx:/# . venv/bin/activate

(Kill currently running server instance - twice)
(venv) root@rx:/# netstat -tulpn
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name

tcp        0      0 X.X.X.X:8000            0.0.0.0:*               LISTEN      64/python3

(venv) root@rx:/# kill -9 64

(venv) root@rx:/# netstat -tulpn
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name

tcp        0      0 X.X.X.X:8000            0.0.0.0:*               LISTEN      95/python3

(venv) root@rx:/# kill -9 95

(Verify it no longer runs)
(venv) root@rx:/# netstat -tulpn
Active Internet connections (only servers)
Proto Recv-Q Send-Q Local Address           Foreign Address         State       PID/Program name

(Run Hypercorn server in your terminal window)
(venv) root@rx:/# hypercorn --keyfile shared/certs/key[x].pem --certfile shared/certs/cert[x].pem --bind 'X.X.X.X:8000' shared/api.py:app
```