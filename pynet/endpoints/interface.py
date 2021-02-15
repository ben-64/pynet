#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys,os
import struct
import socket
import ctypes
from fcntl import ioctl

from pynet.endpoint import *
from pynet.tools.utils import remove_argument

class ifreq(ctypes.Structure):
    _fields_ = [("ifr_ifrn", ctypes.c_char * 16),
                ("ifr_flags", ctypes.c_short)]


@Endpoint.register
class Interface(Endpoint):
    IFNAMSIZE        = 16
    IFF_UP           = 0x1
    IFF_PROMISC      = 0x100
    SIOCGIFFLAGS     = 0x8913
    SIOCSIFFLAGS     = 0x8914
    SIOCSIFADDR      = 0x8916
    ETH_P_ALL        = 0x0003
    SIOCGIFINDEX     = 0x8933
    IFNAMSIZE        = 16
    SO_ATTACH_FILTER = 26

    RECV_SIZE    = 2048

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--iface","-i",metavar="INTERFACE",required=True,help="Ethernet card to use")
        parser.add_argument("--ip","-a",metavar="IP",help="Set IP address")
        parser.add_argument("--up",action="store_true",help="Up the card")
        parser.add_argument("--promisc",action="store_true",help="Set card in promiscous mode")
        parser.add_argument("--bpf","-b",metavar="BPF_FILTER",type=lambda p: p.split(":"),help="BPF filter : ip:port")

    def __init__(self,iface=None,ip=None,up=False,promisc=False,bpf=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.promisc = promisc
        self.iface = iface if iface is not None else "\x00"*Interface.IFNAMSIZE
        self.addr = ip
        self.up = up
        self.promisc = promisc
        self.bpf = bpf

    def init(self):
        self.create_socket()
        if self.bpf: self.set_bpf_filter(self.bpf[0],self.bpf[1])
        if self.addr: self.set_ip(self.addr)
        if self.promisc: self.set_promisc(self.promisc)
        if self.up : self.set_up()
        self.bind()

    def __del__(self):
        if self.promisc:
            self.set_promisc(False)
        self.sock.close()

    def create_socket(self):
        self.sock = socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.ntohs(Interface.ETH_P_ALL))

    def bind(self):
        self.sock.bind((self.iface,0))

    def set_up(self):
        """ iconfig IF up """
        ifr = struct.pack("%usH" % Interface.IFNAMSIZE, self.iface, Interface.IFF_UP)
        ioctl(self.sock, Interface.SIOCSIFFLAGS, ifr)

    def set_ip(self,addr):
        """ ifconfig IF addr """
        ifr = struct.pack("%ushH4s8s" % Interface.IFNAMSIZE, self.iface, socket.AF_INET, 0, socket.inet_aton(addr),("\x00"*8).encode())
        ioctl(self.sock, Interface.SIOCSIFADDR, ifr)

    def set_promisc(self,promisc=True):
        ifr = ifreq()
        ifr.ifr_ifrn = self.iface.encode()

        # Get the flag
        ioctl(self.sock, Interface.SIOCGIFFLAGS, ifr)
        if promisc:
            ifr.ifr_flags |= Interface.IFF_PROMISC
        else:
            ifr.ifr_flags ^= Interface.IFF_PROMISC
        ioctl(self.sock, Interface.SIOCSIFFLAGS, ifr) 

    def send(self,data):
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

    def set_bpf_filter(self,host,port):
        from pynet.tools.bpf import BPFNetwork

        # Build BPF filter
        bpf_filter = BPFNetwork(host,int(port)).build()

        # Create internal Linux Structure
        from ctypes import create_string_buffer, addressof
        sz_filter = int(len(bpf_filter)/8)
        bpf_filter = create_string_buffer(bpf_filter)
        bpf_filter_addr = addressof(bpf_filter)  
        bpf_struct = struct.pack('HL', sz_filter, bpf_filter_addr)

        # Attach filter
        self.sock.setsockopt(socket.SOL_SOCKET, Interface.SO_ATTACH_FILTER, bpf_struct)


class VirtualInterface(Interface):
    _desc_ = "TUN/TAP interface"
    tun_file = "/dev/net/tun"
    TUNSETIFF = 0x400454ca
    IFF_TUN   = 0x0001
    IFF_TAP   = 0x0002
    IFF_NO_PI = 0x1000

    def __init__(self,flags=IFF_TUN|IFF_NO_PI,*args,**kargs):
        super().__init__(*args,**kargs)
        self.flags = flags
        self.fd = os.open(VirtualInterface.tun_file, os.O_RDWR)
        ifr = struct.pack("%usH" % Interface.IFNAMSIZE, self.iface.encode(), flags)
        self.iface = ioctl(self.fd, VirtualInterface.TUNSETIFF, ifr)

    def create_socket(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM,socket.IPPROTO_IP)

    def bind(self):
        pass

    def recv(self):
        return os.read(self.fd,Interface.RECV_SIZE)

    def send(self,data):
        try:
            os.write(self.fd,data)
        except:
            print("Failed to send data : %r %r" % (self.fd,data))


@Endpoint.register
class TUN(VirtualInterface):
    _desc_ = "TUN interface"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        remove_argument(parser,"iface")
        parser.add_argument("--iface","-i",metavar="INTERFACE",default="pytun0",help="Virtual IP card name")

    def __init__(self,iface="pytun0",*args,**kargs):
        super().__init__(iface=iface,flags=VirtualInterface.IFF_TUN|VirtualInterface.IFF_NO_PI,*args,**kargs)


@Endpoint.register
class TAP(VirtualInterface):
    _desc_ = "TAP interface"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        remove_argument(parser,"iface")
        parser.add_argument("--iface","-i",metavar="INTERFACE",default="pytap0",help="Virtual ethernet card name")

    def __init__(self,iface="pytap0",*args,**kargs):
        super().__init__(iface=iface,flags=VirtualInterface.IFF_TAP|VirtualInterface.IFF_NO_PI,*args,**kargs)
