#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import signal

class InsensitiveDict(dict):
    def __setitem__(self, key, value):
        super(InsensitiveDict, self).__setitem__(key.lower(), value)

    def __getitem__(self, key):
        return super(InsensitiveDict, self).__getitem__(key.lower())

    def __contains__(self,key):
        return super(InsensitiveDict, self).__contains__(key.lower())

class Register(object):
    @classmethod
    def register(cls,obj):
        cls.registry[obj.get_cmdline_name()] = obj
        return obj

    @classmethod
    def get(cls, name, default=None):
        return cls.registry.get(name, default)

    @classmethod
    def itervalues(cls):
        return cls.registry.values()

    @classmethod
    def items(cls):
        return cls.registry.items()

class DirectAccessDict(dict):
    def __getattr__(self,f):
        return self[f]

def hexdump(s,size=16):
    """ Hexdump data """
    def out(c):
        if c < 32 or c > 126: sys.stdout.write(".")
        else: sys.stdout.write(chr(c))

    s = list(s)
    for i in range(len(s)):
        sys.stdout.write("%02x " % (s[i],))
        if i != 0 and i%size == size-1:
            sys.stdout.write("\t\t|")
            for j in range(i-size+1,i+1):
                out(s[j])
            sys.stdout.write("|\n")
    l = len(s)
    m = l%size
    sys.stdout.write("%s\t\t|" % (" "*(size-m)*3,))
    for i in range(l-m,l):
        out(s[i])
    sys.stdout.write("%s|\n" % (" "*(size-m),))

def get_all_subclasses(cls):
    all_subclasses = []

    for subclass in cls.__subclasses__():
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses

def remove_argument(parser, destinations):
    """ Used to remove an argument in a parser, opposite of add_argument """
    destinations = destinations if type(destinations) is list else [destinations]
    for destination in destinations:
        for action in parser._actions:
            daction = vars(action)
            if destination in daction["dest"]:
                for option in daction["option_strings"][:]:
                    parser._handle_conflict_resolve(None,[(option,action)])
                break

# Taken from https://bitbucket.org/secdev/cakeutils/interceptor.py
def system(cmd, canfail=True):
    ret = os.system(cmd)
    if ret != 0:
        err = "Error %i when executing [%s]" % (ret, cmd)
        if canfail:
            print(err)
        else:
            raise Exception()
    return ret


class Configurator:
    def __init__(self, command=system):
        self.init=[]
        self.fini=[]
        self.level=0
        self.command = command

    def add_init(self, *cmds):
        self.init.append(cmds)
    def add_fini(self, *cmds):
        self.fini.append(cmds)

    def set_max_level(self):
        self.level = len(self.init)

    def configure(self, force=False):
        old_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            for l in self.init:
                for c in l:
                    try:
                        self.command(c)
                    except Exception as e:
                        if not force:
                            raise
                        log.warning("Ignoring error: %s" % e)
                self.level+=1
        finally:
            signal.signal(signal.SIGINT, old_sigint)
    def deconfigure(self, force=False):
        old_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        try:
            while self.level:
                for c in self.fini[self.level-1]:
                    try:
                        self.command(c)
                    except Exception as e:
                        if not force:
                            raise
                        log.warning("Ignoring error: %s" % e)
                    self.level -= 1
        finally:
            signal.signal(signal.SIGINT, old_sigint)
