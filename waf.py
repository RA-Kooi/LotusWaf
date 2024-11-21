#!/usr/bin/env python3

VERSION="2.1.4"

import os, sys

wafdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "waf")

from waflib import Scripting
Scripting.waf_entry_point(os.getcwd(), VERSION, wafdir)
