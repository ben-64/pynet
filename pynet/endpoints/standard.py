#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import select
import tty
import termios
from queue import Queue

from pynet.endpoint import *


@Endpoint.register
class STDIN(InputEndpoint):
    _desc_ = "Input standard"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--raw","-r",action="store_true",help="Send character by character")

    def __init__(self,raw=False,*args,**kargs):
        super().__init__(*args,**kargs)
        self.old_term_attr = None
        self.stop = False
        self.raw = raw
        if raw:
            self.remove_newline_needed()

    def remove_newline_needed(self):
        self.old_term_attr = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)

    def recover_newline_needed(self):
        if self.old_term_attr:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_term_attr)

    def get(self):
        if self.raw:
            d = sys.stdin.buffer.read(1)
            sys.stdout.buffer.write(d)
            sys.stdout.flush()
            if d == b"\x03":
                self.recover_newline_needed()
                raise EndpointClose()
            return d
        return sys.stdin.buffer.readline()

    def recv(self):
        """ Call to receive data """
        while not self.stop:
            while sys.stdin in select.select([sys.stdin],[],[],0.5)[0]:
                data = self.get()
                if len(data) == 0:
                    raise EndpointClose()
                return data
            else:
                pass
        raise EndpointClose()

    def close(self):
        self.stop = True
        self.recover_newline_needed()


@Endpoint.register
class DEVNULL(Endpoint):
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


@Endpoint.register
class ECHO(Endpoint):
    _desc_ = "Returns what it receives"
    _cmd_ = "ECHO"

    def __init__(self,*args,**kargs):
        super().__init__(*args,**kargs)
        self.q = Queue()

    def send(self,data):
        self.q.put_nowait(data)

    def recv(self):
        return self.q.get()

    def close(self):
        self.q.put_nowait(None)
 
