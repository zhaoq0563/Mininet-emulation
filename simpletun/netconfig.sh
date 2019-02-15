#!/bin/bash

if [ $# -lt 3 ];then
	echo "Usage: $0 [set | clear] [interface name] [ip-addr/mask]"
	exit 1
fi

if [ "$1" == "set" ];then
    sudo ip tuntap add mode tun $2
    sudo ifconfig $2 up
    sudo ip addr add $3 dev $2
elif [ "$1" == "clear" ];then
    sudo ip addr del $3 dev $2
    sudo ifconfig $2 down
    sudo ip tuntap del mode tun $2
else
    echo "Must give an operation: set or clear!"
fi

