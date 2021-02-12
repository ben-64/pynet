#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
from threading import Thread
from select import select

from pynet.tools.utils import Register
from pynet.module import Module
from pynet.endpoint import EndpointClose

class Forwarder(object):
    def __init__(self,modules=[]):
        self.modules = modules
        self.forwarding_client = {}
        self.forwarding_server = {}
        self.stop = False

    @staticmethod
    def is_forward_possible(sender,receiver):
        return True

    def add(self,client,server):
        # Instanciate modules
        modules = list(map(lambda m:m.get(client,server),self.modules))
        if Forwarder.is_forward_possible(client,server):
            self.forwarding_client[client] = server
            self.do_forward(client,server,modules)
        if Forwarder.is_forward_possible(server,client):
            self.forwarding_server[server] = client
            self.do_forward(server,client,modules)

    def remove(self,sender):
        if sender in self.forwarding_client:
            self.stop_forward(sender)
            sender.close()
            self.forwarding_client[sender].close()
            del(self.forwarding_client[sender])

        if sender in self.forwarding_server:
            self.stop_forward(sender)
            sender.close()
            self.forwarding_server[sender].close()
            del(self.forwarding_server[sender])

    def fw(self,receiver,sender,modules):
        """ Forward between receiver and sender. Return True if the communication has ended """
        try:
            data = receiver.proto_recv()
        except EndpointClose:
            return True

        # If endpoint returns None, we won't send it to modules
        if data is None: return False

        from_client = receiver in self.forwarding_client

        if not type(data) is list:
            data = [data]

        for msg in data:
            msg = self.handle_data(msg,from_client,modules)

            # If Module returns None, it means that this packet won't be forwarded
            if msg is None: return False

            try:
                sender.proto_send(msg)
            except EndpointClose:
                return True

        return False

    def handle_data(self,data,from_client,modules):
        """ Function to transform data """
        for m in modules:
            data = m.handle(data,from_client)
        return data

    def do_forward(self,sender,receiver,modules):
        pass

    def stop_forward(self,sender,receiver):
        pass

    def run(self):
        raise NotImplementedError()

    def close(self):
        pass


class ThreadForwarder(Forwarder):
    class FwdThread(Thread):
        def __init__(self,sender,receiver,modules,forwarder):
            super().__init__()
            self.sender = sender
            self.receiver = receiver
            self.forwarder = forwarder
            self.modules = modules
            self.stop = False

        def run(self):
            while not self.stop and not self.forwarder.fw(self.sender,self.receiver,self.modules):
                pass
            self.forwarder.remove(self.sender)

    def __init__(self,modules=[]):
        super().__init__(modules)
        self.threads = {}

    def do_forward(self,sender,receiver,modules):
        th = ThreadForwarder.FwdThread(sender,receiver,modules,self)
        self.threads[sender] = th
        th.start()

    def stop_forward(self,sender):
        th = self.threads[sender]
        th.stop = True
        del(self.threads[sender])

    def run(self):
        while not self.stop:
            time.sleep(1)

    def close(self):
        self.stop = True
        for sender,th in list(self.threads.items()):
            th.sender.close()
            th.receiver.close()
            th.stop = True
            th.join()


# class SelectForwarder(Forwarder):
#     def __init__(self,modules=[],timeout=3):
#         super().__init__(modules)
#         self.timeout = timeout
#         self.sockets = []

#     def do_forward(self,com):
#         self.sockets.append(com.e1)

#     def stop_forward(self,com):
#         self.sockets.remove(com.e1)

#     def run(self):
#         while not self.stop:
#             (read,write,error) = select.select(socks,[],socks,self.timeout)
#             if error:
#                 continue
#             elif read:
#                 for endpoint in read:
#                     com = self.forwarding[endpoint]
#                     data = self.handle_data(endpoint.recv(),com.client)
#                     com.e2.send(data)
