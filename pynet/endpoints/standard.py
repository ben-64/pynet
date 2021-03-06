#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import select

from pynet.endpoint import *

@Endpoint.register
class STDIN(InputEndpoint):
    _desc_ = "Input standard"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--size","-s",metavar="INTEGER",type=int,help="Size to read")

    def __init__(self,size=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.size = size
        self.stop = False

    def recv(self):
        """ Call to receive data """
        while not self.stop:
            while sys.stdin in select.select([sys.stdin],[],[],0.5)[0]:
                data = sys.stdin.buffer.readline()
                if len(data) == 0:
                    raise EndpointClose()
                return data
            else:
                pass

    def close(self):
        self.stop = True


@Endpoint.register
class DEVNULL(OutputEndpoint):
    _desc_ = "Ignore data"
    pass


@Endpoint.register
class STDOUT(OutputEndpoint):
    _desc_ = "Output standard"

    def send(self,data):
        sys.stdout.buffer.write(data)
        sys.stdout.flush()


@Endpoint.register
class STANDARD(STDIN,STDOUT):
    _desc_ = "Input/Output standard"
    _cmd_ = "-"
    EP1 = True
    EP2 = True

    def close(self):
        self.stop = True
