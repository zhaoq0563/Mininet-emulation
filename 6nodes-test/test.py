#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

import os, time, threading

""" Application related function """

def sendingIperfTraffic(nodes, loc):
    print "*** Starting iPerf Server on host ***"
    server = nodes['h2']
    server.cmd('iperf -s &')
    if not os.path.exists(loc):
        os.mkdir(loc)
        user = os.getenv('SUDO_USER')
        os.system('sudo chown -R '+user+':'+user+' '+loc)
    server.cmd('tcpdump -i h2-eth0 -w '+loc+'/server.pcap &')

    print "*** Starting iPerf Clients on stations ***"
    time.sleep(1)
    client = nodes['h1']
    totalTime = 10
    client.cmdPrint('iperf -c 10.0.0.2 -t '+str(totalTime))

""" Main function of the simulation """

def mobileNet(loc, loss, conges, delay):

    print("*** System configuration ***\n")
    # Configuring the congestion control
    if conges == 'bbr':
        os.system('sudo sysctl -w net.core.default_qdisc=fq')
    else:
        os.system('sudo sysctl -w net.core.default_qdisc=pfifo_fast')
    os.system('sudo sysctl -w net.ipv4.tcp_congestion_control='+conges)

    net = Mininet(controller=Controller, link=TCLink, autoSetMacs=True)

    print("*** Creating nodes ***")
    nodes = {}

    node = net.addHost('h1')
    nodes['h1'] = node
    node = net.addHost('h2')
    nodes['h2'] = node
    node = net.addSwitch('s1')
    nodes['s1'] = node
    node = net.addSwitch('s2')
    nodes['s2'] = node
    node = net.addSwitch('s3')
    nodes['s3'] = node
    node = net.addSwitch('s4')
    nodes['s4'] = node

    net.addLink(nodes['h1'], nodes['s1'])
    net.addLink(nodes['s1'], nodes['s2'])
    net.addLink(nodes['s2'], nodes['s3'], bw=10, delay=str(delay)+'ms', loss=float(loss)*100)
    # net.addLink(nodes['s2'], nodes['s3'], bw=10)
    net.addLink(nodes['s3'], nodes['s4'])
    net.addLink(nodes['s4'], nodes['h2'])

    node = net.addController('c0')
    nodes['c0'] = node

    print("*** Starting network simulation ***")
    net.start()

    print("*** Configuring virtual ports for VMs ***")
    os.system('sudo ip tuntap add mode tap vport1')
    os.system('sudo ip tuntap add mode tap vport2')
    os.system('sudo ifconfig vport1 up')
    os.system('sudo ifconfig vport2 up')
    os.system('sudo ovs-vsctl add-port s1 vport1')
    os.system('sudo ovs-vsctl add-port s4 vport2')

    CLI(net)

    print "*** Starting to generate the traffic ***"
    traffic_thread = threading.Thread(target=sendingIperfTraffic, args=(nodes, loc))
    traffic_thread.start()
    traffic_thread.join()

    print("*** Stopping network ***")
    os.system('sudo ovs-vsctl del-port s1 vport1')
    os.system('sudo ovs-vsctl del-port s4 vport2')
    os.system('sudo ifconfig vport1 down')
    os.system('sudo ifconfig vport2 down')
    os.system('sudo ip link delete vport1')
    os.system('sudo ip link delete vport2')
    net.stop()



if __name__ == '__main__':
    print("*** *** *** *** *** *** *** *** *** *** ***")
    print("***                                     ***")
    print("***  Welcome to the Mininet simulation  ***")
    print("***                                     ***")
    print("*** *** *** *** *** *** *** *** *** *** ***\n")
    while True:
        print("--- Available congestion control: ")
        print("reno\tcubic\tbbr")
        conges = raw_input('--- Please select: ')
        if conges == 'reno' or conges == 'cubic' or conges == 'bbr':
            break

    while True:
        delay = raw_input('--- Please input the delay (ms): ')
        break

    loss = 0.001
    user = os.getenv('SUDO_USER')
    if not os.path.exists('results'):
        os.mkdir('results')
        os.system('sudo chown -R ' + user + ':' + user + ' ' + 'results')
    resLoc = 'results/'+str(loss)+'/'
    if not os.path.exists(resLoc):
        os.mkdir(resLoc)
        os.system('sudo chown -R ' + user + ':' + user + ' ' + resLoc)

    setLogLevel('info')
    mobileNet(resLoc+conges[0:2]+delay, loss, conges, delay)

