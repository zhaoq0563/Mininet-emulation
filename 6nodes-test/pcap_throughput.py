#!/usr/bin/python

import os

cur_path = 'results/0.0001/'
for i in os.listdir(cur_path):
    pcap_file = cur_path+i+'/server.pcap'
    out_file = cur_path+i+'/res.stat'
    os.system('tshark -r ' + pcap_file + ' -qz \"io,stat,0,BYTES()ip.src==10.0.0.1,AVG(tcp.analysis.ack_rtt)tcp.analysis.ack_rtt&&ip.addr==10.0.0.1\" >' + out_file)
    f = open(out_file, 'r')
    for line in f:
        if line.startswith('|'):
            l = line.strip().strip('|').split()
            if '<>' in l:
                duration = float(l[2])
                byte = float(l[4])
                throughput = byte * 8 / duration
                delay = float(l[6])
    f.close()
    f = open(out_file, 'a')
    f.write('\n\n'+str(throughput/1000000)+'\n\n'+str(delay))
    f.close()
    print i+"\t"+str(throughput/1000000)

