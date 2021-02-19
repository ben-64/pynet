#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import socket
import ssl

from pynet.endpoint import Endpoint
from pynet.endpoints.socket import TCP,TCP_LISTEN
from pynet.tools.common import PYNET_FOLDER,create_pynet_folder
from pynet.tools.ssl import generate_certificate

tls_version = {"SSLv23":ssl.PROTOCOL_SSLv23,
               "TLS" :ssl.PROTOCOL_TLS,
               "TLSv1" :ssl.PROTOCOL_TLSv1,
               "TLSv1_2" : ssl.PROTOCOL_TLSv1_2}

CA=os.path.join(PYNET_FOLDER,"pynet_ca.pem")
CAKEY=os.path.join(PYNET_FOLDER,"pynet_key.pem")

def create_certificate(cpath,kpath):
    create_pynet_folder()
    print("Generating pynet certificate/key inside %r" % (cpath,))
    cert,key = generate_certificate("/CN=pynet CA")
    open(cpath,"wb").write(cert)
    open(kpath,"wb").write(key)

@Endpoint.register
class TLS(TCP):
    _desc_ = "TLS Client"

    @classmethod
    def set_cli_arguments(cls,parser):
        TCP.set_cli_arguments(parser)
        tls = parser.add_argument_group('TLS',"TLS specific options")
        tls.add_argument("-c","--certificate",metavar="PATH",help="Certificate file for client authentication")
        tls.add_argument("-k","--key",metavar="PATH",help="Key file for client authentication")
        tls.add_argument("--tls-version",metavar="TLS_VERSION",default="TLSv1_2",help="TLS Version to used between : %s" % ",".join([k for k in tls_version]))
        tls.add_argument("--tls-ciphers","-C",metavar="CIPHERS",default="ALL",help="Ciphers available")

    def __init__(self,tls_version="TLSv1_2",tls_ciphers="ALL",certificate=None,key=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.tls_version = tls_version
        self.ciphers = tls_ciphers
        self.certificate = certificate
        self.key = key

    def create_socket(self):
        tcp_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock = ssl.wrap_socket(tcp_sock,keyfile=self.key,certfile=self.certificate,ssl_version=tls_version[self.tls_version],ciphers=self.ciphers)


@Endpoint.register
class TLS_LISTEN(TCP_LISTEN):
    _cmd_ = "TLS-LISTEN"
    _desc_ = "TLS Server"

    @classmethod
    def set_cli_arguments(cls,parser):
        TCP_LISTEN.set_cli_arguments(parser)
        tls = parser.add_argument_group('TLS',"TLS specific options")
        tls.add_argument("-c","--certificate",metavar="PATH",default=CA,help="Certificate file")
        tls.add_argument("-k","--key",metavar="PATH",default=CAKEY,help="Key file")
        tls.add_argument("--tls-version",metavar="TLS_VERSION",default="TLSv1_2",help="TLS Version to used between : %s" % ",".join([k for k in tls_version]))
        tls.add_argument("--tls-ciphers","-C",metavar="CIPHERS",default="ALL",help="Ciphers available")

    def __init__(self,certificate=CA,key=CAKEY,tls_version="TLSv1_2",tls_ciphers="ALL",*args,**kargs):
        super().__init__(*args,**kargs)
        if not os.path.exists(certificate):
            if os.path.exists(key):
                print("Cert does not exist, but key exists, exiting")
                sys.exit(1)
            create_certificate(certificate,key)
        self.certificate = certificate
        self.key = key
        self.tls_version = tls_version
        self.ciphers = tls_ciphers

    def get_conf(self):
        """ Use if we need to duplicate EndPoint, to keep the mandatory parameters """
        return {"proto":self.proto, "certificate":self.certificate, "key":self.key, "tls_version":self.tls_version, "ciphers":self.ciphers}

    def create_socket(self):
        tcp_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock = ssl.wrap_socket(tcp_sock,keyfile=self.key,certfile=self.certificate,ssl_version=tls_version[self.tls_version],ciphers=self.ciphers)

    def accept(self):
        while True:
            try:
                return super().accept()
            except ssl.SSLError as e:
                print("Error during client connection [%s] aborting..." % (e.reason,))
