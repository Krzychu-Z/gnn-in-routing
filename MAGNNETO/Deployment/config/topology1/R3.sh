#!/bin/bash
# * R3 router configuration file *

vtysh << EOM
conf t

interface eth0
ip address 10.0.10.3/24
no shutdown

interface eth1
ip address 10.0.5.3/24
no shutdown

interface eth2
ip address 10.0.6.3/24
no shutdown

exit
exit
write
EOM
