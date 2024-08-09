#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse

from pynet.plugin import Plugin
import pynet.endpoints as Endpoints
import pynet.proxys as Proxys
import pynet.modules as Modules

Endpoints.import_all()
Proxys.import_all()
Modules.import_all()

class PynetParser(object):
    def __init__(self,name,description="",plugins_cb=[]):
        self.name = name
        self.description = description
        self.plugins_cb = plugins_cb
        self.parser = self.create_parser()

    def load_dynamic_plugins(self):
        """ Load plugins located in --plugin-path folder command line """
        args,remain = self.parser.parse_known_args()

        # Import new plugins if necessary
        if args.plugin_path: self.import_plugin_dir(args.plugin_path)

        return args,remain

    def import_plugin_dir(self,path):
        """ Import python files from path """
        sys.path.append(path)
        for f in os.listdir(path):
            if f[-3:] == ".py":
                __import__(f[:-3],fromlist=["*"])

    def create_parser(self):
        """ The main big parser """
        parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description=f"{self.description}",add_help=False)
        parser.add_argument("--plugin-path",metavar="PATH",default=None,help="Where to find additionnal plugins")
        return parser

    def create_plugin_parser(self,parser,plugins):
        """ Add each parser for plugins """
        for plugin in plugins:
            plugin_parser = parser.add_parser(plugin.get_cmdline_name(),description="%s (%s) command line" % (plugin.get_cmdline_name(),plugin._desc_))
            # Temporary option taking what parse is not able to parse for now
            plugin_parser.add_argument("remain", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
            plugin.set_cli_arguments(plugin_parser)

    def parse(self):
        """ Parse the command line and generate classes and args """
        res = []
        args,remain = self.load_dynamic_plugins()

        if len(remain) == 1 and remain[0] in ("-h","--help"):
            h = ""
            for ptype,cb in self.plugins_cb:
                h += "%s => %s\n" % (ptype.ljust(15," ")," ".join(map(lambda x:x.get_cmdline_name(),filter(cb,Plugin.registerer.itervalues()))))
            self.parser.print_help()
            print(f"\n\n{h}")
            self.parser.exit(0)

        # Build nice suparser output
        for ptype,cb in self.plugins_cb:
            desc = "%s => %s\n" % (ptype.ljust(15," ")," ".join(map(lambda x:x.get_cmdline_name(),filter(cb,Plugin.registerer.itervalues()))))
        
            parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,description=desc)
            subparser = parser.add_subparsers(dest="plugin",metavar="",description=desc,title="Plugins to used : %s" % (", ".join(["%s" % x for x in map(lambda e:e[0],self.plugins_cb)])))
            p = list(filter(cb,Plugin.registerer.itervalues()))
            self.create_plugin_parser(subparser,p)

            args,remain = parser.parse_known_args(remain)
            if hasattr(args,"remain"): remain = args.remain + remain
            res.append(self.get_plugin_class(args))

        return res

    def get_plugin_class(self,args):
        def remove_keys(d,keys):
            for k in keys:
                d.pop(k,None)

        plugin_args = vars(args)
        plugin_cls = Plugin.registerer.get(plugin_args["plugin"])
        remove_keys(plugin_args,("plugin","plugin_path","remain"))
        return plugin_cls,plugin_args
