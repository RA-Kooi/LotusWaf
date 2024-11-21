#!/usr/bin/env python3
# encoding: utf-8

import argparse

from Common import *

# Show general help output when waf --help is executed
def load_configuration_options(config, opt):
    default_platform = sys.platform + '_x' + platform.machine()[-2:]

    platform_help ='Set the target platform you want to build for.\n' \
        + 'Default is the host platform. Possible platforms are ' \
        + config['target_platforms'][0] + ', '

    for i in range(1, len(config['target_platforms'])):
        platform_help += config['target_platforms'][i] + ', '
    #endfor

    opt.add_option(
        '--release',
        action='store_false',
        dest='development',
        default=True,
        help='Make a build for production, excludes flags like warning is error.')

    opt.add_option(
        '--target-platform',
        action='store',
        dest='target_platform',
        default=default_platform,
        help=platform_help)

    opt.add_option(
        '-c',
        '--target-configuration',
        action='store',
        dest='config',
        default=config['configurations'][0],
        help='Select the project configuration to use. '
        + 'Valid configurations are %r [default: %s]'
        % (config['configurations'], config['configurations'][0]))

    toolset_help = 'R|Select the toolset to use for compiling. Valid toolsets are:\n'
    for _platform in config['toolsets']:
        toolset_help = toolset_help + '{\n\tplatform: ' + _platform + ': '

        toolset_help += '\n\ttoolsets: ['
        for _toolset in config['toolsets'][_platform]:
            toolset_help += _toolset + ', '
        #endfor

        toolset_help = toolset_help[:-2] + ']'
        toolset_help += '\n},\n'
    #endfor

    if default_platform in config['toolsets']:
        toolset_help = toolset_help[:-2] + '\n[default: %s]' \
                % config['toolsets'][default_platform][0]

        opt.add_option(
            '--toolset',
            action='store',
            dest='toolset',
            default=config['toolsets'][default_platform][0],
            help=toolset_help)
    else:
        print(
            'No platform defined with the name ' \
            + default_platform \
            + ', unable to print toolset help.')
    #endif
#enddef

# Show use specific help output when waf --help is executed
def load_use_options(config, opt):
    from optparse import OptionGroup
    use = get_use(opt)

    group = opt.add_option_group('Library options')

    for use_flag in use:
        if use[use_flag]['type'] == 'flags':
            continue
        #endif

        if not 'common' in use[use_flag]:
            opt.fatal('Missing common block in use[' + use_flag + '].')
        #endif

        if not 'optional' in use[use_flag]['common']:
            opt.fatal('Missing optional in use[' + use_flag + '][\'common\'].')
        #endif

        if use[use_flag]['common']['optional'] == True:
            group.add_option(
                '--without-' + use_flag,
                action='store_true',
                dest='without_' + use_flag,
                default=False,
                help='Stops ' + use_flag \
                + ' from being included in any project.' \
                + ' This may be overridden by the target platform.')
        #endif

        if use[use_flag]['type'] != 'headers':
            group.add_option(
                '--with-' + use_flag,
                action='store',
                dest='with_' + use_flag,
                default=None,
                help='Links to the static or dynamic version of ' + use_flag \
                + '. Valid inputs are [dynamic, static] ' \
                + '[default: defined in use flag file (usually dynamic)]')
        #endif

        group.add_option(
            '--' + use_flag + '-includes',
            action='append',
            dest=use_flag + '_includes',
            default=None,
            help='Set include directories for ' + use_flag \
            + ', specify multiple times to add multiple include directories. ' \
            + 'If not specified, the default of the use_flags file is used, if present.')

        if use[use_flag]['type'] != 'headers':
            group.add_option(
                '--' + use_flag + '-libpath',
                action='append',
                dest=use_flag + '_libpath',
                default=None,
                help='Set dynamic link search directories for ' + use_flag \
                + ', specify multiple times to add multiple search directories. ' \
                + 'If not specified, the default of the use_flags file is used, if present.')

            group.add_option(
                '--' + use_flag + '-lib',
                action='store',
                dest=use_flag + '_lib',
                default=None,
                help='Set the name of the dynamic link library to link to (without lib suffix).')

            group.add_option(
                '--' + use_flag + '-stlibpath',
                action='append',
                dest=use_flag + '_stlibpath',
                default=None,
                help='Set static link search directories for ' + use_flag \
                + ', specify multiple times to add multiple search directories. ' \
                + 'If not specified, the default of the use_flags file is used, if present.')

            group.add_option(
                '--' + use_flag + '-stlib',
                action='store',
                dest=use_flag + '_stlib',
                default=None,
                help='Set the name of the static link library to link to (without lib suffix).')
        #endif
    #endfor
#enddef

class SmartFormatter(argparse.HelpFormatter):
    def _split_lines(self, text: str, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        #endif

        return argparse.HelpFormatter._split_lines(self, text, width)
    #enddef
#endclass

# Standard waf options function, called when --help is passed
def options(opt: OptionsContext):
    opt.load('unity waf_unit_test')
    opt.load('clang_compilation_database')
    opt.parser.remove_option('--alltests')
    opt.parser.remove_option('--notests')
    opt.parser.remove_option('--clear-failed')
    opt.parser.remove_option('--dump-test-scripts')
    opt.parser.remove_option('--libdir')
    opt.parser.remove_option('--bindir')
    opt.parser.remove_option('--out')
    opt.parser.remove_option('--top')

    def wrapper(opt, fn):
        def inner_wrapper(option):
            return fn(opt.parser.formatter, option)
        #enddef

        return inner_wrapper
    #enddef

    opt.parser.formatter_class = SmartFormatter

    config = get_config(opt)

    load_configuration_options(config, opt)
    load_use_options(config, opt)
#enddef
