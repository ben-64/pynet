#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
from threading import Thread
from select import select

import logging

from pynet.tools.utils import Register
from pynet.module import Module
from pynet.endpoint import EndpointClose

logger = logging.getLogger("Forwarder")
logger.setLevel(logging.WARNING)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


class Forwarder(object):
   
    def __init__(self,ep1,ep2,modules=[],end_forwarder_callback=None):
        self.modules = list(map(lambda m:m.get(ep1,ep2),modules))
        self.ep1 = ep1
        self.ep2 = ep2
        self.callback_end = end_forwarder_callback
        logger.debug("New forwarder [%r:%r]" % (self.ep1,self.ep2))

    @staticmethod
    def is_forward_possible(ep1,ep2):
        return hasattr(ep1,"recv") and hasattr(ep2,"send")

    def fw(self,receiver,sender,from_client):
        """ Forward between receiver and sender. Return True if the communication has ended """
        try:
            data = receiver.proto_recv()
            logger.debug("Received data from %r [%r]" % (receiver,data))
        except EndpointClose:
            logger.debug("Receiver %r has closed, closing sender %r" % (receiver,sender))
            sender.do_close()
            return True

        # If endpoint returns None, we won't send it to modules
        if data is None: return False

        if not type(data) is list:
            data = [data]

        for msg in data:
            msg = self.handle_data(msg,from_client)

            # If Module returns None, it means that this packet won't be forwarded
            if msg is None: return False

            try:
                sender.proto_send(msg)
                logger.debug("Sending data to %r" % (sender,))
            except EndpointClose:
                logger.debug("Sender %r has closed, closing receiver %r" % (sender,receiver))
                receiver.do_close()
                return True

        return False

    def handle_data(self,data,from_client):
        """ Function to transform data """
        for m in self.modules:
            data = m.handle(data,from_client)
        return data

    def start(self):
        raise NotImplementedError()

    def wait_until_end(self):
        raise NotImplementedError()

    def run(self):
        self.start()
        self.wait_until_end()

    def close(self):
        pass

    def is_active(self):
        return True

    def __repr__(self):
        return "%s(%s:%s)" % (self.__class__.__name__,self.ep1,self.ep2)


class ThreadForwarder(Forwarder):
    """ Forward date from ep1 to ep2 AND from ep2 to ep1 with two threads """

    class FwdThread(Thread):
        """ Thread forwarding data from ep1 to ep2 """
        def __init__(self,ep1,ep2,from_ep1,forwarder):
            super().__init__()
            self.ep1 = ep1
            self.ep2 = ep2
            self.from_ep1 = from_ep1
            self.forwarder = forwarder

        def run(self):
            while not self.forwarder.fw(self.ep1,self.ep2,self.from_ep1):
                pass
            self.forwarder.end_thread(self)

        def __repr__(self):
            return "%s(%s -> %s)" % (self.__class__.__name__,self.ep1,self.ep2)

    def start(self):
        # Creating and starting all necessary threads
        self.threads = []
        if Forwarder.is_forward_possible(self.ep1,self.ep2):
            self.threads.append(ThreadForwarder.FwdThread(self.ep1,self.ep2,True,self))
            logger.debug("Start fwd between %r and %r" % (self.ep1,self.ep2))

        if Forwarder.is_forward_possible(self.ep2,self.ep1):
            self.threads.append(ThreadForwarder.FwdThread(self.ep2,self.ep1,False,self))
            logger.debug("Start fwd between %r and %r" % (self.ep2,self.ep1))

        for th in self.threads:
            th.start()

    def wait_until_end(self):
        # Waiting for thread termination
        while len(self.threads) > 0:
            # It can have been already closed and removed from the list by end_thread
            try:
                self.threads[0].join()
                th = self.threads.pop(0)
                logger.debug("End fwd between %r and %r" % (th.ep1,th.ep2))
            except IndexError:
                pass

    def is_active(self):
        return len(self.threads) > 0

    def end_thread(self,thread):
        """ Callback called by a thread when it ends """
        try:
            # Might already have been removed
            self.threads.remove(thread)
        except ValueError:
            pass
        logger.debug("End fwd between %r and %r" % (thread.ep1,thread.ep2))

        # If there is no more threads, and a callback is defined, forwarder is terminated
        if self.callback_end and len(self.threads) == 0:
            self.callback_end(self)

    def close(self):
        # It can have been already closed and removed from the list in wait_until_end
        logger.debug("Closing forwarder [%r:%r]" % (self.threads[0].ep1,self.threads[0].ep2))
        try:
            self.threads[0].ep1.close()
            self.threads[0].ep2.close()
        except IndexError:
            pass
