#!/bin/bash
# * R2 router configuration file *

vtysh << EOM
conf t

interface eth0
ip address 10.0.2.2/24
no shutdown

interface eth1
ip address 10.0.7.2/24
no shutdown

interface eth2
ip address 10.0.3.2/24
no shutdown

exit
exit
write
EOM
