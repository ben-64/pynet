#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from threading import Thread
import logging
from collections import defaultdict
from copy import copy
import time

from pynet.forwarder import ThreadForwarder
from pynet.tools.utils import Register
from pynet.module import Module,PassThrough,ModuleContainer
from pynet.endpoint import InputEndpoint,OutputEndpoint
from pynet.plugin import Plugin


class Relay(object):
    def __init__(self,first_endpoint,second_endpoint,module=ModuleContainer(PassThrough,{}),forwarder=ThreadForwarder):
        self.modules = [module]
        self.first_endpoint = first_endpoint
        self.second_endpoint = second_endpoint
        self.forwarder = forwarder(self.modules)
        self.stop = False

    def run(self):
        try:
            self.do_run()
        except KeyboardInterrupt:
            pass
        self.close()

    def do_run(self):
        self.first_endpoint.init()
        self.second_endpoint.init()
        self.forwarder.add(self.first_endpoint,self.second_endpoint)
        while not self.stop:
            time.sleep(1)

    def close(self):
        self.forwarder.close()


class MultipleClientRelay(Relay):
    def do_run(self):
        self.first_endpoint.init()
        while not self.stop:
            client,_ = self.first_endpoint.handle_new_client()
            server = self.second_endpoint.duplicate()
            server.init()
            self.forwarder.add(client,server)
            #print("CLIENTS: %s" % (",".join(["%u:%u" % (k.sock.fileno(),v.sock.fileno()) for k,v in self.forwarder.forwarding_client.items()])))
            #print("SERVERS: %s" % (",".join(["%u:%u" % (k.sock.fileno(),v.sock.fileno()) for k,v in self.forwarder.forwarding_server.items()])))

    def close(self):
        super().close()
        self.first_endpoint.close()


class ProxyRegister(Register):
    _cmd_  = "Proxy"
    _desc_ = "List of registered Proxys"
    registry = defaultdict(dict)


class Proxy(Plugin):
    _desc_ = "Default Proxy"
    registerer = ProxyRegister

    @classmethod
    def set_cli_arguments(cls,parser):
        parser.add_argument("--console",action="store_true",help="Activate IPython console")

    def __init__(self,module=ModuleContainer(PassThrough,{}),console=None,forwarder=ThreadForwarder,*args,**kargs):
        super().__init__(*args,**kargs)
        self.modules = [module]
        self.forwarder = forwarder(self.modules)
        self.console = console
        self.stop = False
        if console:
            import console
            self.console = console.start_console(self)

    def init(self):
        pass

    def close(self):
        pass

    def run(self):
        raise NotImplementedError()
