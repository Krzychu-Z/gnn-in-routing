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