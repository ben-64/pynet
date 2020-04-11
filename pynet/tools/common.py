#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

PYNET_FOLDER=os.path.expanduser("~/.pynet/")

def create_pynet_folder():
    if not os.path.exists(PYNET_FOLDER):
        os.makedirs(PYNET_FOLDER)
