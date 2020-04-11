#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import array
import random
from pynet.module import Module,PassThrough

# Taken from scapy : scapy/utils.py
def corrupt_bytes(s, p=0.01, n=None):
    """Corrupt a given percentage or number of bytes from a string"""
    s = array.array("B",s)
    l = len(s)
    if n is None:
        n = max(1,int(l*p))
    for i in random.sample(range(l), n):
        s[i] = (s[i]+random.randint(1,255))%256
    return s.tobytes()

# Taken from scapy : scapy/utils.py
def corrupt_bits(s, p=0.01, n=None):
    """Flip a given percentage or number of bits from a string"""
    s = array.array("B",s)
    l = len(s)*8
    if n is None:
        n = max(1,int(l*p))
    for i in random.sample(range(l), n):
        s[int(i/8)] ^= 1 << (i%8)
    return s.tobytes()

@Module.register
class Corrupt(PassThrough):
    _desc_ = "Corruption Module"

    @classmethod
    def set_cli_arguments(cls,parser):
        parser.add_argument("--seed",metavar="SEED",type=int,help="Set seed for random values to be reproductible")
        parser.add_argument("--bytes","-B",action="store_true",help="If set then corrupt byte will be set instead of corrupt bits")
        parser.add_argument("--number","-n",metavar="NUMBER",default=None,type=int,help="Number of bits/bytes fuzzed inside a packet")
        parser.add_argument("--percentage","-c",metavar="PERCENTAGE",default=0.01,type=float,help="Percentage of bits/bytes fuzzed inside a packet (will be override by number if set)")
        parser.add_argument("--request",action="store_true",help="Will corrupt request to fuzz server")
        parser.add_argument("--response",action="store_true",help="Will corrupt response to fuzz client")
        parser.add_argument("--both",action="store_true",help="Will corrupt request and response to fuzz respectively server and client")

    def __init__(self,*args,**kargs):
        super().__init__(*args,**kargs)
        if self.args.bytes:
            self.corrupt = corrupt_bytes
        else:
            self.corrupt = corrupt_bits

        self.number = self.args.number
        self.percentage = self.args.percentage

        self.corrupt_request = self.args.both or self.args.request
        self.corrupt_response = self.args.both or self.args.response

        # To be reproductible
        if not self.args.seed is None:
            random.seed(self.args.seed)

    def do_corrupt(self,data):
        return self.corrupt(data,self.percentage,self.number)

    def handle(self,data,one):
        if self.corrupt_request and one:
            data = self.do_corrupt(data)
        elif self.corrupt_response and not one:
            data = self.do_corrupt(data)
        return data
