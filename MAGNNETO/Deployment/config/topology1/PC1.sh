#!/bin/bash
# * PC1 configuration file *

vtysh << EOM
conf t
interface eth0
ip address 10.0.1.254/24
no shutdown
exit
exit
write
EOM
