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
class Socks4Client(TCP):
    _desc_ = "Socks4 Client: Going to connect to a socks4 server"

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
class Socks4Server(TCP):
    _desc_ = "Socks4 Server: socks4 protocol needed (a socks4 client is supposed to be sending information)"

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


@Endpoint.register
class Socks5Client(TCP):
    _desc_ = "Socks5 Client: Going to connect to a socks5 server"

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
        parser.add_argument("--username",metavar="USERNAME",dest="user",default=None,help="Username (optional)")
        parser.add_argument("--password",metavar="PASSWORD",dest="password",default=None,help="Password (optional)")

    def __init__(self,sserver="127.0.0.1",dport=1080,fserver="127.0.0.1",fport=8080,user=None,password=None,*args,**kargs):
        super().__init__(destination=sserver,dport=dport,*args,**kargs)
        self.fserver = fserver
        self.fport = fport
        self.user = user
        self.password = password

    def _auth(self, username, password):
        use_auth = username is not None or password is not None

        if use_auth and username is None:
            print("Password specified but username is missing")
            sys.exit(0)

        if use_auth and password is None:
            print("Username specified but password is missing")
            sys.exit(0)

        if use_auth:
            # Ask the server to authenticate using a username and password
            super().send(b"\x05\x01\x02")
        else:
            # No authentication
            super().send(b"\x05\x01\x00")

        # Get the server's answer regarding authentication
        res = super().recv()

        if not res:
            print("Unable to connect to socks server: empty response to greeting")
            sys.exit(0)

        if res[0] != 5:
            print("Unable to connect to socks server: got unexpected protocol version %d" % (res[0],))
            sys.exit(0)

        if res == b"\x05\x00":
            # Server replied that no authentication is required
            return

        if res == b"\x05\xFF":
            print("Unable to connect to socks server: server rejected authentication mechanism")
            sys.exit(0)

        if res == b"\x05\x02":
            # Server asks for username and password
            if not use_auth:
                print("Unable to connect to socks server: authentication required (res:%s)" % (res,))
                sys.exit(0)

            encoded_user = struct.pack(">c",len(username)) + username.encode("utf-8")
            encoded_pass = struct.pack(">c",len(password)) + password.encode("utf-8")
            super().send(b"\x01" + encoded_user + encoded_pass)

            res = super().recv(2)
            if res != b"\x01\x00":
                print("Unable to connect to socks server: authentication failed (res:%s)" % (res,))
                sys.exit(0)

            return

        print("Unable to connect to socks server: unsupported auth method (res:%s)" % (res,))
        sys.exit(0)

    def connect(self):
        super().connect()
        self._auth(self.user, self.password)

        connection_pkt = b"\x05\x01\x00\x01" + socket.inet_aton(self.fserver) + struct.pack(">H",self.fport)
        super().send(connection_pkt)
        res = super().recv()
        if res[:3] != b"\x05\x00\x00":
            print("Unable to connect to socks server (res:%s)" % (res,))
            sys.exit(0)

