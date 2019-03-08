import scapy, sys
from scapy.all import *
from scapy.utils import PcapReader

packets = rdpcap("./results/pcaps/r2-eth0.pcap")
data = []
for packet in packets:
    if 'TCP' in packet:
    	s = repr(packet)
    	print(s)
    break
    	# data.append([packet['TCP'].seq, packet['TCP'].ack, packet['TCP'].options[2][1][0], packet['TCP'].options[2][1][1]])

# sudo tshark -r /dfd/sta1-eth1.pcap -qz "io,stat,0,BYTES()ip.src==10.0.1.3,AVG(tcp.analysis.ack_rtt)tcp.analysis.ack_rtt&&ip.addr==10.0.1.3" > a.out
# for packet in data:
# 	print packet

# tsvaltmp, tsecrtmp = (0, 0)
# for pkt in packets:
# 	if 'TCP' in pkt:
# 		tsdata=dict(pkt['TCP'].options)
# 		tsvalpkt = tsdata['Timestamp'][0]
# 		tsecrpkt = tsdata['Timestamp'][1]
# 		if tsvaltmp == tsecrpkt:
# 			rtt = tsvalpkt - tsecrtmp
# 			# if rtt != 0:
# 			print rtt
# 		tsvaltmp = tsvalpkt
# 		tsecrtmp = tsecrpkt