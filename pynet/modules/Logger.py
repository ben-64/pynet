#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import time
import json
from base64 import b64encode
from pynet.module import Module,PassThrough

COLOR_END = '\033[0m'

def hexdump(direction,s,color="",size=16):
    """ Hexdump data """
    def out(c):
        if c < 32 or c > 126: sys.stdout.write(".")
        else: sys.stdout.write(chr(c))

    s = list(s)
    sys.stdout.write("%s%s " % (color,direction))
    for i in range(len(s)):
        sys.stdout.write("%02x " % (s[i],))
        if i != 0 and i%size == size-1:
            sys.stdout.write("\t\t|")
            for j in range(i-size+1,i+1):
                out(s[j])
            sys.stdout.write("|\n%s " % direction)
    l = len(s)
    m = l%size
    sys.stdout.write("%s\t\t|" % (" "*(size-m)*3,))
    for i in range(l-m,l):
        out(s[i])
    sys.stdout.write("%s|\n" % (" "*(size-m),))
    sys.stdout.write(COLOR_END)

def get_ansi_color(s):
    return "\033[%sm" % (s,)

def output(direction,s,color=""):
    print("%s%s %s%s" % (color,direction,s,COLOR_END))

def encode_pkt(pkt):
    """ Encode a bytes pkt for storing it in a json file """
    return b64encode(pkt).decode("ascii")

@Module.register
class Logger(PassThrough):
    _desc_ = "Printer module"

    @classmethod
    def set_cli_arguments(cls,parser):
        PassThrough.set_cli_arguments(parser)
        parser.add_argument("--no-log-request",action="store_true",help="Do not print requests done by client")
        parser.add_argument("--no-log-response",action="store_true",help="Do not print responses sent by server")
        parser.add_argument("--no-hex",action="store_false",dest="hex",help="Do not print data in hexa")
        parser.add_argument("--color-client",metavar="COLOR",default="31",type=get_ansi_color,help="Color for client communication (default=31)")
        parser.add_argument("--color-server",metavar="COLOR",default="32",type=get_ansi_color,help="Color for client communication (default=32)")
        parser.add_argument("--no-color","-N",action="store_false",dest="color",help="Do not use colors")
        parser.add_argument("--output","-o",metavar="json",dest="output_json",help="Output json file")

    def __init__(self,no_log_request=False,no_log_response=False,hex=True,color=True,color_client="\033[31m",color_server="\033[32m",output_json=None,*args,**kargs):
        super().__init__(*args,**kargs)
        self.log_request = not no_log_request
        self.log_response = not no_log_response
        if output_json and os.path.exists(output_json): os.remove(output_json)
        self.fout = output_json
        if hex:
            self.output = hexdump
        else:
            self.output = output
        if color:
            self.color_client = color_client
            self.color_server = color_server
        else:
            self.color_client = ""
            self.color_server = ""

    def store(self,data,one):
        try:
            with open(self.fout,"r") as f:
                d = json.loads(f.read())
        except:
            d = []

        pkt = [{"one":one,"ts":time.time(),"data":encode_pkt(data)}]
        d.extend(pkt)

        with open(self.fout,"w") as f:
            json.dump(d,f)
        
    def handle(self,data,one):
        if self.log_request and one:
            self.output(">",data,color=self.color_client)
        elif self.log_response and not one:
            self.output("<",data,color=self.color_server)
        if self.fout: self.store(data,one)
        return data
