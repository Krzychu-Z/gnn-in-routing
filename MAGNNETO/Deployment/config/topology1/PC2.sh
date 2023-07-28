#!/bin/bash
# * PC2 configuration file *

vtysh << EOM
conf t
interface eth0
ip address 10.0.9.254/24
no shutdown
exit
exit
write
EOM
