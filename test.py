#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

from subprocess import call
import time, os, json


"""Main function of the simulation"""

def mobileNet(name, configFile):

    print("*** Loading the parameters for simulation ***\n")

    # with open(configFile, 'r') as read_file:
    #     paras = json.load(read_file)
    # sats = paras['SatcomScnDef']['sateDef']
    # usrs = paras['SatcomScnDef']['userDef']
    # lnks = paras['SatcomScnDef']['scnLinkDef']

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
    net.addLink(nodes['s2'], nodes['s3'])
    net.addLink(nodes['s3'], nodes['s4'])
    net.addLink(nodes['s4'], nodes['h2'])


    # for sat,i in zip(sats,range(1,len(sats)+1)):
    #     sat_name = 'h'+str(i)
    #     sat_id = str(sat['satID'])+'-sat'
    #     print(sat_name, sat_id)
    #     swi_name = 's'+str(i)
    #     swi_id = sat['satID']
    #     node = net.addHost(sat_name, position=str(50+(5*i))+',50,0')
    #     nodes[sat_id] = node
    #     node = net.addSwitch(swi_name)
    #     nodes[swi_id] = node
    #     net.addLink(nodes[sat_id], nodes[swi_id])
    #
    # for usr,i in zip(usrs,range(len(sats)+1,len(sats)+len(usrs))):
    #     usr_name = 'h'+str(i)
    #     usr_id = str(usr['ID'])+'-usr'
    #     print(usr_name, usr_id)
    #     swi_name = 's' + str(i)
    #     swi_id = usr['ID']
    #     node = net.addHost(usr_name, position=str(50+(30*i))+',150,0')
    #     nodes[usr_id] = node
    #     node = net.addSwitch(swi_name)
    #     nodes[swi_id] = node
    #     net.addLink(nodes[usr_id], nodes[swi_id])
    #
    # for lnk in lnks:
    #     src_id = lnk['Config'][0]['srcID']
    #     des_id = lnk['Config'][1]['destID']
    #     print(src_id, des_id)
    #     node_s = nodes[src_id]
    #     node_d = nodes[des_id]
    #     net.addLink(node_s, node_d)

    node = net.addController('c0')
    nodes['c0'] = node

    print("*** Starting network simulation ***")
    net.start()

    CLI(net)

    print("*** Stopping network ***")
    net.stop()


if __name__ == '__main__':
    print("*** *** *** *** *** *** *** *** *** *** ***")
    print("***                                     ***")
    print("***  Welcome to the Mininet simulation  ***")
    print("***                                     ***")
    print("*** *** *** *** *** *** *** *** *** *** ***\n")
    while True:
        print("--- Available configuration: ")
        for config in os.listdir('./'):
            if '.json' in config:
                print(config.rstrip('.json'))
        configName = raw_input('--- Please select the configuration file: ')
        print(configName+'.json')
        if os.path.exists('./'+configName+'.json'):
            break

    while True:
        name = raw_input('--- Please name this testing: ')
        break

    setLogLevel('info')

    mobileNet(name, configName + '.json')

