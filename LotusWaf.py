#!/usr/bin/env python3
# encoding: utf-8

import platform, sys, json, os, sysconfig

from waflib import Logs, TaskGen, Options
from waflib.Build import BuildContext
from waflib.Configure import conf, ConfigurationContext
from waflib.Options import OptionsContext
from waflib.TaskGen import feature, before_method, after_method, taskgen_method
from waflib.Tools import waf_unit_test
from waflib.Tools.ccroot import USELIB_VARS

from Common import *
from Configure import configure
from Options import options
from Build import build
