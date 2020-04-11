#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import struct
import time

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
        self.fd = open(self.pcap,"wb")
        if not self.append:
            self.write_pcap_header()

    def write_pcap_header(self):
        self.fd.write(struct.pack("IHHIIII",0xa1b2c3d4,2,4,0,0,0xFFFF,self.linktype))

    def write_pkt(self,pkt):
        t = time.time()
        it = int(t)
        sec = it
        usec = int(round((t - it) * (1000000)))
        self.fd.write(struct.pack("IIII",sec,usec,len(pkt)+14,len(pkt)+14))
        self.fd.write(b"\x00"*12 + b"\x08\x00" + pkt)
        if self.sync:
            self.fd.flush()

    def handle(self,data,one):
        super().handle(data,one)
        self.write_pkt(data)
        return data

    def close(self):
        self.fd.close()
