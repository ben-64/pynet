#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from pynet.proxy import Proxy
from pynet.proxys.layer4 import TCPProxy
from pynet.endpoints.tls import TLS,TLS_LISTEN,tls_version,CA,CAKEY

@Proxy.register
class TLSProxy(TCPProxy):
    _desc_ = "TLS Proxy"
    CLIENT_ENDPOINT = TLS_LISTEN
    SERVER_ENDPOINT = TLS

    @classmethod
    def set_cli_arguments(cls,parser):
        super().set_cli_arguments(parser)
        tls = parser.add_argument_group('TLS',"TLS specific options")
        tls.add_argument("-c","--certificate",metavar="PATH",default=CA,help="Certificate file")
        tls.add_argument("-k","--key",metavar="PATH",default=CAKEY,help="Key file")
        tls.add_argument("-C","--client-certificate",metavar="PATH",help="Certificate file for client authentication")
        tls.add_argument("-K","--client-key",metavar="PATH",help="Key file for client authentication")
        tls.add_argument("--tls-version",metavar="TLS_VERSION",default="TLSv1_2",help="TLS Version to used between : %s" % ",".join([k for k in tls_version]))
        tls.add_argument("--tls-ciphers",metavar="CIPHERS",default="ALL",help="Ciphers available")

    def __init__(self,certificate,key,client_certificate=None,client_key=None,tls_version="TLSv1_2",tls_ciphers="ALL",*args,**kargs):
        self.certificate = certificate
        self.key = key
        self.client_certificate = client_certificate
        self.client_key = client_key
        self.tls_version = tls_version
        self.tls_ciphers = tls_ciphers
        super().__init__(*args,**kargs)

    def create_client_side(self):
        return self.CLIENT_ENDPOINT(bind=self.host,port=self.port,certificate=self.certificate,key=self.key,tls_version=self.tls_version,tls_ciphers=self.tls_ciphers)

    def create_server_side(self,dest,dport,sport):
        return self.SERVER_ENDPOINT(destination=dest,port=dport,src_port=sport,certificate=self.client_certificate,key=self.client_key,tls_version=self.tls_version,tls_ciphers=self.tls_ciphers)
