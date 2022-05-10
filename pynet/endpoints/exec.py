#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess,shlex
import pty
import tty
import fcntl

from pynet.endpoint import *

@Endpoint.register
class Exec(Endpoint):
    _desc_ = "Execute command"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--command","-c",metavar="COMMAND",required=True,help="Command to execute")

    def __init__(self,command,use_pty=True,*args,**kargs):
        super().__init__(*args,**kargs)
        self.use_pty = use_pty
        self.cmd = shlex.split(command)

        # Create a pty that will be given to the program
        # In order to avoid libc buffering
        self.master, self.slave = self.get_pty()

        self.stdin = subprocess.PIPE
        self.stdout = self.slave
        self.stderr = self.slave

    def init(self):
        self.start_cmd()

        self.process.stdout = os.fdopen(os.dup(self.master),'r+b', 0)
        self.process.stderr = os.fdopen(os.dup(self.master),'r+b', 0)
        os.close(self.master)
        os.close(self.slave)

        # Set non blocking mode
        fd = self.process.stdout.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def get_pty(self):
        master,slave = pty.openpty()
        tty.setraw(master)
        tty.setraw(slave)
        return master,slave

    def start_cmd(self):
        self.process = subprocess.Popen(self.cmd,shell=True,stdin=self.stdin,stdout=self.stdout,stderr=self.stdout)

    def send(self,data):
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def recv(self):
        data = self.process.stdout.read(4096)
        if self.process.poll() == 0:
            print("End command")
            raise EndpointClose()
        if not data or len(data) == 0:
            pass
        else:
            return data
