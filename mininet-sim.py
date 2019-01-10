#!/usr/bin/python

# from mininet.fdm_intf_handoff import FDM
# from mininet.net import Mininet
# from mininet.node import OVSKernelAP
# from mininet.link import TCLink
# from mininet.cli import CLI
# from mininet.log import setLogLevel, info

from subprocess import call
import time, random, os, json, sys

"""Traffic generator related functions"""

def sendingDITGTraffic(nodes, folderName, numOfSPSta, numOfMPSta, numOfFixApSta, numOfFixLteSta, demand, mEnd, MPStaSet, ethPerSta, wlanPerSta):
    print "*** Starting D-ITG Server on host ***"
    host = nodes['h1']
    info('Starting D-ITG server...\n')
    host.cmd('pushd ~/D-ITG-2.8.1-r1023/bin')
    host.cmd('./ITGRecv &')
    host.cmd('PID=$!')
    host.cmd('popd')
    if not os.path.exists(folderName):
        os.mkdir(folderName)
        user = os.getenv('SUDO_USER')
        os.system('sudo chown -R ' + user + ':' + user + ' ' + folderName)
    host.cmd('tcpdump -i h1-eth0 -w ' + folderName + '/h1.pcap &')

    print "*** Starting D-ITG Clients on stations ***"
    info('Starting D-ITG clients...\n')
    time.sleep(1)
    for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
        sender = nodes['sta'+str(i)]
        receiver = nodes['h'+str(1)]
        bwReq = demand['sta'+str(i)]*250
        ITGTest(sender, receiver, bwReq, (mEnd-1)*1000)
        if i<=numOfSPSta+numOfMPSta and i in MPStaSet:
            for j in range(0, wlanPerSta):
                sender.cmd('tcpdump -i sta'+str(i)+'-wlan'+str(j)+' -w '+folderName+'/sta'+str(i)+'-wlan'+str(j)+'.pcap &')
            for j in range(wlanPerSta, ethPerSta+wlanPerSta):
                sender.cmd('tcpdump -i sta'+str(i)+'-eth'+str(j)+' -w '+folderName+'/sta'+str(i)+'-eth'+str(j)+'.pcap &')
        elif i<=numOfSPSta+numOfMPSta+numOfFixApSta:
            sender.cmd('tcpdump -i sta'+str(i)+'-wlan0 -w '+folderName+'/sta'+str(i)+'-wlan0.pcap &')
        else:
            sender.cmd('tcpdump -i sta'+str(i)+'-eth1 -w '+folderName+'/sta'+str(i)+'-eth1.pcap &')


def setupIperfServer(nodes, folderName, numOfSPSta, numOfMPSta, numOfFixApSta, numOfFixLteSta):
    """Set up iPerf3 Server on host."""
    print "*** Starting iPerf3 Server on host ***"
    host = nodes['h1']
    info("Starting iPerf3 server...\n")
    base_port = 5502
    for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
        host.cmd('iperf3 -s -p ' + str(base_port+i) + ' &')
    if not os.path.exists(folderName):
        os.mkdir(folderName)
        user = os.getenv('SUDO_USER')
        os.system('sudo chown -R '+user+':'+user+' '+folderName)
    host.cmd('tcpdump -i h1-eth0 -w '+folderName+'/h1.pcap &')
    return base_port


def startClientTrafficMonitoring(nodes, folderName, numOfSPSta, numOfMPSta, numOfFixApSta, numOfFixLteSta, ethPerSta, wlanPerSta):
    """Start traffic montioring of clients."""
    print "*** Starting tcpdump for each client ***"
    info("Starting tcpdump for each client...\n")
    for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
        sender = nodes['sta'+str(i)]
        if i <= numOfSPSta+numOfMPSta:
            for j in range(0, wlanPerSta):
                sender.cmd('tcpdump -i sta'+str(i)+'-wlan'+str(j)+' -w '+folderName+'/sta'+str(i)+'-wlan'+str(j)+'.pcap &')
            for j in range(wlanPerSta, ethPerSta+wlanPerSta):
                sender.cmd('tcpdump -i sta'+str(i)+'-eth'+str(j)+' -w '+folderName+'/sta'+str(i)+'-eth'+str(j)+'.pcap &')


def startIperfClients(nodes, numOfSPSta, numOfMPSta, numOfFixApSta, numOfFixLteSta, demand, mEnd, base_port):
    """Set up iPerf3 Clients on stations."""
    print "*** Starting iPerf3 Clients on stations ***"
    info('Starting iPerf3 clients...\n')
    for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
        sender = nodes['sta'+str(i)]
        receiver = nodes['h1']
        bwReq = demand['sta'+str(i)]
        iperf3Test(sender, receiver, bwReq, mEnd, base_port+i)


def sendingIperfTraffic(nodes, folderName, numOfSPSta, numOfMPSta, numOfFixApSta, numOfFixLteSta, demand, mEnd, ethPerSta, wlanPerSta):
    """Send traffic via iPerf3 traffic generator."""
    print "*** Starting iPerf3 Server on host ***"
    host = nodes['h1']
    info('Starting iPerf3 server...\n')
    base_port = 5502
    for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
        host.cmd('iperf3 -s -p ' + str(base_port+i) + ' &')
    if not os.path.exists(folderName):
        os.mkdir(folderName)
        user = os.getenv('SUDO_USER')
        os.system('sudo chown -R '+user+':'+user+' '+folderName)
    host.cmd('tcpdump -i h1-eth0 -w '+folderName+'/h1.pcap &')

    print "*** Starting iPerf3 Clients on stations ***"
    info('Starting iPerf3 clients...\n')
    time.sleep(5)
    for i in range(1, numOfSPSta+numOfMPSta+numOfFixApSta+numOfFixLteSta+1):
        sender = nodes['sta'+str(i)]
        receiver = nodes['h1']
        bwReq = demand['sta'+str(i)]
        iperf3Test(sender, receiver, bwReq, mEnd, base_port+i)
        if i<=numOfSPSta+numOfMPSta:
            for j in range(0, wlanPerSta):
                sender.cmd('tcpdump -i sta'+str(i)+'-wlan'+str(j)+' -w '+folderName+'/sta'+str(i)+'-wlan'+str(j)+'.pcap &')
            for j in range(wlanPerSta, ethPerSta+wlanPerSta):
                sender.cmd('tcpdump -i sta'+str(i)+'-eth'+str(j)+' -w '+folderName+'/sta'+str(i)+'-eth'+str(j)+'.pcap &')


def ITGTest(client, server, bw, sTime):
    info('Sending message from ', client.name, '<->', server.name, '\n')
    client.cmd('pushd ~/D-ITG-2.8.1-r1023/bin')
    client.cmdPrint('./ITGSend -T TCP -a 10.0.0.1 -c 500 -m rttm -O '+str(bw)+' -t '+str(sTime)+' -l log/'+str(client.name)+'.log -x log/'+str(client.name)+'-'+str(server.name)+'.log &')
    client.cmd('PID_'+client.name+'=$!')
    client.cmd('popd')


def iperf3Test(client, server, bw, sTime, port):
    info('Sending iperf3 from ', client.name, '<->', server.name, '\n')
    client.cmdPrint('iperf3 -c 10.0.0.1 -b ' + str(bw) + 'M -p '+str(port)+' -t '+str(sTime)+' &')
    client.cmdPrint('PID_'+client.name+'=$!')


"""Main function of the simulation"""

def mobileNet(name, mptcpEnabled, fdmEnabled, replay, configFile):

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

    # node = net.addHost('h1', ip='10.0.0.1')
    # nodes['h1'] = node

    for sat,i in zip(sats,range(1,len(sats)+1)):
        sta_name = 'sta'+str(i)
        sat_id = sat['satID']
        print sta_name, sat_id
        node = net.addStation(sta_name, position=str(50+(5*i))+',50,0')
        nodes[sat_id] = node

    for usr,i in zip(usrs,range(len(sats)+1,len(sats)+len(usrs))):
        sta_name = 'sta'+str(i)
        usr_id = usr['ID']
        print sta_name, usr_id
        node = net.addStation(sta_name, position=str(50+(30*i))+',150,0')
        nodes[usr_id] = node

    for lnk in lnks:
        src_id = lnk['Config'][0]['srcID']
        des_id = lnk['Config'][1]['destID']
        print src_id, des_id
        node_s = nodes[src_id]
        node_d = nodes[des_id]
        net.addLink(node_s, node_d)

    time.sleep(50)

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

    print "*** Configuring propagation model ***"
    net.propagationModel(model=propModel, exp=exponent)

    print "*** Configuring wifi nodes ***"
    net.configureWifiNodes()

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

    # setLogLevel('info')

    # if fdmEnabled==0:
    #     mobileNet(name+'-mptcp', 1, 0, 'i', 0, configName + '.json')
    # else:
    #     mobileNet(name+'-fdm', 1, 1, 'i', 0, configName + '.json')

    mobileNet(name, 1, 0, 0, configName + '.json')

