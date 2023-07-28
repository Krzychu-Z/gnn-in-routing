#!/bin/bash
# * R4 router configuration file *

vtysh << EOM
conf t

interface eth0
ip address 10.0.3.4/24
no shutdown

interface eth1
ip address 10.0.4.4/24
no shutdown

interface eth2
ip address 10.0.8.4/24
no shutdown

exit
exit
write
EOM
