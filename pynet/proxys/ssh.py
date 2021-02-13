#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import getpass
import time
from threading import Thread

from pynet.tools.utils import remove_argument
from pynet.endpoint import *
from pynet.proxy import Proxy
from pynet.proxys.layer4 import TCPProxy
from pynet.endpoints.ssh import SSH,SSH_LISTEN,SSHChannel

try:
    import paramiko
except:
    print("paramiko not present, unable to load SSH endpoints")
    raise NotImplementedError


class SSHChannelProxyThread(Thread):
    def __init__(self,proxy):
        super().__init__()
        self.proxy = proxy

    def run(self):
        self.proxy.run() 


class SSHServerProxy(paramiko.ServerInterface,Endpoint):
    def __init__(self,client,debug=True):
        self.client = client
        self.chans = {}
        self.debug = debug

    def check_channel_request(self, kind, chanid):
        if self.debug: print("check_channel_request : %r %r" % (kind,chanid))
        client_channel = self.client._transport.open_session()
        self.chans[chanid] = client_channel
        return paramiko.OPEN_SUCCEEDED

    def check_auth_publickey(self, username, key):
        return paramiko.AUTH_SUCCESSFUL

    def check_auth_password(self, username, password):
        if self.debug: print("check_auth_password")
        return paramiko.AUTH_SUCCESSFUL

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_exec_request(self, channel, command):
        if self.debug: print("check_channel_exec_request: %r" % (command,))
        self.chans[channel.chanid].exec_command(command)
        return True

    def check_channel_forward_agent_request(self,channel):
        if self.debug: print("check_channel_forward_agent_request")
        paramiko.agent.AgentRequestHandler(self.chans[channel.chanid])
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        if self.debug: print("check_channel_pty_request %r" % (channel,))
        self.chans[channel.chanid].get_pty(term, width, height, pixelwidth, pixelheight)
        return True

    def check_channel_shell_request(self, channel):
        if self.debug: print("Channel shell request : %r" % (channel,))
        self.chans[channel.chanid].invoke_shell()
        return True


@Proxy.register
class SSHProxy(TCPProxy):
    """ Handle multiple SSH connections """
    _desc_ = "SSH Proxy"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        remove_argument(parser,"port")
        remove_argument(parser,"server_port")
        parser.add_argument("--port","-p",metavar="PORT",type=int,default=2222,help="Port to bind to (default 2222)")
        parser.add_argument("--server-port",metavar="PORT",default=22,type=int,help="Port Server to connect to, by default 22")
        parser.add_argument("--user","-U",metavar="USER",default=getpass.getuser(),help="User to connect with (default current user)")
        parser.add_argument("--password","-P",metavar="Password",help="Password to connect with")

    def __init__(self,user=getpass.getuser(),password=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.user = user
        self.password = password

    def init(self):
        self.client_side.init()

    def close(self):
        pass

    def create_client_side(self):
        return SSH_LISTEN(bind=self.host,port=self.port,transparent=self.transparent)

    def create_server_side(self,dest,dport,sport):
        return SSH(destination=dest,port=dport,user=self.user,password=self.password,exec_command=False,tty=False,src_port=sport,transparent=self.transparent,invoke_shell=False)

    def handle_new_tcp_connection(self,listening_channel,real_dst_addr=None):
        """ Handle a new data coming to the socket """

        # Create socket that will be exchanging data with the real server
        if self.mirror:
            sport = listening_channel.transport.sock.getpeername()[1]
        elif self.src_port:
            sport = self.src_port
        else:
            sport = None

        if self.transparent:
            dst_ip,dst_port = real_dst_addr
        else:
            dst_ip = self.server_ip
            dst_port = self.server_port if self.server_port else self.port

        endpoint_server = self.create_server_side(self.server_ip,self.server_port,sport)
        endpoint_server.init()
        ssh_server = SSHServerProxy(endpoint_server.ssh)
        try:
            listening_channel.transport.start_server(server=ssh_server)
        except paramiko.SSHException:
            print('*** SSH negotiation failed.')
            sys.exit(1)

        proxy = SSHChannelProxy(listening_channel,endpoint_server,ssh_server,module=self.modules[0])
        proxy_thread = SSHChannelProxyThread(proxy)
        proxy_thread.start()

    def run(self):
        self.init()
        while not self.stop:
            listening_channel,real_dst_addr = self.client_side.handle_new_tcp_client()
            self.handle_new_tcp_connection(listening_channel,real_dst_addr)


class SSHChannelProxy(Proxy):
    """ Handle multiple SSH channel inside a SSH connection """
    def __init__(self,ssh_listen,ssh,ssh_server,*args,**kargs):
        super().__init__(*args,**kargs)
        self.ssh_listen = ssh_listen
        self.ssh = ssh
        self.ssh_server = ssh_server

    def handle_new_channel(self,endpoint_client):
        endpoint_server = SSHChannel(self.ssh_server.chans[endpoint_client.channel.chanid])
        self.relay.add(endpoint_server,endpoint_client) 

    def run(self):
        while not self.stop:
            client = self.ssh_listen.handle_new_client()
            self.handle_new_channel(client)

