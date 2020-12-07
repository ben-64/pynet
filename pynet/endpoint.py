#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

from pynet.tools.utils import Register
from pynet.plugin import Plugin
from pynet.proto import *

class EndpointClose(Exception):
    pass

class EndpointRegister(Register):
    _cmd_  = "Endpoint"
    _desc_ = "List of registered Endpoints"
    registry = defaultdict(dict)

class Endpoint(Plugin):
    _desc_ = "Default Endpoint"
    registerer = EndpointRegister
    EP1 = True
    EP2 = True

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--proto",metavar="PROTO",type=lambda p:eval(p),default=NoProto(),help="Use a specific protocol : %s" % (",".join([x.__name__ for x in ProtoRegister.itervalues()])))

    def __init__(self,proto=NoProto(),*args,**kargs):
        super().__init__(*args,**kargs)
        self.proto = proto

    def get_conf(self):
        """ Use if we need to duplicate EndPoint, to keep the mandatory parameters """
        return {"proto":self.proto}

    def init(self):
        pass

    def close(self):
        pass

    def recv(self):
        """ Call to receive data """
        pass

    def send(self,data):
        pass

    def do_recv(self):
        return self.recv()

    def do_send(self,data):
        return self.send(data)

    def proto_recv(self):
        return self.proto.remove(self.do_recv())

    def proto_send(self,data):
        data = data if type(data) is list else [data]
        for d in data:
            pkts = self.proto.add(d)
            pkts = pkts if type(pkts) is list else [pkts]
            for pkt in pkts:
                self.do_send(pkt)

class InputEndpoint(Endpoint):
    EP2 = False

class OutputEndpoint(Endpoint):
    EP1 = False
