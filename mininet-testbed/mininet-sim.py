#!/usr/bin/python

from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel, info

from subprocess import call
import time, datetime, threading, os, json, collections, sys, requests, socket

# SOCK_HOST = '192.168.88.131'
SOCK_HOST = 'localhost'
SOCK_PORT = 65432
DATA_HOST = '192.168.1.3'
#DATA_HOST = 'localhost'
DATA_PORT = '8888'
SOL  = 299792.458

"""Controller function"""

def controllerLogic(net, nodes, tcInfo, actList):

    print("### Controlling logic is running ###\n")
    lastTime = 0
    for acts in actList:
        # Sleeping until the starting point of next series of actions
        time.sleep(float(acts[0])-lastTime)
        # Interpreting the action one by one
        for act in acts[1]:
            # Link action
            if len(act) == 4:
                # Locating the current link info
                curLink = str(act[0])+'->'+str(act[1])

                if act[2] == 'removeLink':
                    del tcInfo[curLink]
                    net.delLinkBetween(nodes[str(act[0])], nodes[str(act[1])])
                else:
                    # Adding corresponding parameters for new link
                    if act[2] == 'establishLink':
                        tcInfo.setdefault(curLink, {})['bw'] = float(act[3].strip('Mbps'))
                    # Changing corresponding parameters of old link
                    else:
                        net.delLinkBetween(nodes[str(act[0])], nodes[str(act[1])])
                        if act[2] == 'throughputChange':
                            tcInfo[curLink]['bw'] = float(act[3].strip('Mbps'))
                        elif act[2] == 'propDelayChange':
                            tcInfo[curLink]['delay'] = act[3]
                    # Adding new link
                    addLinkCmd = 'net.addLink(nodes["'+str(act[0])+'"],nodes["'+str(act[1])+'"],'
                    for k,v in tcInfo[curLink].iteritems():
                        value = "'"+str(v)+"'" if (str(k)=='delay') else str(v)
                        addLinkCmd += str(k)+'='+value+','
                    eval(addLinkCmd.strip(',')+')')

            # App action
            # elif len(act) == 3:

        # Updating last timestamp
        lastTime = float(acts[0])


"""Helper function"""

def initSocket(event):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SOCK_HOST, SOCK_PORT))

    instr = ''
    while instr != event:
        print("*** Waiting for instructions ... ***")
        s.listen(5)
        conn, addr = s.accept()
        # print('Connected by ', addr)
        while True:
            instr = conn.recv(1024)
            if not instr:
                print('Connection lost...')
                break
            if instr == event:
                break
    s.close()


def delayUpdate(snode, dnode, delay):
    links = snode.connectionsTo(dnode)

    srcLink = links[0][1]
    dstLink = links[0][1]

    srcLink.config(**{ 'delay' : str(delay)+'ms' })
    dstLink.config(**{ 'delay' : str(delay)+'ms' })


def linkUpdate(net, nodes, links, app, event, evts, protocol):
    #print "stage updating link delays ---------------\n\n"
	# Update links
    path = json.loads(event['path'])['pathById']
    dist = json.loads(event['distance'])
    sumDelay = 0.0
    for i in range(len(path)-1):
        snode = nodes[str(path[i])+'-swi']
        dnode = nodes[str(path[i+1])+'-swi']
        delay = float(dist[i]) / SOL
        sumDelay += delay
        #print path[i]+'-swi' + '    ---->>     ' + path[i+1]+'-swi'+'  -----with delay: '+str(delay)+'\n'
        # net.addLink(snode, dnode, bw=100, delay=str(delay)+'ms')
        delayUpdate(snode, dnode, delay)
        # links.append((str(path[i])+'-swi', str(path[i+1])+'-swi'))

	# Update event detail for emulation
	evt_detail = {}
    evt_detail['app'] = app
    evt_detail['src'] = str(path[0])
    evt_detail['dst'] = str(path[-1])
    evt_detail['prc'] = str(protocol)
    evt_detail['tra'] = int(event['datavol'])
    evt_detail['fak'] = int(event['throughput'])
    evt_detail['tim'] = str(event['timetick'])
    evt_detail['dly'] = float(sumDelay)
    evts.append(evt_detail)


def linkEval(net, nodes, evts, t):
    #print "stage evaluating links ---------------\n\n"
    for index, evt in enumerate(evts):
        snode = nodes[evt['src']+'-host']
        dnode = nodes[evt['dst']+'-host']
        dnode.cmdPrint('iperf -s > output_'+str(index)+' &') if evt['prc']=='TCP' else dnode.cmdPrint('iperf -u -s > output_'+str(index)+' &')
        dnode.cmd('pid_'+str(index)+'=$!')
        dstIp = dnode.IP()
        snode.cmdPrint('iperf -c '+dstIp+' -n '+str(evt['tra'])+'M &') if evt['prc']=='TCP' else snode.cmdPrint('iperf -c '+dstIp+' -u -b 100M -n '+str(evt['tra'])+'M > /dev/null 2>&1 &')
    time.sleep(15)
    for index, evt in enumerate(evts):
        dnode = nodes[evt['dst']+'-host']
        dnode.cmd('kill -9 $pid_'+str(index))
    print "stage sending results back ---------------\n\n"
    for index, evt in enumerate(evts):
        # grab the results
        res             = {}
        res['app']      = evt['app']
        res['time']     = str(t)
        res['tput']     = evt['fak']
        res['pdelay']   = evt['dly']
        f = open('output_'+str(index), 'r')
        for line in f:
            if 'MBytes' in line.split():
                resStr = line.split()
                for index, item in enumerate(resStr):
                    if item == 'sec':
                        res['applicationDelay'] = float(resStr[index-1][4:]) if '0.0-' in resStr[index-1] else float(resStr[index-1])
                    if item == 'Mbits/sec':
                        res['goodput'] = float(resStr[index-1])
        f.close()
        print 'send the res of '+res['app']+' at time '+res['time']+'------------- '+str(res['goodput'])+' '+str(res['applicationDelay'])+' '+str(res['tput'])+' '+str(res['pdelay'])+'\n'
        headers  = {'Content-Type': 'application/json'}
        response = requests.post(url=' http://'+DATA_HOST+':'+DATA_PORT+'/api/mininet/update', headers=headers, data=json.dumps(res))
        res.clear()


"""Main function of the emulation"""

def mobileNet(name, configFile):

    initSocket('s')

    print("*** Starting to initialize the emulation topology ***")
    topos = requests.get('http://'+DATA_HOST+':'+DATA_PORT+'/api/settings/init')
    if topos.status_code != 200:
        # This means something went wrong.
        raise ApiError('GET /tasks/ {}'.format(topos.status_code))
    sats = topos.json()['satellites']
    bass = topos.json()['basestations']

    print sats
    print bass

    # print("*** Loading the parameters for emulation ***\n")
    # Parsing the JSON file
    # with open(configFile, 'r') as read_file:
    #     paras = json.load(read_file)
    # sats = paras['SatcomScnDef']['sateDef']
    # usrs = paras['SatcomScnDef']['userDef']
    # lnks = paras['SatcomScnDef']['scnLinkDef']

    # # Initializing the Mininet network
    net = Mininet(controller=Controller, link=TCLink, autoSetMacs=True)

    print("*** Creating nodes ***")
    # Storing all nodes objects
    nodes = {}
    # Storing all links information
    links = []

    # Creating satellite nodes: each satellite is constructed with one host and one switch
    for sat,i in zip(sats,range(1,len(sats)+1)):
        sat_name = 'h'+str(i)
        # Satellite host
        sat_id = str(sat['satID'])+'-host'
        print(sat_name, sat_id)
        swi_name = 's'+str(i)
        # Satellite switch
        swi_id = str(sat['satID'])+'-swi'
        node = net.addHost(sat_name, position=str(50+(5*i))+',50,0')
        nodes[sat_id] = node
        node = net.addSwitch(swi_name)
        nodes[swi_id] = node
        net.addLink(nodes[sat_id], nodes[swi_id])

    # Creating base station nodes: each base station is constructed with one host and one switch
    for bas,i in zip(bass,range(len(sats)+1,len(sats)+len(bass)+1)):
        bas_name = 'h'+str(i)
        # Base station host
        bas_id = str(bas['id'])+'-host'
        print(bas_name, bas_id)
        swi_name = 's'+str(i)
        # Base station switch
        swi_id = str(bas['id'])+'-swi'
        node = net.addHost(bas_name, position=str(50+(30*i))+',150,0')
        nodes[bas_id] = node
        node = net.addSwitch(swi_name)
        nodes[swi_id] = node
        net.addLink(nodes[bas_id], nodes[swi_id])

    # # Creating links
    # for lnk in lnks:
    #     src_id = str(lnk['Config'][0]['srcType'])+str(lnk['Config'][0]['srcID'])
    #     des_id = str(lnk['Config'][1]['destType'])+str(lnk['Config'][1]['destID'])
    #     print(src_id, des_id)
    #     node_s = nodes[src_id]
    #     node_d = nodes[des_id]
    #     net.addLink(node_s, node_d, bw=100)
    #     tcInfo.setdefault(src_id+'->'+des_id, {})
    #     break

    # Creating default controller to the network
    node = net.addController('c0')
    nodes['c0'] = node

    # print("*** Loading event into Controller ***")
    # # Parsing the JSON file
    # with open('configs/gpsSCNSimulationscripv2t.json', 'r') as read_file:
    #     events = json.load(read_file)
    # linkEvents = events['SimScript']['scnLinkEvnt']
    # appEvents = events['SimScript']['scnappEvnt']
    # # Storing all the events info
    # actList = {}
    # # Link event: format [time, [source, destination, event type, parameter]]
    # for evt in linkEvents:
    #     for act in evt['actionlist']:
    #         actList.setdefault(str(act['Time']), []).append([str(evt['srcType'])+str(evt['srcID']), str(evt['destType'])+str(evt['destID']), str(act['Type']), str(act['para1'])])
    # # Application event: format [time, [application name, event type, parameter]]
    # for evt in appEvents:
    #     for act in evt['actionlist']:
    #         actList.setdefault(str(act['Time']), []).append([str(evt['AppName']), str(act['Type']), str(act['para1'])])
    # # Sorting the event list based on the timestamp
    # actList = sorted(actList.items(), key=lambda x:float(x[0]))
    # print actList

    initSocket('e')

    # Temp implementation for getting the topology once for all
    events = requests.get('http://'+DATA_HOST+':'+DATA_PORT+'/api/data/applications')
    if events.status_code != 200:
        # This means something went wrong
        raise ApiError('GET /tasks/ {}'.format(events.status_code))
    for app in events.json():
        tpath = json.loads(app['events'][0]['path'])['pathById']
        tdist = json.loads(app['events'][0]['distance'])
        for i in range(len(tpath)-1):
            snode = nodes[str(tpath[i])+'-swi']
            dnode = nodes[str(tpath[i+1])+'-swi']
            key   = (str(tpath[i])+'-swi', str(tpath[i+1])+'-swi')
            delay = float(tdist[i]) / SOL
            print tpath[i]+'-swi' + '    ---->>     ' + tpath[i+1]+'-swi'+'  ----- with delay: '+str(delay)
            if key not in links and key[::-1] not in links:
                net.addLink(snode, dnode, bw=100, delay=str(delay)+'ms')
                links.append(key)

    print("*** Starting network emulation ***")
    # Starting the Mininet emulation network
    net.start()

    # # Creating and starting the controller logic thread
    # control_thread = threading.Thread(target=controllerLogic,args=(net, nodes, tcInfo, actList))
    # control_thread.start()
    # control_thread.join()

    # CLI(net)

    print("*** Loading the events for emulation ***\n")
    events = requests.get('http://'+DATA_HOST+':'+DATA_PORT+'/api/data/applications')
    if events.status_code != 200:
        # This means something went wrong
        raise ApiError('GET /tasks/ {}'.format(events.status_code))
    apps = events.json()
    evts_tracker = [0 for _ in range(len(apps))]
    stime = datetime.datetime.strptime(sorted(apps, key=lambda e:e['startTime'])[0]['startTime'], '%Y-%m-%d %H:%M:%S.%f')
    etime = datetime.datetime.strptime(sorted(apps, key=lambda e:e['endTime'])[-1]['endTime'], '%Y-%m-%d %H:%M:%S.%f')

    while stime < etime:
    	evts = []
    	for evt, app in enumerate(apps):
            for index, event in enumerate(app['events'][evts_tracker[evt]:]):
                curtime = datetime.datetime.strptime(event['timetick'], '%Y-%m-%dT%H:%M:%S.%f')
                if stime >= curtime and stime <= (curtime+datetime.timedelta(seconds=15)):
                    linkUpdate(net, nodes, links, str(app['appName']), event, evts, app['protocol'])
                    evts_tracker[evt] += (index+1)
                    break
        control_thread = threading.Thread(target=linkEval,args=(net, nodes, evts, stime))
        control_thread.start()
        control_thread.join()
        stime += datetime.timedelta(seconds=15)
        # for l in links:
        #     net.delLinkBetween(nodes[l[0]], nodes[l[1]]) 
        # links[:] = []
  

    # CLI(net)
    # time.sleep(5)
    # nodes['38833-sat'].cmdPrint('iperf -s &')
    # nodes['39533-sat'].cmdPrint('iperf -c 10.0.0.22 -t 10')
    # time.sleep(15)

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

    print("*** Stopping network ***")
    os.system('rm -rf output_*')
    net.stop()


if __name__ == '__main__':
    print("\n*** *** *** *** *** *** *** *** *** *** ***")
    print("***                                     ***")
    print("***  Welcome to the Mininet simulation  ***")
    print("***                                     ***")
    print("*** *** *** *** *** *** *** *** *** *** ***\n")
    # while True:
    #     print("--- Available configuration: ")
    #     for config in os.listdir('./configs/'):
    #         if '.json' in config:
    #             print(config.rstrip('.json'))
    #     configName = raw_input('--- Please select the configuration file: ')
    #     print(configName+'.json')
    #     if os.path.exists('./configs/'+configName+'.json'):
    #         break

    # while True:
    #     name = raw_input('--- Please name this testing: ')
    #     break

    setLogLevel('info')

    # mobileNet(name, 'configs/'+configName+'.json')
    mobileNet('test', 'configs/sample.json')

