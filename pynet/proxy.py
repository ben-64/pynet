#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
from collections import defaultdict
from copy import copy
import time
from threading import Thread

from pynet.forwarder import ThreadForwarder
from pynet.tools.utils import Register
from pynet.module import Module,PassThrough,ModuleContainer
from pynet.endpoint import InputEndpoint,OutputEndpoint
from pynet.plugin import Plugin

logger = logging.getLogger("RELAY")
logger.setLevel(logging.WARNING)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


class AbstractRelay(object):
    def __init__(self,module=ModuleContainer(PassThrough,{}),forwarder=ThreadForwarder):
        self.modules = [module]
        self.forwarder_cls = forwarder

    def instanciate_forwarder(self,ep1,ep2,end_forwarder_cb=None):
        return self.forwarder_cls(ep1,ep2,self.modules,end_forwarder_cb)

    def run(self):
        try:
            self.do_run()
        except KeyboardInterrupt:
            pass
        self.close()

    def do_run(self):
        pass

    def close(self):
        pass


class Relay(AbstractRelay):
    def __init__(self,first_endpoint,second_endpoint,module=ModuleContainer(PassThrough,{}),forwarder=ThreadForwarder):
        super().__init__(module,forwarder)
        self.ep1 = first_endpoint
        self.ep2 = second_endpoint

    def do_run(self):
        self.forwarder = self.instanciate_forwarder(self.ep1,self.ep2)
        self.ep1.init()
        self.ep2.init()
        logger.debug("relay starting forwarder %r" % (self.forwarder,))
        self.forwarder.run()

    def close(self):
        self.forwarder.close()


class MultipleRelay(AbstractRelay):
    def __init__(self,*args,**kargs):
        super().__init__(*args,**kargs)
        self.forwarders = []

    def end_forwarder(self,forwarder):
        """ Callback called by a forwarder when it ends """
        self.forwarders.remove(forwarder)
        logger.debug("Remove forwarder %r" % (forwarder,))

    def close(self):
        logger.debug("Closing Multiple relay")
        for fwd in self.forwarders:
            fwd.close()

    def add(self,ep1,ep2):
        fwd = self.instanciate_forwarder(ep1,ep2,self.end_forwarder)
        self.forwarders.append(fwd)
        fwd.start()


class MultipleClientRelay(MultipleRelay):
    def __init__(self,first_endpoint,second_endpoint,*args,**kargs):
        super().__init__(*args,**kargs)
        self.ep1 = first_endpoint
        self.ep2 = second_endpoint
        self.stop = False

    def do_run(self):
        self.ep1.init()
        try:
            while not self.stop:
                client,_ = self.ep1.handle_new_client()
                server = self.ep2.duplicate()
                server.init()
                self.add(client,server)
        except KeyboardInterrupt:
            self.stop = True

    def close(self):
        super().close()
        self.stop = False


class ProxyRegister(Register):
    _cmd_  = "Proxy"
    _desc_ = "List of registered Proxys"
    registry = defaultdict(dict)


class Proxy(Plugin):
    _desc_ = "Default Proxy"
    registerer = ProxyRegister

    class BackgroundTask(Thread):
        def __init__(self,proxy):
            super().__init__()
            self.daemon = True
            self.proxy = proxy

        def run(self):
            self.proxy.run()

    @classmethod
    def set_cli_arguments(cls,parser):
        parser.add_argument("--console",action="store_true",help="Activate IPython console")

    def __init__(self,module=ModuleContainer(PassThrough,{}),console=None,relay=MultipleRelay,*args,**kargs):
        super().__init__(*args,**kargs)
        self.relay = relay(module)
        self.console = console
        self.stop = False
        if console:
            import console
            self.console = console.start_console(self)

    def init(self):
        pass

    def close(self):
        pass

    def start(self):
        self.thread = Proxy.BackgroundTask(self)
        self.thread.start()

    def run(self):
        try:
            self.do_run()
        except KeyboardInterrupt:
            pass
        self.relay.close()
        self.close()
