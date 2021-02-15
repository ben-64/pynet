#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import select
import readline
from queue import Queue
from threading import Lock

from pynet.endpoint import *

@Endpoint.register
class CmdLine(Endpoint):
    _desc_ = "CMDLINE"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--rc-file","-i",metavar="PATH",help="Command to execute when connection is done")
        parser.add_argument("--log","-l",metavar="PATH",help="Everything that will be typed and received will be logged in that file")
 
    def __init__(self,rc_file=None,log=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.rc_file = rc_file
        self.log = log
        self.q = Queue()
        self.log_lock = Lock()

    def write_log(self,data):
        if self.log:
            self.log_lock.acquire()
            with open(self.log,"a+b") as f:
                f.write(data)
            self.log_lock.release()

    def exec_rc_commands(self):
        if self.rc_file:
            with open(self.rc_file,"r") as f:
                cmds = f.readlines()
            for cmd in cmds:
                self.q.put_nowait(cmd)

    def init(self):
        self.exec_rc_commands()

    def recv_stdin(self):
        return input() + "\n"

    def _cmd_recv(self):
        if self.q.qsize() > 0:
            return self.q.get()
        else:
            return self.recv_stdin()

    def recv(self):
        """ Call to receive data """
        line = self._cmd_recv()
        x = line.split(" ")
        cmd,args = x[0].strip("\n")," ".join(x[1:]).strip("\n")
        if hasattr(self,"do_" + cmd):
            getattr(self,"do_" + cmd)(args)
        else:
            line = line.encode()
            self.write_log(line)
            return line

    def send(self,data):
        self.write_log(data)
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()

    def do_quit(self,args):
        self.do_close()
