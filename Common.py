#!/usr/bin/env python3
# encoding: utf-8

import json, os, platform, sys
from typing import Any, Dict, List, Union

from waflib.Configure import ConfigurationContext
from waflib.Options import OptionsContext

JSONType = Union[str, int, float, bool, None, Dict[str, any], List[Any]]

def normalized_join2(a: str, b: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.join(a, b)))
#enddef

def normalized_join3(a: str, b: str, c: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.join(a, b, c)))
#enddef

# Load the project configurations and return it as a dictionary
def get_config(cfg: Union[ConfigurationContext, OptionsContext]) -> JSONType:
    file = str()

    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.join('project_configurations.lotus_config')
    else:
        file = normalized_join2(cfg.top_dir, 'project_configurations.lotus_config')
    #endif

    with open(file, encoding='utf-8') as config_file:
        return json.loads(config_file.read())
    #endwith
#enddef

# Load the use flags file and return it as a dictionary
def get_use(cfg: Union[ConfigurationContext, OptionsContext]) -> JSONType:
    file = str()

    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.join('UseFlags', 'use_flags.lotus_use')
    else:
        file = normalized_join3(cfg.top_dir, 'UseFlags', 'use_flags.lotus_use')
    #endif

    with open(file, encoding='utf-8') as config_file:
        return json.loads(config_file.read())
    #endwith
#enddef

# Load the toolset passed to waf via --toolset and return it as a dictionary
def get_toolset(cfg: Union[ConfigurationContext, OptionsContext]) -> JSONType:
    file = str()

    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.join('Toolsets', cfg.env.cur_toolset + '.lotus_toolset')
    else:
        toolset_name = cfg.env.cur_toolset + '.lotus_toolset'
        file = normalized_join3(cfg.top_dir, 'Toolsets', toolset_name)
    #endif

    with open(file, encoding='utf-8') as toolset_file:
        return json.loads(toolset_file.read())
    #endwith
#enddef
