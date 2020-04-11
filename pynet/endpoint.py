#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

from pynet.tools.utils import Register
from pynet.plugin import Plugin

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

    def init(self):
        pass

    def close(self):
        pass

    def recv(self):
        """ Call to receive data """
        pass

    def send(self,data):
        pass


class InputEndpoint(Endpoint):
    EP2 = False

class OutputEndpoint(Endpoint):
    EP1 = False
