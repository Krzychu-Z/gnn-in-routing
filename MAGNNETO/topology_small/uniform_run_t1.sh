#!/bin/bash

kathara exec pc1 'bash ./shared/uniform_storm_t1.sh' &
kathara exec pc2 'bash ./shared/uniform_storm_t1.sh' &
kathara exec pc3 'bash ./shared/uniform_storm_t1.sh' &
kathara exec pc4 'bash ./shared/uniform_storm_t1.sh' &
kathara exec pc5 'bash ./shared/uniform_storm_t1.sh'
