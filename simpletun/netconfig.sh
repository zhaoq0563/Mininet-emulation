#!/bin/bash

name="tunt2"
ipaddr="192.168.0.4/24"


if [ "$1" == "set" ];then
        sudo ip tuntap add mode tun $name
        sudo ifconfig $name up
        sudo ip addr add $ipaddr dev $name
elif [ "$1" == "clear" ];then
        sudo ip addr del $ipaddr dev $name
        sudo ifconfig $name down
        sudo ip tuntap del mode tun $name
else
        echo "Must give an operation: set or clear!"
fi

