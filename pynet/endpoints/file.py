#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from pynet.endpoint import *

@Endpoint.register
class FILE(OutputEndpoint):
    _desc_ = "File"

    @classmethod
    def set_cli_arguments(cls,parser):
        InputEndpoint.set_cli_arguments(parser)
        parser.add_argument("--path","-p",metavar="PATH",help="File to write")
        parser.add_argument("--append","-a",action="store_true",help="Append to file")

    def __init__(self,path,append=False):
        super().__init__()
        self.path = path
        if not append: open(self.path,"w").close()

    def send(self,data):
        """ Call to receive data """
        with open(self.path,"a") as f:
            f.write(data.decode())
