#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pynet.tools.utils import Configurator

class TProxyConfigurator(Configurator):
    def __init__(self,port=5555,proto="tcp",chain="INTERCEPT",mark=64,table=101,client_iface="eth0",server_iface="eth1",Filter=""):
        super().__init__()
        self.add_init("iptables -t mangle -N %s" % (chain,))
        self.add_fini("iptables -t mangle -X %s" % (chain,))
        self.add_init("iptables -t mangle -A %s -j MARK --set-mark %u" % (chain,mark),
                      "iptables -t mangle -A %s -j ACCEPT" % (chain,))
        self.add_fini("iptables -t mangle -F %s" % (chain,))
        self.add_init("iptables -t mangle -A PREROUTING -p %s -m socket -j %s" % (proto,chain,))
        self.add_fini("iptables -t mangle -D PREROUTING -p %s -m socket -j %s" % (proto,chain))
        self.add_init("ip rule add fwmark %u lookup %u" % (mark,table))
        self.add_fini("ip rule del fwmark %u lookup %u" % (mark,table))
        self.add_init("ip route add local 0/0 dev lo table %u" % (table,))
        self.add_fini("ip route del local 0/0 dev lo table %u" % (table,))
        self.add_init("iptables -t mangle -A PREROUTING -p %s -i %s %s -j TPROXY --on-port %u --tproxy-mark %u" % (proto,client_iface,Filter,port,mark))
        self.add_fini("iptables -t mangle -D PREROUTING -p %s -i %s %s -j TPROXY --on-port %u --tproxy-mark %u" % (proto,client_iface,Filter,port,mark))
        self.add_init("iptables -I INPUT -p %s -m mark --mark %u -j ACCEPT" % (proto,mark))
        self.add_fini("iptables -D INPUT -p %s -m mark --mark %u -j ACCEPT" % (proto,mark))


class BridgeConfigurator(Configurator):
    def __init__(self,client_iface="eth0",server_iface="eth1",bridge_iface="br0",client_filter="-p ipv4 --ip-proto udp --ip-dport 64240",server_filter="-p ipv4 --ip-proto udp --ip-sport 64240"):
        super().__init__()
        self.bridge_iface = bridge_iface
        self.add_init("ip link add name %s type bridge" % (bridge_iface,)),
        self.add_fini("ip link delete %s type bridge" % (bridge_iface,))
        self.add_init("ip link set %s up" % (bridge_iface,)),
        self.add_fini("ip link set %s down" % (bridge_iface,)),
        self.add_iface_to_bridge(client_iface)
        self.add_iface_to_bridge(server_iface)

        self.add_init("ebtables -t broute -A BROUTING -i %s %s -j redirect --redirect-target DROP" % (client_iface,client_filter))
        self.add_fini("ebtables -t broute -D BROUTING -i %s %s -j redirect --redirect-target DROP" % (client_iface,client_filter))
        self.add_init("ebtables -t broute -A BROUTING -i %s %s -j redirect --redirect-target DROP" % (server_iface,server_filter))
        self.add_fini("ebtables -t broute -D BROUTING -i %s %s -j redirect --redirect-target DROP" % (server_iface,server_filter))

    def add_iface_to_bridge(self,iface):
        self.add_init("ip link set %s master %s" % (iface,self.bridge_iface))
        self.add_fini("ip link set %s nomaster" % (iface,))
