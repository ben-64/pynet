#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pynet.proxy import Proxy
from pynet.endpoints.tls import TLS
from pynet.endpoints.proxy_https import ProxyTLSClient,ProxyTLSServer
from pynet.proxys.tls import TLSProxy

@Proxy.register
class HTTPSProxy(TLSProxy):
    CLIENT_ENDPOINT = ProxyTLSServer
    SERVER_ENDPOINT = TLS

    def __init__(self,*args,**kargs):
        super().__init__(*args,**kargs)

    def create_client_side(self):
        return self.CLIENT_ENDPOINT(bind=self.host,port=self.port,certificate=self.certificate,key=self.key,tls_version=self.tls_version,tls_ciphers=self.tls_ciphers)

    def create_server_side(self,dest,dport):
        return self.SERVER_ENDPOINT(destination=dest,port=dport,tls_version=self.tls_version,tls_ciphers=self.tls_ciphers)


    def handle_new_connection(self,endpoint_client,real_dst_addr):
        """ Handle a new data coming to the socket """
        dst_ip,dst_port = real_dst_addr

        endpoint_server = self.create_server_side(dst_ip,dst_port)
        endpoint_server.init()

        self.forwarder.replay(endpoint_client,endpoint_server)
