#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

from pynet.proxy import Proxy
from pynet.endpoints.socket import TCP,TCP_LISTEN,UDP,UDP_LISTEN
from pynet.proxys.tproxy import TProxyConfigurator,BridgeConfigurator

class Layer4Proxy(Proxy):

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("-b","--bind",metavar="IP",default="0.0.0.0",help="Address to bind to (will be override if transparent mode is choosen)")
        parser.add_argument("-p","--port",metavar="PORT",default="8080",type=int,help="Port to bind to")
        parser.add_argument("--src-port",metavar="PORT",default=None,type=int,help="Bind Source Port")
        parser.add_argument("--server-ip","-d",default="127.0.0.1",metavar="IP",help="IP Server to connect to")
        parser.add_argument("--server-port",metavar="PORT",type=int,help="Port Server to connect to, by default the same as the client")
        parser.add_argument("--mirror",action="store_true",help="Use the same source port as the client one (might need root permission if port is lower than 1024, and don't work if client is on the same system as the proxy)")
        parser.add_argument("--transparent",action="store_true",help="Use as transparent proxy")

        tproxy = parser.add_argument_group('Transparent proxy options')
        tproxy.add_argument("--tproxy-chain",metavar="CHAIN",default="INTERCEPT",help="Use CHAIN as Netfilter interception chain")
        tproxy.add_argument("--tproxy-mark",metavar="MARK",default=64,type=int,help="use MARK as NetFilter packet mark for ip rule")
        tproxy.add_argument("--tproxy-table",metavar="TABLE",default=101,type=int,help="use TABLE for interception routing table number")
        tproxy.add_argument("--tproxy-client-iface",metavar="IFACE",default="eth0",help="Interface connected to client")
        tproxy.add_argument("--tproxy-server-iface",metavar="IFACE",default="eth1",help="Interface connected to server")
        tproxy.add_argument("--tproxy-specific-filter",metavar="FILTER",default="",help="Use specific filter to avoid intercepting unecessary trafic")
        tproxy.add_argument("--no-tproxy-netfilter",action="store_false",dest="tproxy_netfilter",help="Configure netfilter system for tproxy")
        tproxy.add_argument("--bridge",action="store_true",help="Proxy mode is in bridged mode")

    def __init__(self,*args,**kargs):
        super().__init__(*args,**kargs)
        self.port = self.args.port
        self.host = self.args.bind
        self.server_ip = self.args.server_ip
        self.server_port = self.args.server_port
        self.src_port = self.args.src_port
        self.dst = (self.server_ip,self.server_port)
        self.mirror = self.args.mirror
        self.transparent = self.args.transparent
        self.bridge = self.args.bridge

        if self.transparent and args.tproxy_netfilter:
            self.netfilter_configurator = TProxyConfigurator(self.port,self._proto_,args.tproxy_chain,args.tproxy_mark,args.tproxy_table,args.tproxy_client_iface,args.tproxy_server_iface,args.tproxy_specific_filter)
            self.netfilter_configurator.configure()
            if self.bridge:
                self.bridge_configurator = BridgeConfigurator(args.tproxy_client_iface,args.tproxy_server_iface)
                self.bridge_configurator.configure()

        self.client_side = self.create_client_side()

    def init(self):
        self.client_side.init()

    def close(self):
        if self.transparent and self.args.tproxy_netfilter:
            self.netfilter_configurator.deconfigure()
        if self.bridge:
            self.bridge_configurator.deconfigure()

    def create_client_side(self):
        return self.CLIENT_ENDPOINT(bind=self.host,sport=self.port,transparent=self.transparent)

    def create_server_side(self,dest,dport,sport):
        return self.SERVER_ENDPOINT(destination=dest,dport=dport,sport=sport,transparent=self.transparent)

    def handle_new_connection(self,endpoint_client,real_dst_addr=None):
        """ Handle a new data coming to the socket """

        # Create socket that will be exchanging data with the real server
        if self.mirror:
            sport = endpoint_client.sock.getpeername()[1]
        elif self.src_port:
            sport = self.src_port
        else:
            sport = None

        if self.transparent:
            dst_ip,dst_port = real_dst_addr
        else:
            dst_ip = self.server_ip
            dst_port = self.server_port if self.server_port else self.port

        endpoint_server = self.create_server_side(dst_ip,dst_port,sport)
        endpoint_server.init()

        self.forwarder.add(endpoint_client,endpoint_server)

    def run(self):
        self.init()
        while not self.stop:
            client,real_dst_addr = self.client_side.handle_new_client()
            self.handle_new_connection(client,real_dst_addr)


@Proxy.register
class TCPProxy(Layer4Proxy):
    _desc_ = "TCP Proxy"
    CLIENT_ENDPOINT = TCP_LISTEN
    SERVER_ENDPOINT = TCP

@Proxy.register
class UDPProxy(Layer4Proxy):
    _desc_ = "UDP Proxy"
    CLIENT_ENDPOINT = UDP_LISTEN
    SERVER_ENDPOINT = UDP
