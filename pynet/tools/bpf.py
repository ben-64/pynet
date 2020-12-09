#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import struct
import socket
import itertools

class BPFOPCODES:
    LD    = 0x20
    LDH   = 0x28
    LDB   = 0x30
    JEQ   = 0x15
    RET   = 0x06
    JSET  = 0x45
    LDXB  = 0xb1 # 4*([k]&0xf)
    LDH_X = 0x48


class BPFCmd(object):
    def __init__(self,opcode,value,labelt='',labelf='',label=None):
        self.opcode = opcode
        self.value = value
        self.labelt = labelt
        self.labelf = labelf
        self.label = label

    def get(self):
        h = {}
        if self.label: h["label"] = self.label
        h["opcode"] = self.opcode
        h["value"] = self.value
        if self.labelt: h["t"] = self.labelt
        if self.labelt: h["f"] = self.labelf
        return h

    def build(self,pos,labels):
        def compute_jump(labelpos):
            return labelpos-pos-1

        if self.labelt:
            if not self.labelt in labels:
                print("Unable to resolve %s" % (self.labelt,))
                labelt = 0
            else:
                labelt = compute_jump(labels[self.labelt])
        else:
            labelt = 0
        if self.labelf:
            if not self.labelf in labels:
                print("Unable to resolve %s" % (self.labelf,))
                labelf = 0
            else:
                labelf = compute_jump(labels[self.labelf])
        else:
            labelf = 0

        #print("0x%2x %u %u 0x%x" % (self.opcode,labelt,labelf,self.value))
        return struct.pack("HBBI",self.opcode,labelt,labelf,self.value)

    def __str__(self):
        s = []
        if self.label:
            s.append("%s" % (self.label.ljust(10," "),))
        else:
            s.append("%s" % (" ".ljust(10," "),))
        s.append("0x%x 0x%x" % (self.opcode,self.value,))
        if self.labelt:
            s.append("True:%s" % (self.labelt,))
        if self.labelf:
            s.append("False:%s" % (self.labelf,))
        return " ".join(s)


class BPFFilter(object):
    def __init__(self,cmds):
        self.cmds = cmds

    def __repr__(self):
        return "\n".join(map(str,self.cmds))

    def solve_labels(self):
        h = {}
        for i in range(len(self.cmds)):
            if self.cmds[i].label:
                h[self.cmds[i].label] = i
        return h

    def build(self):
        cmds = []
        labels = self.solve_labels()
        for i in range(len(self.cmds)):
            cmds.append(self.cmds[i].build(i,labels))
        return b"".join(cmds)


class BPFNetwork(object):
    """ Used to build a BPF filter """
    TCP =  0x6
    UDP = 0x11

    def __init__(self,host,port):
        self.host = host
        self.port = port

    def is_ipv4(self,true=None,false=None):
        return [
            BPFCmd(BPFOPCODES.LDH,0xc),
            BPFCmd(BPFOPCODES.JEQ,0x800,labelt=true,labelf=false)
        ]

    def is_proto(self,proto=TCP,label=None,true=None,false=None):
        return [
            BPFCmd(BPFOPCODES.LDB,0x17,label=label),
            BPFCmd(BPFOPCODES.JEQ,proto,labelt=true,labelf=false)
        ]

    def is_ipv4_host(self,host,path="src",label=None,true=None,false=None):
        offset = 0x1e if path == "dst" else 0x1a
        return [
            BPFCmd(BPFOPCODES.LD,offset,label=label),
            BPFCmd(BPFOPCODES.JEQ,int.from_bytes(socket.inet_aton(host),"big"),labelt=true,labelf=false),
        ]

    def is_ipv4_fragmented(self,label=None,true=None,false=None):
        return [
            BPFCmd(BPFOPCODES.LDH,0x14,label=label),
            BPFCmd(BPFOPCODES.JSET,0x1FFF,labelt=true,labelf=false)
        ]

    def is_port(self,port,path="dst",label=None,true=None,false=None):
        offset = 0x10 if path == "dst" else 0xe
        return [
            BPFCmd(BPFOPCODES.LDXB,0xe,label=label),  # Load in X the size of IP header
            BPFCmd(BPFOPCODES.LDH_X,offset),
            BPFCmd(BPFOPCODES.JEQ,port,labelt=true,labelf=false),
        ]

    def reject(self,label="reject"):
        return [
            BPFCmd(BPFOPCODES.RET,0,label=label)
        ]

    def allow(self,label="allow"):
        return [
            BPFCmd(BPFOPCODES.RET,0xFFFFFFFF,label=label)
        ]

    def build(self):
        r = [
            # Check IP protocol
            self.is_ipv4(false="allow"),

            # Check SRC IP and DST PORT
            self.is_ipv4_host(self.host,path="src",false="response"),
            self.is_ipv4_fragmented(true="allow"),
            self.is_port(self.port,path="dst",true="reject",false="allow"),

            # Check DST IP and SRC PORT
            self.is_ipv4_host(self.host,path="dst",label="response",false="allow"),
            self.is_ipv4_fragmented(true="allow"),
            self.is_port(self.port,path="src",true="reject",false="allow"),

            self.reject(),
            self.allow()
        ]

        return BPFFilter(list(itertools.chain.from_iterable(r))).build()

    def __repr__(self):
        return repr(self.build())
