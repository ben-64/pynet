#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
import time
import socket

from pynet.module import Module
from pynet.modules.Logger import Logger

@Module.register
class Pcap(Logger):
    _desc_ = "Pcap Module"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--pcap","-p",metavar="PCAP",default="out.pcap",help="Pcap file to write")
        parser.add_argument("--link","-l",metavar="LINK_TYPE",default=1,type=int,help="Type of link layer")
        parser.add_argument("--append","-a",action="store_true",help="Append to pcap")
        parser.add_argument("--sync","-s",action="store_true",help="Sync pcap file")

    def __init__(self,pcap="out.pcap",link=1,append=False,sync=True,*args,**kargs):
        super().__init__(*args,**kargs)
        self.pcap = pcap
        self.linktype = link
        self.append = append
        self.sync = sync
        self.src,self.dst,self.sport,self.dport = self.get_src_dst()
        self.fd = open(self.pcap,"wb")
        if not self.append:
            self.write_pcap_header()

    def write_pcap_header(self):
        self.fd.write(struct.pack("IHHIIII",0xa1b2c3d4,2,4,0,0,0xFFFF,self.linktype))

    def get_time(self):
        """ Generate time """
        t = time.time()
        it = int(t)
        sec = it
        usec = int(round((t - it) * (1000000)))
        return struct.pack("II",sec,usec)
         
    def get_layer2(self,payload):
        """ Generate fake layer 2 data """
        return b"\x00"*12 + b"\x08\x00" + payload

    def get_layer3(self,src,dst,payload,proto4=b'\x11'):
        """ Generate fake layer 3 """
        return b'E\x00' + struct.pack(">H",len(payload)+20) + b'\x00\x01\x00\x00@' + proto4 + b'|\xcd' +  socket.inet_aton(src) + socket.inet_aton(dst) + payload

    def get_layer4(self,sport,dport,payload):
        """ Generate fake UDP layer 4 """
        chk = b'\x00\x00'
        return struct.pack(">H",sport) + struct.pack(">H",dport) + struct.pack(">H",len(payload)+6) + chk + payload


    def get_src_dst(self):
        if hasattr(self.ep1,"sock"):
            src = self.ep1.sock.getpeername()[0]
            sport = self.ep1.sock.getpeername()[1]
        else:
            if hasattr(self.ep2,"sock"):
                src = self.ep2.sock.getsockname()[0]
                sport = self.ep2.sock.getsockname()[1]
            else:
                src = "127.0.0.1"
                sport = "64100"

        if hasattr(self.ep2,"sock"):
            dst = self.ep2.sock.getpeername()[0]
            dport = self.ep2.sock.getpeername()[1]
        else:
            if hasattr(self.ep1,"sock"):
                print(self.ep1.sock)
                dst = self.ep1.sock.getsockname()[0]
                dport = self.ep1.sock.getsockname()[1]
            else:
                dst = "127.0.0.1"
                dport = "64200"

        return src,dst,sport,dport


    def write_pkt(self,pkt,client):
        if client:
            src,dst,sport,dport = self.src,self.dst,self.sport,self.dport
        else:
            dst,src,dport,sport = self.src,self.dst,self.sport,self.dport

        l4 = self.get_layer4(sport,dport,pkt)
        l3 = self.get_layer3(src,dst,l4)
        l2 = self.get_layer2(l3)
        self.fd.write(self.get_time() + struct.pack("II",len(l2),len(l2)) + l2)
        if self.sync:
            self.fd.flush()

    def handle(self,data,one):
        super().handle(data,one)
        self.write_pkt(data,one)
        return data

    def close(self):
        self.fd.close()
