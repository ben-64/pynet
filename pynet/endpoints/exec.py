#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess,shlex
from threading import Event

from pynet.endpoint import *

@Endpoint.register
class Exec(Endpoint):
    _desc_ = "Execute command"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--command","-c",metavar="COMMAND",required=True,help="Command to execute")

    def __init__(self,command,*args,**kargs):
        super().__init__(*args,**kargs)
        self.cmd = shlex.split(command)
        self.is_cmd_running = Event()
        self.is_cmd_running.clear()

    def init(self):
        if not self.is_cmd_running.is_set():
            self.start_cmd()

    def start_cmd(self):
        self.process = subprocess.Popen(self.cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        os.set_blocking(self.process.stdout.fileno(), False)
        self.is_cmd_running.set()

    def send(self,data):
        self.process.stdin.write(data)
        self.process.stdin.flush()

    def recv(self):
        while self.is_cmd_running.wait(0.5):
            data = self.process.stdout.read()
            if self.process.poll() == 0:
                print("End command")
                raise EndpointClose()
            if not data or len(data) == 0:
                pass
                #self.is_cmd_running.clear()
            else:
                return data
