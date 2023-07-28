#!/bin/bash
# * R5 router configuration file *

vtysh << EOM
conf t

interface eth0
ip address 10.0.9.5/24
no shutdown

interface eth1
ip address 10.0.8.5/24
no shutdown

interface eth2
ip address 10.0.6.5/24
no shutdown

exit
exit
write
EOM
