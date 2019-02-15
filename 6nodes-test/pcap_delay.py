import scapy, sys
from scapy.all import *
from scapy.utils import PcapReader

packets = rdpcap("./results/pcaps/r1-eth1.pcap")
# data = []
# for packet in packets:
#     if 'TCP' in packet:
#     	# s = repr(packet)
#     	data.append([packet['TCP'].seq, packet['TCP'].ack, packet['TCP'].options[2][1][0], packet['TCP'].options[2][1][1]])

# for packet in data:
# 	print packet
tsvaltmp, tsecrtmp = (0, 0)
for pkt in packets:
	if 'TCP' in pkt:
		tsdata=dict(pkt['TCP'].options)
		tsvalpkt = tsdata['Timestamp'][0]
		tsecrpkt = tsdata['Timestamp'][1]
		if tsvaltmp == tsecrpkt:
			rtt = tsvalpkt - tsecrtmp
			# if rtt != 0:
			print rtt
		tsvaltmp = tsvalpkt
		tsecrtmp = tsecrpkt