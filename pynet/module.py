#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

from pynet.tools.utils import Register
from pynet.plugin import Plugin

class ModuleRegister(Register):
    _cmd_  = "Module"
    _desc_ = "List of registered Modules"
    registry = defaultdict(dict)

class ModuleContainer(object):
    def __init__(self,module_cls,module_args,*args,**kargs):
        self.cls = module_cls
        self.args = module_args

    def get(self,ep1,ep2):
        self.args["ep1"] = ep1
        self.args["ep2"] = ep2
        return self.cls.from_cli(self.args)

class Module(Plugin):
    _desc_ = "Default Module"
    registerer = ModuleRegister

    def __init__(self,ep1,ep2,*args,**kargs):
        super().__init__(*args,**kargs)
        self.ep1 = ep1
        self.ep2 = ep2

    def handle(self,data,one):
        pass

class PassThrough(Module):
    def handle(self,data,one):
        return data
