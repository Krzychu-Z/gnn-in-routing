#!/bin/bash
# * R1 router configuration file *

vtysh << EOM
conf t

interface eth0
ip address 10.0.1.1/24
no shutdown

interface eth1
ip address 10.0.2.1/24
no shutdown

interface eth2
ip address 10.0.4.1/24
no shutdown

interface eth3
ip address 10.0.5.1/24
no shutdown

exit
exit
write
EOM
