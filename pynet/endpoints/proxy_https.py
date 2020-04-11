#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import socket
import ssl
from io import BytesIO

from pynet.endpoint import *
from pynet.endpoints.socket import TCP_LISTEN,SOCKET
from pynet.endpoints.tls import TLS,TLS_LISTEN,tls_version
from pynet.tools.ssl import generate_certificate_from_path

def extract_addr_in_connect(data):
    data = data.split(b"\n")
    cmd,addr,http = data[0].split(b" ")
    dst,port = addr.split(b":")
    return dst,int(port)

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:65.0) Gecko/20100101 Firefox/65.0"

@Endpoint.register
class ProxyTLSClient(TLS):
    _desc_ = "Proxy HTTPS Sender"

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        parser.add_argument("--user-agent","-u",metavar="USERAGENT",default=UA,help="User-Agent to use")
        parser.add_argument("--proxy-destination",metavar="DESTINATION",help="Value for the HTTP CONNECT, default is the destination IP")
        parser.add_argument("--proxy-port",metavar="PORT",help="Value for the HTTP CONNECT port, default is the destination port")
        parser.add_argument("--no-tls",action="store_false",dest="tls",help="Do not use TLS")

    def __init__(self,user_agent=UA,proxy_destination=None,proxy_port=None,tls=True,*args,**kargs):
        super().__init__(*args,**kargs)
        self.ua = user_agent.encode("utf-8")
        self.proxy_destination = proxy_destination.encode("utf-8") if proxy_destination else self.destination.encode("utf-8")
        self.proxy_port = int(proxy_port) if proxy_port else self.port
        self.tls = tls

    def create_socket(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    def connect(self):
        try:
            self.sock.connect(self.connect_addr)
        except ConnectionRefusedError:
            print("Connection refused")
            sys.exit(0)

        destination = b"%s:%u" % (self.proxy_destination,self.proxy_port)
        self.sock.send(b'CONNECT %b HTTP/1.1\r\nUser-Agent: %s\r\nProxy-Connection: keep-alive\r\nConnection: keep-alive\r\nHost: %b\r\n\r\n' % (destination,self.ua,destination))
        res = self.sock.recv(4096)
        if self.tls:
            self.sock = ssl.wrap_socket(self.sock,ssl_version=tls_version[self.tls_version],ciphers=self.ciphers)

@Endpoint.register
class ProxyTLSServer(TLS_LISTEN):
    _desc_ = "Proxy HTTPS Receiver"

    def create_socket(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)

    def accept(self):
        csock,caddr = self.sock.accept()
        #print("New client: %r" % (caddr,))
        return SOCKET(sock=csock)

    def handle_new_client(self):
        """ Handle the connection of a new client """
        while True:
            endpoint_client = self.accept()
            data = endpoint_client.sock.recv(4096)

            print("DATA:%r" % (data,))
            try:
                addr = extract_addr_in_connect(data)
            except:
                print("Unable to get addr : %r" % (data,))
                continue
            endpoint_client.sock.send(b"HTTP/1.1 200 Connection Established\r\n\r\n")

            print("REDIRECTING for %r" % (addr,))

            name = "/CN=%s" % (addr[0].decode("utf-8"),)
            #name = '/C=US/ST=California/L=Los Altos/O=Netskope, Inc./CN=*.goskope.com'

            cert,key = generate_certificate_from_path(name,capath=self.certificate,keypath=self.key)


            certfile=b"/tmp/cert_%s.der" % addr[0]
            open(certfile,"wb").write(cert)

            keyfile=b"/tmp/key_%s.der" % addr[0]
            open(keyfile,"wb").write(key)

            try:
                endpoint_client.sock = ssl.wrap_socket(endpoint_client.sock,keyfile=keyfile,certfile=certfile,ssl_version=tls_version[self.tls_version],ciphers=self.ciphers,server_side=True)
                return endpoint_client,addr
            except ssl.SSLError as e:
                print("Error during client connection [%s] aborting..." % (e.reason,))
