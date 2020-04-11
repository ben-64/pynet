#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import getpass
import socket
import threading
import time
from pprint import pprint
from queue import Queue
try:
    import paramiko
except:
    print("paramiko not present, unable to load SSH endpoints")
    raise NotImplementedError

from pynet.tools.utils import remove_argument
from pynet.endpoint import *
from pynet.endpoints.socket import TCP,TCP_LISTEN
from pynet.tools.common import PYNET_FOLDER,create_pynet_folder

HOST_KEY=os.path.join(PYNET_FOLDER,"host_rsa_key")

def create_host_key(path):
    import subprocess

    if not os.path.exists(PYNET_FOLDER):
        create_pynet_folder()

    try:
        subprocess.check_call("ssh-keygen -t rsa -b 2048 -f %s -q -N ''" % (path,),shell=True)
    except:
        print("Unable to create host key...")
        raise
        sys.exit(1)


@Endpoint.register
class SSH(TCP):
    _desc_ = "SSH Client"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        remove_argument(parser,"port")
        parser.add_argument("--port","-p",metavar="PORT",type=int,default=22,help="Destination port")
        parser.add_argument("--user","-U",metavar="USER",default=getpass.getuser(),help="User to connect with (default current user)")
        parser.add_argument("--password","-P",metavar="Password",help="Password to connect with")
        parser.add_argument("--tty",action="store_true",help="Ask for a TTY")
        parser.add_argument("--exec-command",action="store_true",help="Run exec command instead of invoke_shell")
        parser.add_argument("--no-invoke-shell",action="store_false",dest="invoke_shell",help="Run invoke_shell")

    def __init__(self,port=22,user=getpass.getuser(),password=None,exec_command=False,invoke_shell=True,tty=False,*args,**kargs):
        super().__init__(port=port,*args,**kargs)
        self.user = user
        self.password = password
        self.tty = tty
        self.exec_command = exec_command
        self.invoke_shell = invoke_shell

        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.WarningPolicy)

        self.out = Queue()

    def connect(self):
        super().connect()
        try:
            self.ssh.connect(self.destination,port=self.port,username=self.user,password=self.password,sock=self.sock)
        except:
            print("Unable to connect to %s:%s" % (self.destination,self.port))

    def init(self):
        super().init()
        if self.exec_command:
            self.shell_channel = None
        elif self.invoke_shell:
            self.shell_channel = self.ssh.invoke_shell()
            self.stdin_shell = self.shell_channel.makefile('wb')
            self.stdout_shell = self.shell_channel.makefile('r')

    def close(self):
        self.ssh.close()

    def send(self,data):
        try:
            if self.exec_command:
                i,o,e = self.ssh.exec_command(data,get_pty=self.tty)
                self.out.put(o.read())
            elif self.invoke_shell:
                self.shell_channel.send(data)
        except:
            self.close()
            raise EndpointClose()

    def recv(self):
        if self.exec_command:
            data = self.out.get()
        elif self.invoke_shell:
            data = self.shell_channel.recv(4096)
        return data


class SSHServer(paramiko.ServerInterface,Endpoint):
    def __init__(self):
        self.data = Queue()
        self.shell_request = False

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_exec_request(self, channel, command):
        return True

    def check_channel_forward_agent_request(self,channel):
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        return True




@Endpoint.register
class SSH_LISTEN(TCP_LISTEN):
    _desc_ = "SSH Server"

    def __init__(self,*args,**kargs):
        super().__init__(*args,**kargs)
        if not os.path.exists(HOST_KEY):
            create_host_key(HOST_KEY)
        self.host_key = paramiko.RSAKey(filename=HOST_KEY)
    
    def handle_new_tcp_client(self):
        endpoint_client,real_dst_addr = super().handle_new_client()
        transport = paramiko.Transport(endpoint_client.sock)
        transport.set_gss_host(socket.getfqdn(""))
        transport.load_server_moduli()
        transport.add_server_key(self.host_key)
        return SSHListeningChannel(transport),real_dst_addr

    def handle_new_client(self):
        """ Handle the connection of a new client """
        channel,real_dst_addr = self.handle_new_tcp_client()

        ssh_server = SSHServer()

        try:
            channel.transport.start_server(server=ssh_server)
        except paramiko.SSHException:
            print('*** SSH negotiation failed.')
            sys.exit(1)

        return channel.accept(),real_dst_addr


class SSHListeningChannel(Endpoint):
    def __init__(self,transport):
        self.transport = transport

    def accept(self):
        channel = self.transport.accept(20)
        if channel is None:
            print("*** No channel")
            sys.exit(1)
        return SSHChannel(channel)

    def handle_new_client(self):
        chan = self.accept()
        return chan
        
    def recv(self):
        data = self.channel.recv(4096)

        if len(data) == 0:
            self.close()
            raise EndpointClose()

        return data

    def send(self,data):
        try:
            self.channel.sendall(data)
            #print("Sent : %r" % (data,))
        except:
            self.close()
            raise EndpointClose()


class SSHChannel(Endpoint):
    def __init__(self,channel):
        self.channel = channel

    def close(self):
        self.channel.shutdown(2)
        self.channel.close()

    def recv(self):
        data = self.channel.recv(4096)

        if len(data) == 0:
            self.close()
            raise EndpointClose()

        return data

    def send(self,data):
        try:
            self.channel.sendall(data)
        except:
            self.close()
            raise EndpointClose()
