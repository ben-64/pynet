#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys,os
import struct
import socket
from fcntl import ioctl

from pynet.endpoint import *

class Interface(Endpoint):
    IFNAMSIZE    = 16
    IFF_UP       = 0x1
    SIOCSIFFLAGS = 0x8914
    SIOCSIFADDR  = 0x8916
    RECV_SIZE    = 2048

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--ip","-i",metavar="IP",help="Set IP address")

    def __init__(self,name=None,ip=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.name = name if name is not None else "\x00"*Interface.IFNAMSIZE
        # Socket used for ioctl
        self.sd = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_IP)
        # socket linked to interface
        self.fd = 0
        self.addr = ip

    def __del__(self):
        self.sd.close()

    def up(self):
        """ iconfig IF up """
        ifr = struct.pack("%usH" % Interface.IFNAMSIZE, self.name, Interface.IFF_UP)
        ioctl(self.sd, Interface.SIOCSIFFLAGS, ifr)

    def ip(self,addr):
        """ ifconfig IF addr """
        ifr = struct.pack("%ushH4s8s" % Interface.IFNAMSIZE, self.name, socket.AF_INET, 0, socket.inet_aton(addr),("\x00"*8).encode())
        ioctl(self.sd, Interface.SIOCSIFADDR, ifr)

    def init(self):
        self.ip(self.addr)
        self.up()

    def recv(self):
        return os.read(self.fd,Interface.RECV_SIZE)

    def send(self,data):
        return os.write(self.fd,data)


class VirtualInterface(Interface):
    _desc_ = "TUN/TAP interface"
    tun_file = "/dev/net/tun"
    TUNSETIFF = 0x400454ca
    IFF_TUN   = 0x0001
    IFF_TAP   = 0x0002
    IFF_NO_PI = 0x1000

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)

    def __init__(self,name=None,ip=None,flags=IFF_TUN|IFF_NO_PI,*args,**kargs):
        super().__init__(name=name,ip=ip,*args,**kargs)
        self.flags = flags
        self.fd = os.open(VirtualInterface.tun_file, os.O_RDWR)
        ifr = struct.pack("%usH" % Interface.IFNAMSIZE, self.name.encode(), flags)
        self.name = ioctl(self.fd, VirtualInterface.TUNSETIFF, ifr)


@Endpoint.register
class TUN(VirtualInterface):
    _desc_ = "TUN interface"
    def __init__(self,*args,**kargs):
        super().__init__(name="pytun0",flags=VirtualInterface.IFF_TUN|VirtualInterface.IFF_NO_PI,*args,**kargs)


@Endpoint.register
class TAP(VirtualInterface):
    _desc_ = "TAP interface"
    def __init__(self,*args,**kargs):
        super().__init__(name="pytap0",flags=VirtualInterface.IFF_TAP|VirtualInterface.IFF_NO_PI,*args,**kargs)
