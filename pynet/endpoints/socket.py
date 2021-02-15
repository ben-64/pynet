#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import socket

from pynet.endpoint import *
from pynet.tools.utils import remove_argument

SO_ORIGINAL_DST = 80 # Socket option
IP_TRANSPARENT = 19
IP_RECVORIGDSTADDR = 20

class SOCKET(Endpoint):
    _desc_ = "Socket Client"
    socket_type = None
    socket_family = None

    def __init__(self,sock=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.connect_addr = None
        self.bind_addr = None
        self.sock = sock

    def init(self):
        self.create_socket()
        self.bind()
        self.connect()

    def close(self):
        # Necessary because could be closed multiple times
        try:
            #print("[%r] close" % (self.sock.fileno(),))
            self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()
        except:
            pass

    def create_socket(self):
        self.sock = socket.socket(self.socket_family,self.socket_type)

    def connect(self):
        if self.connect_addr:
            try:
                #print("[%r] connect to %r" % (self.sock.fileno(),self.connect_addr))
                self.sock.connect(self.connect_addr)
            except ConnectionRefusedError:
                print("Connection refused")
                sys.exit(0)

    def bind(self):
        if self.bind_addr:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
            self.sock.bind(self.bind_addr)

    def send(self,data):
        #print("[%r] send" % (self.sock.fileno(),))
        try:
            self.sock.send(data)
        except:
            self.do_close()
            raise EndpointClose()

    def recv(self):
        try:
            data = self.sock.recv(4096)
        except:
            data = ""
        if len(data) == 0:
            self.do_close()
            raise EndpointClose()
        return data


class NetSocket(SOCKET):
    _desc_ = "NetSocket Client"
    socket_family = socket.AF_INET
    EP1 = False

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--destination","-d",metavar="IP",default="127.0.0.1",help="Destination Host")
        parser.add_argument("--port","-p",metavar="PORT",dest="dport",type=int,help="Destination port")
        parser.add_argument("--src-port","-s",metavar="PORT",dest="sport",type=int,help="Source port")

    def __init__(self,destination,dport,sport=None,transparent=False,*args,**kargs):
        super().__init__(*args,**kargs)
        self.destination = destination
        self.dport = dport
        self.connect_addr = (self.destination,self.dport)
        self.transparent = transparent
        if sport: self.bind_addr = ("0.0.0.0",sport)

    def bind(self):
        if self.transparent:
            # Because we will receive packet that were not for us
            self.sock.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
            self.sock.setsockopt(socket.SOL_IP, IP_RECVORIGDSTADDR, 1)
        super().bind()


class UnixSocketEmission(SOCKET):
    socket_family = socket.AF_UNIX
    EP1 = False

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--destination","-d",metavar="FILE",required=True,help="Unix socket destination")
        parser.add_argument("--abstract","-a",action="store_true",help="Use abstract socket")

    def __init__(self,destination,abstract=False,*args,**kargs):
        super().__init__(*args,**kargs)
        self.connect_addr = "\x00" + destination if abstract else destination
 

class NetSocketListen(SOCKET):
    _desc_ = "NetSocket Server"
    socket_family = socket.AF_INET
    EP2 = False

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--bind","-b",metavar="IP",default="0.0.0.0",help="Bind Address")
        parser.add_argument("--port","-p",metavar="PORT",dest="sport",type=int,required=True,help="Bind port")

    def __init__(self,sport=None,bind="0.0.0.0",transparent=False,destination=None,dport=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.bind_ip = bind
        self.sport = sport
        self.destination = destination
        self.dport = dport
        self.bind_addr = (self.bind_ip,self.sport)
        if destination and dport: self.connect_addr = (destination,self.dport)
        self.transparent = transparent

    def bind(self):
        if self.transparent:
            # Because we will need original destination
            self.sock.setsockopt(socket.SOL_IP, IP_RECVORIGDSTADDR, 1)
            # Because we will receive packet that were not for us
            self.sock.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
        super().bind()

    def create_socket_client(self,*args,**kargs):
        # Some configuration can be set from upper classes
        kargs.update(self.get_conf())
        return self.__class__(*args,**kargs)


class UnixSocketReception(SOCKET):
    socket_family = socket.AF_UNIX
    EP2 = False

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--bind","-b",metavar="FILE",required=True,help="File system Unix Socket")
        parser.add_argument("--abstract","-a",action="store_true",help="Use abstract socket")

    def __init__(self,bind,abstract=False,*args,**kargs):
        super().__init__(*args,**kargs)
        self.bind_addr = "\x00" + bind if abstract else bind

    def close(self):
        super().close()
        if self.bind_addr[0] != "\x00":
            os.remove(self.bind_addr)
 

@Endpoint.register
class TCP(NetSocket):
    _desc_ = "TCP Client"
    socket_type = socket.SOCK_STREAM


@Endpoint.register
class TCP_LISTEN(NetSocketListen):
    _desc_ = "TCP Server"
    _cmd_ = "TCP-LISTEN"
    socket_type = socket.SOCK_STREAM

    def accept(self):
        csock,caddr = self.sock.accept()
        #print("New client: %r" % (caddr,))
        x = self.create_socket_client(sock=csock)
        return x

    def bind(self):
        super().bind()
        self.sock.listen(10)

    def handle_new_client(self):
        """ Handle the connection of a new client """
        endpoint_client = self.accept()
        if self.transparent:
            dst_addr = endpoint_client.sock.getsockopt(socket.SOL_IP,SO_ORIGINAL_DST,16)
            dst_port,dst_ip = struct.unpack("!2xH4s8x", dst_addr)
            dst_ip = socket.inet_ntoa(dst_ip)
            return endpoint_client,(dst_ip,dst_port)
        else:
            return endpoint_client,None

@Endpoint.register
class UDP(NetSocket):
    _desc_ = "UDP Client"
    socket_type = socket.SOCK_DGRAM


@Endpoint.register
class UDP_LISTEN(NetSocketListen):
    _cmd_ = "UDP-LISTEN"
    _desc_ = "UDP Server"
    socket_type = socket.SOCK_DGRAM

    def handle_new_client(self):
        """ Handle the connection of a new client """
        # Read without consuming data, to get client addr
        if self.transparent:
            data,ancdata,flags,c_addr = sock.recvmsg(4096,socket.MAX_ANC_SIZE|socket.MSK_PEED)
            # Find real address
            for cmsg_level, cmsg_type, cmsg_data in ancdata:
                if cmsg_level == socket.SOL_IP and cmsg_type == IP_RECVORIGDSTADDR:
                    port,ip = struct.unpack_from("!xxH4s", cmsg_data)
                    real_dst_addr = socket.inet_ntoa(ip),port
                    break
        else:
            data,c_addr = self.sock.recvfrom(4096,socket.MSG_PEEK)
            real_dst_addr = None

        endpoint = self.create_socket_client(sock=self.sock,destination=c_addr[0],dport=c_addr[1])
        endpoint.connect()

        # Recreate a new listening socket for potential new UDP clients
        self.init()
        return endpoint,real_dst_addr
    

@Endpoint.register
class UnixSocketConnect(UnixSocketEmission):
    _desc_ = "Unix socket Stream mode"
    _cmd_ = "UNIX-CONNECT"
    socket_type = socket.SOCK_STREAM


@Endpoint.register
class UnixSocketSend(UnixSocketEmission):
    _desc_ = "Unix socket datagram mode"
    _cmd_ = "UNIX-SENDTO"
    socket_type = socket.SOCK_DGRAM


@Endpoint.register
class UnixSocketListen(UnixSocketReception):
    _desc_ = "Unix Socket Listen in stream mode"
    _cmd_ = "UNIX-LISTEN"
    socket_type = socket.SOCK_STREAM

    def accept(self):
        csock,addr = self.sock.accept()
        return create_socket_client(sock=csock)

    def bind(self):
        super().bind()
        self.sock.listen(10)

    def handle_new_client(self):
        """ Handle the connection of a new client """
        endpoint_client = self.accept()
        return endpoint_client,None


@Endpoint.register
class UnixSocketRecv(UnixSocketReception):
    _desc_ = "Unix Socket receive in datagram mode"
    _cmd_ = "UNIX-RECV"
    socket_type = socket.SOCK_DGRAM
