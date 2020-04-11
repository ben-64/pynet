#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from collections import defaultdict

from pynet.tools.utils import Register
from pynet.tools.utils import Register,DirectAccessDict

class PluginRegister(Register):
    _cmd_  = "Plugin"
    _desc_ = "List of registered Plugins"
    registry = defaultdict(dict)

class Plugin(object):
    _desc_ = "Default plugin"
    registerer = PluginRegister

    @classmethod
    def register(cls,f):
        PluginRegister.register(f)
        return cls.registerer.register(f)

    @classmethod
    def from_cli(cls,cli):
        obj = cls(**cli)
        obj.cli = cli
        return obj

    @classmethod
    def set_cli_arguments(cls,parser):
        pass

    @classmethod
    def get_cmdline_name(cls):
        if hasattr(cls,"_cmd_") and \
           (not hasattr(cls.__bases__[0],"_cmd_") or cls.__bases__[0]._cmd_ != cls._cmd_):
            key = "_cmd_"
        else:
            key = "__name__"
        return getattr(cls,key)

    def duplicate(self):
        return type(self).from_cli(self.cli)

    def __init__(self,*args,**kargs):
        self.args = DirectAccessDict(kargs)
