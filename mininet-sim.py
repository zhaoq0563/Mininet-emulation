#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import OVSKernelAP
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

from subprocess import call
import time, random, os, json, sys


"""Main function of the simulation"""

def mobileNet(name, mptcpEnabled, fdmEnabled, configFile):

    # call(["sudo", "sysctl", "-w", "net.mptcp.mptcp_enabled="+str(mptcpEnabled)])
    # if not mptcpEnabled:
    #     call(["sudo", "modprobe", "mptcp_coupled"])
    #     call(["sudo", "sysctl", "-w", "net.mptcp.mptcp_scheduler=default"])
    #     call(["sudo", "sysctl", "-w", "net.ipv4.tcp_congestion_control=lia"])

    print "*** Loading the parameters for simulation ***\n"

    mStart = 0
    mEnd = 180
    acMode = 'ssf'
    propModel = 'logDistance'
    exponent = 4
    folderName = 'pcap_'+name

    with open(configFile, 'r') as read_file:
        paras = json.load(read_file)
    sats = paras['SatcomScnDef']['sateDef']
    usrs = paras['SatcomScnDef']['userDef']
    lnks = paras['SatcomScnDef']['scnLinkDef']
    # print sats, usrs, lnks

    net = Mininet(controller=None, accessPoint=OVSKernelAP, link=TCLink, autoSetMacs=True)

    print "*** Creating nodes ***"
    nodes = {}

    node = net.addHost('h1')
    nodes['h1'] = node
    node = net.addSwitch('s1')
    nodes['s1'] = node
    net.addLink(nodes['h1'], nodes['s1'])

    for sat,i in zip(sats,range(1,len(sats)+1)):
        sat_name = 'h'+str(i)
        sat_id = str(sat['satID'])+'-sat'
        print sat_name, sat_id
        swi_name = 's'+str(i)
        swi_id = sat['satID']
        node = net.addHost(sat_name, position=str(50+(5*i))+',50,0')
        nodes[sat_id] = node
        node = net.addSwitch(swi_name)
        nodes[swi_id] = node
        net.addLink(nodes[sat_id], nodes[swi_id])

    for usr,i in zip(usrs,range(len(sats)+1,len(sats)+len(usrs))):
        usr_name = 'h'+str(i)
        usr_id = usr['ID']
        print usr_name, usr_id
        node = net.addHost(usr_name, position=str(50+(30*i))+',150,0')
        nodes[usr_id] = node

    for lnk in lnks:
        src_id = lnk['Config'][0]['srcID']
        des_id = lnk['Config'][1]['destID']
        print src_id, des_id
        node_s = nodes[src_id]
        node_d = nodes[des_id]
        net.addLink(node_s, node_d)

    # '''Switch'''
    # numOfSwitch = numOfAp+numOfLte*2+1                        # last one is for server h1
    # for i in range(1, numOfSwitch+1):
    #     switch_name = 's'+str(i)
    #     node = net.addSwitch(switch_name)
    #     nodes[switch_name] = node
    #     if i>numOfAp+numOfLte and i!=numOfSwitch:
    #         nets.append(switch_name)

    # '''Access Point'''
    # for i in range(1, numOfAp+1):
    #     ap_name = 'ap'+str(i)
    #     ap_ssid = ap_name+'_ssid'
    #     ap_mode = 'g'
    #     ap_chan = '1'
    #     ap_range = '40'

    #     if replay==1:
    #         ap_pos = config.readline().strip('\n')
    #     else:
    #         ap_pos = '100,70,0'
    #         config.write(ap_pos+'\n')

    #     paramOfAp[ap_name] = [ap_pos, ap_range]
    #     node = net.addAccessPoint(ap_name, ssid=ap_ssid, mode=ap_mode, channel=ap_chan, position=ap_pos, range=ap_range)
    #     nets.append(ap_name)
    #     nodes[ap_name] = node

    # print "*** Associating and Creating links ***"
    # '''Backhaul links between switches'''
    # for i in range(1, numOfAp+numOfLte+1):
    #     node_u = nodes['s'+str(numOfSwitch)]
    #     node_d = nodes['s'+str(i)]
    #     net.addLink(node_d, node_u, bw=float(backhaulBW[i-1]), delay=str(backhaulDelay[i-1])+'ms', loss=float(backhaulLoss[i-1]))
    #     capacity['s'+str(i)+'-s'+str(numOfSwitch)] = float(backhaulBW[i-1])
    #     delay['s'+str(i)+'-s'+str(numOfSwitch)] = float(backhaulDelay[i-1])

    # '''Link between server and switch'''
    # node_h = nodes['h1']
    # node_d = nodes['s'+str(numOfSwitch)]
    # net.addLink(node_d, node_h)

    # '''Links between stations and LTE switch'''
    # for i in range(1, numOfSPSta+numOfMPSta+1):
    #     for j in range(numOfAp+numOfLte+1, numOfSwitch):
    #         node_lte = nodes['s'+str(j)]
    #         node_sta = nodes['sta'+str(i)]
    #         if lteLinks[i-1][j-numOfAp-numOfLte-1]:
    #             net.addLink(node_sta, node_lte, bw=float(lteBW), delay=str(lteDelay)+'ms', loss=float(lteLoss))
    #         capacity[node_sta.name+'-'+node_lte.name] = float(lteBW)
    #         delay[node_sta.name+'-'+node_lte.name] = float(lteDelay)


    print "*** Building the graph of the simulation ***"
    net.plotGraph(max_x=260, max_y=220)

    print "*** Starting network simulation ***"
    net.start()

    CLI(net)

    # print "*** Addressing for station ***"
    # for i in range(1, numOfSPSta+numOfMPSta+1):
    #     sta_name = 'sta'+str(i)
    #     station = nodes[sta_name]
    #     for j in range(0, wlanPerSta):
    #         station.cmdPrint('ifconfig '+sta_name+'-wlan'+str(j)+' 10.0.'+str(i+1)+'.'+str(j)+'/32')
    #         station.cmdPrint('ip rule add from 10.0.'+str(i+1)+'.'+str(j)+' table '+str(j+1))
    #         station.cmdPrint('ip route add 10.0.'+str(i+1)+'.'+str(j)+'/32 dev '+sta_name+'-wlan'+str(j)+' scope link table '+str(j+1))
    #         station.cmdPrint('ip route add default via 10.0.'+str(i+1)+'.'+str(j)+' dev '+sta_name+'-wlan'+str(j)+' table '+str(j+1))
    #         if j==0:
    #             station.cmdPrint('ip route add default scope global nexthop via 10.0.'+str(i+1)+'.'+str(j)+' dev '+sta_name+'-wlan'+str(j))
    #     for j in range(wlanPerSta, ethPerSta+wlanPerSta):
    #         station.cmdPrint('ifconfig '+sta_name+'-eth'+str(j)+' 10.0.'+str(i+1)+'.'+str(j)+'/32')
    #         station.cmdPrint('ip rule add from 10.0.'+str(i+1)+'.'+str(j)+' table '+str(j+1))
    #         station.cmdPrint('ip route add 10.0.'+str(i+1)+'.'+str(j)+'/32 dev '+sta_name+'-eth'+str(j)+' scope link table '+str(j+1))
    #         station.cmdPrint('ip route add default via 10.0.'+str(i+1)+'.'+str(j)+' dev '+sta_name+'-eth'+str(j)+' table '+str(j+1))
    #         # if j==1 and i==1:
    #         #     station.cmdPrint('ip route add default scope global nexthop via 10.0.'+str(i+1)+'.'+str(j)+' dev '+sta_name+'-eth'+str(j))


    # print "*** Data processing ***"
    # for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
    #     for j in range(0, wlanPerSta):
    #         ip = '10.0.'+str(i+1)+'.'+str(j)
    #         if mptcpEnabled:
    #             out_f = folderName+'/sta'+str(i)+'-wlan'+str(j)+'_mptcp.stat'
    #         else:
    #             out_f = folderName+'/sta'+str(i)+'-wlan'+str(j)+'_sptcp.stat'
    #         nodes['sta'+str(i)].cmdPrint('sudo tshark -r '+folderName+'/sta'+str(i)+'-wlan'+str(j)+'.pcap -qz \"io,stat,0,BYTES()ip.src=='+ip+',AVG(tcp.analysis.ack_rtt)tcp.analysis.ack_rtt&&ip.addr=='+ip+'\" >'+out_f)
    #     for j in range(wlanPerSta, ethPerSta+wlanPerSta):
    #         ip = '10.0.'+str(i+1)+'.'+str(j)
    #         if mptcpEnabled:
    #             out_f = folderName + '/sta' + str(i) + '-eth' + str(j) + '_mptcp.stat'
    #         else:
    #             out_f = folderName + '/sta' + str(i) + '-eth' + str(j) + '_sptcp.stat'
    #         nodes['sta'+str(i)].cmdPrint('sudo tshark -r '+folderName+'/sta'+str(i)+'-eth'+str(j)+'.pcap -qz \"io,stat,0,BYTES()ip.src=='+ip+',AVG(tcp.analysis.ack_rtt)tcp.analysis.ack_rtt&&ip.addr=='+ip+'\" >'+out_f)

    # if trafficGen == 'd':
    #     os.system('sudo python analysis.py '+(str(range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1))).replace(' ', '')+' '+folderName)

    # throughput_l = []
    # delay_l = []
    # for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
    #     throughput, delay, byte = (0.0, 0.0, 0.0)
    #     if i<=numOfSPSta+numOfMPSta:
    #         for j in range(0, wlanPerSta):
    #             if mptcpEnabled:
    #                 out_f = folderName + '/sta' + str(i) + '-wlan' + str(j) + '_mptcp.stat'
    #             else:
    #                 out_f = folderName + '/sta' + str(i) + '-wlan' + str(j) + '_sptcp.stat'
    #             f = open(out_f, 'r')
    #             for line in f:
    #                 if line.startswith('|'):
    #                     l = line.strip().strip('|').split()
    #                     if '<>' in l:
    #                         duration = float(l[2])
    #                         byte += float(l[8])
    #                         throughput += float(l[8]) * 8 / duration
    #                         delay += float(l[8]) * float(l[10])
    #             f.close()
    #         for j in range(wlanPerSta, ethPerSta + wlanPerSta):
    #             if mptcpEnabled:
    #                 out_f = folderName + '/sta' + str(i) + '-eth' + str(j) + '_mptcp.stat'
    #             else:
    #                 out_f = folderName + '/sta' + str(i) + '-eth' + str(j) + '_sptcp.stat'
    #             f = open(out_f, 'r')
    #             for line in f:
    #                 if line.startswith('|'):
    #                     l = line.strip().strip('|').split()
    #                     if '<>' in l:
    #                         duration = float(l[2])
    #                         byte += float(l[8])
    #                         throughput = throughput + float(l[8]) * 8 / duration if duration else 0
    #                         delay += float(l[8]) * float(l[10])
    #             f.close()
    #         delay = delay / byte if byte else 0
    #         throughput_l.append(str(throughput))
    #         delay_l.append(str(delay))
    #         out_f = folderName + "/sta" + str(i) + '-wireshark.stat'
    #         o = open(out_f, 'w')
    #         o.write("Throughput: " + str(throughput) + "\nDelay: " + str(delay))
    #         o.close()

    # statFile = folderName + '/' + protocol + ".stat"
    # o = open(statFile, 'w')
    # host_l = []
    # for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
    #     host_l.append('sta' + str(i))
    # o.write(','.join(str(i) for i in host_l))
    # o.write('\n')
    # o.write(','.join(str(i) for i in throughput_l))
    # o.write('\n')
    # o.write(','.join(str(i) for i in delay_l))
    # o.close()

    print "*** Stopping network ***"
    net.stop()


if __name__ == '__main__':
    print "*** *** *** *** *** *** *** *** *** *** ***"
    print "***                                     ***"
    print "***  Welcome to the Mininet simulation  ***"
    print "***                                     ***"
    print "*** *** *** *** *** *** *** *** *** *** ***\n"
    while True:
        print "--- Available configuration: "
        for config in os.listdir('./'):
            if '.json' in config:
                print config.rstrip('.json')
        configName = raw_input('--- Please select the configuration file: ')
        print configName+'.json'
        if os.path.exists('./'+configName+'.json'):
            break

    # while True:
    #     fdmEnabled = raw_input('--- Enable FDM? (Default YES): ')
    #     if fdmEnabled == 'no' or fdmEnabled == 'n' or fdmEnabled == '0':
    #         fdmEnabled = 0
    #         break
    #     elif fdmEnabled == 'y' or fdmEnabled == 'yes' or fdmEnabled == '1' or fdmEnabled == '':
    #         fdmEnabled = 1
    #         break

    while True:
        name = raw_input('--- Please name this testing: ')
        break

    setLogLevel('info')

    # if fdmEnabled==0:
    #     mobileNet(name+'-mptcp', 1, 0, 'i', 0, configName + '.json')
    # else:
    #     mobileNet(name+'-fdm', 1, 1, 'i', 0, configName + '.json')

    mobileNet(name, 1, 0, configName + '.json')

