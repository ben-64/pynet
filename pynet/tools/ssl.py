#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
from OpenSSL import crypto, SSL

def get_serial():
    return int(time.time() * 1000)

def split_cn(cn):
    """ cn : "/C=US/ST=California/L=Los Altos/O=Ouin, Inc./CN=*.toto.com """
    return dict([x.split("=") for x in cn.replace("/","\x00")[1:].split("\x00")])


def generate_unsigned_certificate(cn,subjaltname=None,ca=True,ksize=1024):
    """ Return cert unsigned and key """

    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, ksize)

    cert = crypto.X509()
    cert.set_version(2)

    cn = split_cn(cn)
    for k,v in cn.items():
        setattr(cert.get_subject(),k,v)

    cert.set_serial_number(get_serial())
    ten_years = 10*365*24*60*60
    cert.gmtime_adj_notBefore(-ten_years)
    cert.gmtime_adj_notAfter(ten_years)
    cert.set_pubkey(key)

    extensions = []

    if subjaltname:
        extensions.append(crypto.X509Extension(b"subjectAltName",False,b", ".join(subjaltname)))
    else:
        extensions.append(crypto.X509Extension(b"subjectAltName",False,b"DNS:%s" % (cn["CN"].encode("utf-8"),)))

    if ca:
        extensions.append(crypto.X509Extension(b'basicConstraints', True, b'CA:TRUE'))
    else:
        extensions.append(crypto.X509Extension(b'basicConstraints', True, b'CA:FALSE'))

    extensions.append(crypto.X509Extension(b'extendedKeyUsage', True, b'serverAuth,emailProtection,timeStamping'))
    extensions.append(crypto.X509Extension(b'keyUsage', False, b"digitalSignature, keyEncipherment"))
    extensions.append(crypto.X509Extension(b'subjectKeyIdentifier', False, b'hash', subject=cert))
    cert.add_extensions(extensions)

    return cert,key

def generate_certificate(cn,ca=None,cakey=None,subjaltname=None,ksize=4096):
    if ca is None or cakey is None:
        cert,key = generate_unsigned_certificate(cn,subjaltname,True,ksize)
        # Self-signed
        cert.add_extensions([crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid:always,issuer:always',issuer=cert)])
        cert.set_issuer(cert.get_subject())

        cert.sign(key, 'sha256')
    else:
        cert,key = generate_unsigned_certificate(cn,subjaltname,False,ksize)
        if not isinstance(ca,crypto.X509):
            try:
                ca = crypto.load_certificate(crypto.FILETYPE_ASN1,ca)
            except:
                ca = crypto.load_certificate(crypto.FILETYPE_PEM,ca)

            try:
                cakey = crypto.load_privatekey(crypto.FILETYPE_ASN1,cakey)
            except:
                cakey = crypto.load_privatekey(crypto.FILETYPE_PEM,cakey)
        cert.add_extensions([crypto.X509Extension(b'authorityKeyIdentifier', False, b'keyid:always,issuer:always',issuer=ca)])
        cert.set_issuer(ca.get_subject())

        cert.sign(cakey, 'sha256')

    cert = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
    key = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

    return cert,key

def generate_certificate_from_path(cn,capath=None,keypath=None,subjaltname=None,ksize=4096):
    if capath is None or keypath is None:
        return generate_certificate(cn,ca=None,cakey=None,subjaltname=subjaltname,ksize=ksize)
    else:
        ca = open(capath,"rb").read()
        key = open(keypath,"rb").read()
        return generate_certificate(cn,ca=ca,cakey=key,subjaltname=subjaltname,ksize=ksize)


if __name__ == "__main__":
    print(get_serial())
    with open(sys.argv[2],"wb") as f:
        cert,key = generate_certificate(sys.argv[1])
        f.write(cert)

