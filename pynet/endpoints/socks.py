#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import struct
import socket
from threading import Event

from pynet.endpoint import Endpoint
from pynet.endpoints.socket import TCP
from pynet.tools.utils import remove_argument

@Endpoint.register
class SocksClient(TCP):
    _desc_ = "Socks Client : Going to connect to a socks server"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        remove_argument(parser,"destination")
        remove_argument(parser,"port")
        remove_argument(parser,"sport")
        parser.add_argument("--socks-server","-d",metavar="IP",dest="sserver",default="127.0.0.1",help="Socks server address")
        parser.add_argument("--socks-port","-p",metavar="PORT",dest="dport",type=int,default=1080,help="Socks server port")
        parser.add_argument("--final-server","-D",metavar="IP",dest="fserver",default="127.0.0.1",help="Final server address")
        parser.add_argument("--final-port","-P",metavar="PORT",dest="fport",type=int,default=8080,help="Final server port")

    def __init__(self,sserver="127.0.0.1",dport=1080,fserver="127.0.0.1",fport=8080,*args,**kargs):
        super().__init__(destination=sserver,dport=dport,*args,**kargs)
        self.fserver = fserver
        self.fport = fport

    def connect(self):
        super().connect()
        connection_pkt = b"\x04\x01" + struct.pack(">H",self.fport) + socket.inet_aton(self.fserver) + b"pynet\x00"
        super().send(connection_pkt)
        res = super().recv()
        if res[1] != 0x5a:
            print("Unable to connect to socks server (res:0x%02x)" % (res[1],))
            sys.exit(0)


@Endpoint.register
class SocksServer(TCP):
    _desc_ = "Socks Server : socks protocol needed (a socks client is supposed to be sending information)"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        remove_argument(parser,"destination")
        remove_argument(parser,"port")
        remove_argument(parser,"sport")

    def __init__(self,*args,**kargs):
        super().__init__(destination=None,dport=None,*args,**kargs)
        self.connected = False
        self.receive_ready_event = Event()
        self.connected_event = Event()

    def connect(self):
        self.create_socket()

    def do_send(self,data):
        if not self.connected:
            self.receive_ready_event.wait()
            version,cmd,port = struct.unpack(">BBH",data[:4])
            ip = socket.inet_ntoa(data[4:8])
            #print("%r %r %r %r %r" % (version,cmd,port,ip,data[8:],))

            self.destination = ip
            self.dport = port
            self.connect_addr = (ip,port)

            super().connect()
            self.connected = True
            self.connected_event.set()
        else:
            super().do_send(data)

    def do_recv(self):
        if not self.connected:
            self.receive_ready_event.set()
            self.connected_event.wait()
            return b"\x00\x5a\x00\x00\x00\x00\x00\x00"
        return super().do_recv()
