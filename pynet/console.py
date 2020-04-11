#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import sys
from ipykernel.kernelapp import IPKernelApp
from ipykernel.ipkernel import IPythonKernel
from traitlets import Type
from ipython_genutils.importstring import import_item
import logging
from IPython.utils.frame import extract_module_locals

# Kernel that does not handle signal, because it won't run in the main thread
class MyIPKernel(IPythonKernel):
    def pre_handler_hook(self):
        pass

    def post_handler_hook(self):
        pass

# App using our own kernel, avoid modifying stdin,stdout and stderr
# Avoir handling signal, because it won't run in the main thread
class MyIPKernelApp(IPKernelApp):
    kernel_class=Type(MyIPKernel)
    def init_io(self):
        if self.displayhook_class:
            displayhook_factory = import_item(str(self.displayhook_class))
            self.displayhook = displayhook_factory(self.session, self.iopub_socket)
            sys.displayhook = self.displayhook
    def init_signal(self):
        pass

# Exactly the same as ipykernel/embed.py, but use our own App instead of IPKernelApp
def my_embed_kernel(module=None, local_ns=None, **kwargs):
    # get the app if it exists, or set it up if it doesn't
    if IPKernelApp.initialized():
        app = MyIPKernelApp.instance()
    else:
        app = MyIPKernelApp.instance(**kwargs)
        app.initialize([])
        # Undo unnecessary sys module mangling from init_sys_modules.
        # This would not be necessary if we could prevent it
        # in the first place by using a different InteractiveShell
        # subclass, as in the regular embed case.
        main = app.kernel.shell._orig_sys_modules_main_mod
        if main is not None:
            sys.modules[app.kernel.shell._orig_sys_modules_main_name] = main

    # load the calling scope if not given
    (caller_module, caller_locals) = extract_module_locals(1)
    if module is None:
        module = caller_module
    if local_ns is None:
        local_ns = caller_locals

    app.kernel.user_module = module
    app.kernel.user_ns = local_ns
    app.shell.set_completer_frame()
    app.start()

class MyIPythonThread(threading.Thread):
    proxy = None

    def run(self):
        ns = {"proxy":self.proxy}
        my_embed_kernel(local_ns=ns)

def start_console(proxy):
    """Function that gets called when client code calls config.include"""
    t = MyIPythonThread()
    t.proxy = proxy
    t.start()
    return t
