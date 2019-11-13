#!/usr/bin/env python3
# encoding: utf-8

from waflib import Logs
from waflib.Configure import conf, ConfigurationContext
from waflib.Options import OptionsContext
from waflib.Tools import waf_unit_test

run_tests = False

# Show general help output when waf --help is executed
def load_configuration_options(config, opt):
    import platform, sys

    default_platform = sys.platform + '_x' + platform.machine()[-2:]

    platform_help ='Set the target platform you want to build for.\n' + \
            'Default is the host platform. Possible platforms are ' + \
            config['target_platforms'][0] + ', '

    for i in range(1, len(config['target_platforms'])):
        platform_help += config['target_platforms'][i] + ', '
    #endfor

    opt.add_option( \
        '--release', \
        action='store_false', \
        dest='development', \
        default=True, \
        help='Make a build for production, excludes flags like warning is error.')

    opt.add_option( \
        '--target-platform', \
        action='store', \
        dest='target_platform', \
        default=default_platform, \
        help=platform_help)

    opt.add_option( \
        '-c', \
        '--target-configuration', \
        action='store', \
        dest='config', \
        default=config['configurations'][0], \
        help='Select the project configuration to use. ' \
        + 'Valid configurations are %r [default: %s]' \
        % (config['configurations'], config['configurations'][0]))

    toolset_help = 'Select the toolset to use for compiling. Valid toolsets are: '
    for _platform in config['toolsets']:
        toolset_help = toolset_help + '{ platform: ' + _platform + ': '

        for _toolset in config['toolsets'][_platform]:
            toolset_help = toolset_help + 'toolset: ' + _toolset + ', '
        #endfor

        toolset_help = toolset_help[:-2]
        toolset_help = toolset_help + ' }, '
    #endfor

    if default_platform in config['toolsets']:
        toolset_help = toolset_help[:-2] + '[default: %s]' \
                % config['toolsets'][default_platform][0]

        opt.add_option( \
            '--toolset', \
            action='store', \
            dest='toolset', \
            default=config['toolsets'][default_platform][0], \
            help=toolset_help)
    else:
        print( \
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
            group.add_option( \
                '--without-' + use_flag, \
                action='store_true', \
                dest='without_' + use_flag, \
                default=False, \
                help='Stops ' + use_flag \
                + ' from being included in any project.' \
                + ' This may be overridden by the target platform.')
        #endif

        if use[use_flag]['type'] != 'headers':
            group.add_option( \
                '--with-' + use_flag, \
                action='store', \
                dest='with_' + use_flag, \
                default=None, \
                help='Links to the static or dynamic version of ' + use_flag \
                + '. Valid inputs are [dynamic, static] ' \
                + '[default: defined in use flag file (usually dynamic)]')
        #endif

        group.add_option( \
            '--' + use_flag + '-includes', \
            action='append', \
            dest=use_flag + '_includes', \
            default=None, \
            help='Set include directories for ' + use_flag \
            + ', specify multiple times to add multiple include directories. ' \
            + 'If not specified, the default of the use_flags file is used, if present.')

        if use[use_flag]['type'] != 'headers':
            group.add_option( \
                '--' + use_flag + '-libpath', \
                action='append', \
                dest=use_flag + '_libpath', \
                default=None, \
                help='Set dynamic link search directories for ' + use_flag \
                + ', specify multiple times to add multiple search directories. ' \
                + 'If not specified, the default of the use_flags file is used, if present.')

            group.add_option( \
                '--' + use_flag + '-lib', \
                action='store', \
                dest=use_flag + '_lib', \
                default=None, \
                help='Set the name of the dynamic link library to link to (without lib suffix).')

            group.add_option( \
                '--' + use_flag + '-stlibpath', \
                action='append', \
                dest=use_flag + '_stlibpath', \
                default=None, \
                help='Set static link search directories for ' + use_flag \
                + ', specify multiple times to add multiple search directories. ' \
                + 'If not specified, the default of the use_flags file is used, if present.')

            group.add_option( \
                '--' + use_flag + '-stlib', \
                action='store', \
                dest=use_flag + '_stlib', \
                default=None, \
                help='Set the name of the static link library to link to (without lib suffix).')
        #endif
    #endfor
#enddef

# Load the toolset passed to waf via --toolset and return it as a dictionary
def get_toolset(cfg):
    import json
    import os
    # TODO: Check if toolset is valid

    toolset = []
    file = str()
    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.normcase(os.path.normpath(os.path.join('Toolsets', \
                cfg.env.cur_toolset + '.lotus_toolset')))
    else:
        file = os.path.normcase(os.path.normpath(os.path.join(cfg.top_dir, \
            'Toolsets/' + cfg.env.cur_toolset + '.lotus_toolset')))
    #endif

    with open(file, encoding='utf-8') as toolset_file:
        toolset = json.loads(toolset_file.read())
    #endwith

    return toolset
#enddef

# Load the project configurations and return it as a dictionary
def get_config(cfg):
    import json
    import os

    config = []
    file = str()
    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = 'project_configurations.lotus_config'
    else:
        file = os.path.normcase(os.path.normpath(os.path.join(cfg.top_dir, \
            'project_configurations.lotus_config')))
    #endif

    with open(file, encoding='utf-8') as config_file:
        config = json.loads(config_file.read())
    #endwith

    return config
#enddef

# Load the use flags file and return it as a dictionary
def get_use(cfg):
    import json
    import os

    use = []
    file = str()
    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.normcase(os.path.normpath( \
            os.path.join('UseFlags', 'use_flags.lotus_use')))
    else:
        file = os.path.normcase(os.path.normpath(os.path.join(cfg.top_dir, \
            os.path.join('UseFlags', 'use_flags.lotus_use'))))
    #endif

    with open(file, encoding='utf-8') as config_file:
        use = json.loads(config_file.read())
    #endwith

    return use
#enddef

# Standard waf options function, called when --help is passed
def options(opt):
    opt.load('unity waf_unit_test')
    opt.parser.remove_option('--alltests')
    opt.parser.remove_option('--notests')
    opt.parser.remove_option('--clear-failed')
    opt.parser.remove_option('--dump-test-scripts')
    opt.parser.remove_option('--libdir')
    opt.parser.remove_option('--bindir')
    opt.parser.remove_option('--out')
    opt.parser.remove_option('--top')
    config = get_config(opt)

    load_configuration_options(config, opt)
    load_use_options(config, opt)
#enddef

# Parse the use flags file and command line options
def configure_use(cfg):
    import os

    use = get_use(cfg)

    for use_flag in use:
        configure_single_use(cfg, use, use_flag)
    #endfor
#enddef

# Parse a single use flag and the corresponding command line options
def configure_single_use(cfg, use, use_flag):
    import os

    type = str()
    if not 'type' in use[use_flag]:
        cfg.fatal(use_flag + ': Use flag type is required!')
    else:
        type = use[use_flag]['type']
    #endif

    if not 'platforms' in use[use_flag]:
        cfg.fatal(use_flag + ': Platforms are required!')
    #endif

    if not 'common' in use[use_flag]:
        cfg.fatal(use_flag + ': A common block is required!')
    #endif

    if type != 'flags' and not 'optional' in use[use_flag]['common']:
        cfg.fatal(use_flag + ': An "optional" directive is required in a common' + \
            ' block, where the type is not "flags"!')
    #endif

    if type != 'flags' and not 'code' in use[use_flag]['common']:
        cfg.fatal(use_flag + ': A "code" directive is required in a common' + \
            ' block, where the type is not "flags"!')
    #endif

    if not cfg.options.target_platform in use[use_flag]['platforms']:
        return
    #endif

    optional = False
    optional_platform = cfg.env.cur_toolset
    if not optional_platform in use[use_flag] \
            or not 'optional' in use[use_flag][optional_platform]:
        optional_platform = 'common'
    #endif

    if type != 'flags' and use[use_flag][optional_platform]['optional'] == True:
        optional = True
        if cfg.options.__dict__['without_' + use_flag] == True:
            print('[' + use_flag + '] Disabled, skipping...')
            return
        #endif
    #endif

    source = str()

    flags = dict()
    flags.setdefault('common', dict())
    flags.setdefault(cfg.env.cur_toolset, dict())
    flags.setdefault(cfg.env.cur_platform, dict())
    for toolset in flags:
        flags[toolset].setdefault('defines', [])
        flags[toolset].setdefault('includes', [])
        flags[toolset].setdefault('cc_flags', [])
        flags[toolset].setdefault('cxx_flags', [])
        flags[toolset].setdefault('ld_flags', [])
        flags[toolset].setdefault('lib_paths', [])
        flags[toolset].setdefault('libs', [])
        flags[toolset].setdefault('use', [])
        flags[toolset].setdefault('real_includes', [])
    #endfor

    if type != 'flags':
        file = os.path.normcase(os.path.normpath(os.path.join('UseFlags', \
            use[use_flag]['common']['code'])))
        with open(file, encoding='utf-8') as source_file:
            source = source_file.read();
        #endwith
    #endif

    for toolset in [cfg.env.cur_platform, cfg.env.cur_toolset, 'common']:
        if not toolset in use[use_flag]:
            continue
        #endif

        if toolset == 'common':
            skip_common = False

            if cfg.env.cur_platform in use[use_flag]:
                if 'no_common' in use[use_flag][cfg.env.cur_platform]:
                    skip_common = use[use_flag][cfg.env.cur_platform]['no_common']
                #endif
            #endif

            if cfg.env.cur_toolset in use[use_flag]:
                if 'no_common' in use[use_flag][cfg.env.cur_toolset]:
                    skip_common = use[use_flag][cfg.env.cur_toolset]['no_common']
                #endif
            #endif

            if skip_common:
                continue
            #endif
        #endif

        if type != 'flags' \
                and cfg.options.__dict__[use_flag + '_includes'] != None:
            flags[toolset]['includes'] = cfg.options.__dict__[use_flag + '_includes']
        elif 'includes' in use[use_flag][toolset]:
            flags[toolset]['includes'] = use[use_flag][toolset]['includes']
        #endif

        current_toolset = get_toolset(cfg)

        include_flags = None
        if 'system_include_flags' in current_toolset:
            include_flags = current_toolset['system_include_flags']
        #endif

        if include_flags == '' or include_flags == []:
            include_flags = None
        #endif

        def make_flags_absolute(relative_path):
            return os.path.normcase( \
                os.path.normpath( \
                    os.path.join(cfg.path.abspath(), relative_path)))
        #enddef

        flags[toolset]['includes'] = list(map( \
            make_flags_absolute, \
            flags[toolset]['includes']))

        if include_flags == None:
            flags[cfg.env.cur_toolset]['real_includes'] = flags[toolset]['includes']
            flags[toolset]['includes'] = []
        else:
            def add_system_flag(path):
                return include_flags + [path]
            #enddef

            flags[toolset]['includes'] = list( \
                map(add_system_flag, flags[toolset]['includes']))

            flatten = lambda l: [item for sublist in l for item in sublist]

            flags[toolset]['includes'] = flatten(flags[toolset]['includes'])
        #endif

        if 'defines' in use[use_flag][toolset]:
            if 'base' in use[use_flag][toolset]['defines']:
                flags[toolset]['defines'] += use[use_flag][toolset]['defines']['base']
            #endif

            if cfg.env.cur_conf in use[use_flag][toolset]['defines']:
                flags[toolset]['defines'] += \
                    use[use_flag][toolset]['defines'][cfg.env.cur_conf]
            #endif

            if 'stlib' in use[use_flag][toolset]['defines']:
                flags[toolset]['defines'] += use[use_flag][toolset]['defines']['stlib']
            #endif

            if 'stlib_' + cfg.env.cur_conf in use[use_flag][toolset]['defines']:
                flags[toolset]['defines'] += \
                    use[use_flag][toolset]['defines']['stlib_' + cfg.env.cur_conf]
            #endif

            if 'shlib' in use[use_flag][toolset]['defines']:
                flags[toolset]['defines'] += use[use_flag][toolset]['defines']['shlib']
            #endif

            if 'shlib_' + cfg.env.cur_conf in use[use_flag][toolset]['defines']:
                flags[toolset]['defines'] += \
                    use[use_flag][toolset]['defines']['shlib_' + cfg.env.cur_conf]
            #endif
        #endif

        if 'cc_flags' in use[use_flag][toolset]:
            flags[toolset]['cc_flags'] += use[use_flag][toolset]['cc_flags']
        #endif

        if 'cc_flags_' + cfg.env.cur_conf in use[use_flag][toolset]:
            flags[toolset]['cc_flags'] += \
                use[use_flag][toolset]['cc_flags_' + cfg.env.cur_conf]
        #endif

        if 'cxx_flags' in use[use_flag][toolset]:
            flags[toolset]['cxx_flags'] += use[use_flag][toolset]['cxx_flags']
        #endif

        if 'cxx_flags_' + cfg.env.cur_conf in use[use_flag][toolset]:
            flags[toolset]['cxx_flags'] += \
                    use[use_flag][toolset]['cxx_flags_' + cfg.env.cur_conf]
        #endif

        if 'ld_flags' in use[use_flag][toolset]:
            flags[toolset]['ld_flags'] += use[use_flag][toolset]['ld_flags']
        #endif

        if 'ld_flags_' + cfg.env.cur_conf in use[use_flag][toolset]:
            flags[toolset]['ld_flags'] += \
                    use[use_flag][toolset]['ld_flags_' + cfg.env.cur_conf]
        #endif

        if 'use' in use[use_flag][toolset]:
            flags[toolset]['use'] += use[use_flag][toolset]['use']
        #endif

        # This should probably be made more readable somehow,
        # but idk how to check for the options without horrible hacks
        if type == 'lib':
            # we either have a dynamic or static lib
            default_shared = True
            if 'shared' in use[use_flag][toolset]:
                default_shared = use[use_flag][toolset]['shared']

            if cfg.options.__dict__['with_' + use_flag] == 'dynamic':
                default_shared = True
            elif cfg.options.__dict__['with_' + use_flag] == 'static':
                default_shared = False

            if default_shared:
                cfg.options.__dict__['with_' + use_flag] = 'dynamic'

                if cfg.options.__dict__[use_flag + '_libpath'] != None:
                    flags[toolset]['lib_paths'] = cfg.options.__dict__[use_flag + '_libpath']
                # No command line option passed
                elif 'shlib_path' in use[use_flag][toolset]:
                    flags[toolset]['lib_paths'] = use[use_flag][toolset]['shlib_path']
                #endif

                if cfg.options.__dict__[use_flag + '_lib'] != None:
                    flags[toolset]['libs'] = [cfg.options.__dict__[use_flag + '_lib']]
                # No command line option passed
                elif 'shlib_link' in use[use_flag][toolset]:
                    flags[toolset]['libs'] = use[use_flag][toolset]['shlib_link']
                #endif
            else:
                cfg.options.__dict__['with_' + use_flag] = 'static'

                if cfg.options.__dict__[use_flag + '_stlibpath'] != None:
                    flags[toolset]['lib_paths'] = \
                            cfg.options.__dict__[use_flag + '_stlibpath']
                # No command line option passed
                elif 'stlib_path' in use[use_flag][toolset]:
                    flags[toolset]['lib_paths'] = use[use_flag][toolset]['stlib_path']
                #endif

                if cfg.options.__dict__[use_flag + '_lib'] != None:
                    flags[toolset]['libs'] = [cfg.options.__dict__[use_flag + '_lib']]
                # No command line option passed
                elif 'stlib_link' in use[use_flag][toolset]:
                    flags[toolset]['libs'] = use[use_flag][toolset]['stlib_link']
                #endif
            #endif

            # Make library paths absolute
            for i in range(len(flags[toolset]['lib_paths'])):
                flags[toolset]['lib_paths'][i] = \
                        os.path.normcase(os.path.normpath(os.path.join( \
                        cfg.path.abspath(), flags[toolset]['lib_paths'][i])))
            #endfor
        #endif
    #endfor

    if not source and type != 'flags':
        cfg.fatal('Source of test file for <' + use_flag + '> is empty.')
    #endif

    # These flags are additive
    defines = flags[cfg.env.cur_toolset]['defines'] + \
        flags[cfg.env.cur_platform]['defines'] + \
        flags['common']['defines']

    includes = flags[cfg.env.cur_toolset]['includes'] + \
        flags[cfg.env.cur_platform]['includes'] + \
        flags['common']['includes']

    cc_flags = flags[cfg.env.cur_toolset]['cc_flags'] + \
        flags[cfg.env.cur_platform]['cc_flags'] + \
        flags['common']['cc_flags']

    cxx_flags = flags[cfg.env.cur_toolset]['cxx_flags'] + \
        flags[cfg.env.cur_platform]['cxx_flags'] + \
        flags['common']['cxx_flags']

    use = flags[cfg.env.cur_toolset]['use'] + \
        flags[cfg.env.cur_platform]['use'] + \
        flags['common']['use']

    # Linking related flags however are not
    ld_flags = []

    if flags[cfg.env.cur_toolset]['ld_flags'] != []:
        ld_flags = flags[cfg.env.cur_toolset]['ld_flags']
    elif flags[cfg.env.cur_platform]['ld_flags'] != []:
        ld_flags = flags[cfg.env.cur_platform]['ld_flags']
    else:
        ld_flags = flags['common']['ld_flags']

    lib_paths = []

    if flags[cfg.env.cur_toolset]['lib_paths'] != []:
        lib_paths = flags[cfg.env.cur_toolset]['lib_paths']
    elif flags[cfg.env.cur_platform]['lib_paths'] != []:
        lib_paths = flags[cfg.env.cur_platform]['lib_paths']
    else:
        lib_paths = flags['common']['lib_paths']

    libs = []

    if flags[cfg.env.cur_toolset]['libs'] != []:
        libs = flags[cfg.env.cur_toolset]['libs']
    elif flags[cfg.env.cur_platform]['libs'] != []:
        libs = flags[cfg.env.cur_platform]['libs']
    else:
        libs = flags['common']['libs']

    # remove duplicates from the list
    for toolset in flags:
        for sublist in flags[toolset]:
            flags[toolset][sublist] = list(dict.fromkeys(flags[toolset][sublist]))
        #endfor
    #endfor

    if cfg.env.CC_NAME == 'msvc' or cfg.env.CXX_NAME == 'msvc':
        for toolset in flags:
            for cflags in ['cc_flags', 'cxx_flags']:
                for flag in flags[toolset][cflags]:
                    if flag[1:].lower() == 'fs':
                        cfg.fatal(use_flag  + ': Don\'t add the /FS flag, ' +
                            'this will be handled by LotusWaf!')
                    #endif

                    if flag[1:3].lower() == 'fd':
                        cfg.fatal(use_flag + ': Don\'t add the /Fd flag, ' + \
                            'this will be handled by LotusWaf!')
                    #endif
                #endfor
            #endfor
        #endfor
    #endif

    if type == 'lib':
        if cfg.options.__dict__['with_' + use_flag] == 'dynamic':
            cfg.check_cxx( \
                fragment=source, \
                use=use + [use_flag] + ['EXE'], \
                uselib_store=use_flag, \
                cxxflags=includes + cxx_flags, \
                cflags=includes + cc_flags, \
                ldflags=ld_flags, \
                libpath=lib_paths, \
                lib=libs, \
                defines=defines, \
                includes=flags[cfg.env.cur_toolset]['real_includes'], \
                msg='Checking for dynamic library <' + use_flag + '>', \
                mandatory=not optional)
        elif cfg.options.__dict__['with_' + use_flag] == 'static':
            cfg.check_cxx( \
                fragment=source, \
                use=use + [use_flag] + ['EXE'], \
                uselib_store=use_flag, \
                cxxflags=includes + cxx_flags, \
                cflags=includes + cc_flags, \
                ldflags=ld_flags, \
                stlibpath=lib_paths, \
                stlib=libs, \
                defines=defines, \
                includes=flags[cfg.env.cur_toolset]['real_includes'], \
                msg='Checking for static library <' + use_flag + '>', \
                mandatory=not optional)
        #endif
    elif type == 'headers': # header only lib
        cfg.check_cxx( \
            fragment=source, \
            use=use + [use_flag] + ['EXE'], \
            uselib_store=use_flag, \
            defines=defines, \
            cxxflags=includes + cxx_flags, \
            cflags=includes + cc_flags, \
            ldflags=ld_flags, \
            includes=flags[cfg.env.cur_toolset]['real_includes'], \
            msg='Checking for header only library <' + use_flag +'>', \
            mandatory=not optional)
    elif type == 'flags':
        print('Adding extra flags for <' + use_flag + '>')
        cfg.env['CFLAGS_' + use_flag] = cc_flags + includes
        cfg.env['CXXFLAGS_' + use_flag] = cxx_flags + includes
        cfg.env['LDFLAGS_' + use_flag] = ld_flags
        cfg.env['INCLUDES_' + use_flag] = flags[cfg.env.cur_toolset]['real_includes']
    #endif
#enddef

# Standard waf configuration function, called when configure is passed
# Here we load, parse and cache the toolset passed to waf
def configure(cfg):
    import os, sys, sysconfig

    if sysconfig.get_platform() == 'mingw':
        Logs.enable_colors(2)
    #endif

    # Cache configuration flags so they can't be overriden at build (1)
    cfg.env.cur_toolset = cfg.options.toolset

    config = get_config(cfg)
    toolset = get_toolset(cfg)

    # Cache configuration flags so they can't be overriden at build (2)
    config_found = False
    for configuration in config['configurations']:
        if cfg.options.config == configuration:
            config_found = True
        #endif
    #endfor

    if config_found == False:
        cfg.fatal('Invalid configuration used!')
    #endif

    # Save the configuration for error checking during build
    cfg.env.cur_conf = cfg.options.config

    # Cache configuration flags so they can't be overriden at build (3)
    platform_found = False
    for platform in config['target_platforms']:
        if cfg.options.target_platform == platform:
            platform_found = True
        #endif
    #endfor

    if platform_found == False:
        cfg.fatal('Invalid platform used!')
    #endif

    cfg.env.cur_platform = cfg.options.target_platform

    ignore_paths = False
    if 'ignore_paths' in toolset:
        ignore_paths = toolset['ignore_paths']
    #endif

    ## Set the compiler paths so waf can find them
    if not ignore_paths:
        cfg.env.CC = toolset['cc_path']
        cfg.env.CXX = toolset['cxx_path']
        cfg.env.AR = toolset['ar_path']
    #endif

    cfg.load(toolset['cc'])
    cfg.load(toolset['cxx'])
    cfg.load('clang_compilation_database')

    if toolset['cc'] == 'msvc' or toolset['cxx'] == 'msvc':
        cfg.load('msvc_pdb')
    #endif

    # Parse compiler flags, defines and system includes
    cfg.env.CFLAGS += toolset['cc_flags']
    if 'cc_flags_' + cfg.options.config in toolset:
        cfg.env.CFLAGS += toolset['cc_flags_' + cfg.options.config]
    #endif

    if cfg.options.development:
        cfg.env.CFLAGS += toolset['dev_cc_flags']
    #endif

    cfg.env.CXXFLAGS += toolset['cxx_flags']
    if 'cxx_flags_' + cfg.options.config in toolset:
        cfg.env.CXXFLAGS += toolset['cxx_flags_' + cfg.options.config]
    #endif

    if cfg.options.development:
        cfg.env.CXXFLAGS += toolset['dev_cxx_flags']
    #endif

    cfg.env.DEFINES += toolset['defines']['base']
    if cfg.options.config in toolset['defines']:
        cfg.env.DEFINES += toolset['defines'][cfg.options.config]
    #endif

    system_include_flags = None
    if 'system_include_flags' in toolset:
        system_include_flags = toolset['system_include_flags']

        if system_include_flags == '' or system_include_flags == []:
            system_include_flags = None
        #endif
    #endif

    for path in toolset['system_includes']:
        if system_include_flags == None:
            cfg.env.INCLUDES += os.path.normcase(os.path.normpath(os.path.join( \
            cfg.path.abspath(), path)))
        else:
            flag = system_include_flags + [os.path.normcase(os.path.normpath(os.path.join( \
                cfg.path.abspath(), path)))]
            cfg.env.CFLAGS += flag
            cfg.env.CXXFLAGS += flag
        #endif
    #endfor

    if cfg.env.CC_NAME == 'msvc' or cfg.env.CXX_NAME == 'msvc':
        for flags in ['CFLAGS', 'CXXFLAGS']:
            for flag in cfg.env[flags]:
                if flag[1:].lower() == 'fs':
                    cfg.fatal('Don\'t add the /FS flag, this will be handled' + \
                        ' by LotusWaf!')
                #endif

                if flag[1:3].lower() == 'fd':
                    cfg.fatal('Don\'t add the /Fd flag, this will be handled' + \
                        ' by LotusWaf!')
                #endif
            #endfor
        #endfor
    #endif

    # Parse linker flags and static lib flags
    cfg.env.ARFLAGS = toolset['stlib_flags']
    if 'stlib_flags_' + cfg.options.config in toolset:
        cfg.env.ARFLAGS += toolset['stlib_flags_' + cfg.options.config]
    #endif

    cfg.env.STLIBPATH = toolset['stlib_path']
    if 'stlib_path_' + cfg.options.config in toolset:
        cfg.env.STLIBPATH += toolset['stlib_path_' + cfg.options.config]
    #endif

    cfg.env.LINKFLAGS_cshlib = toolset['shlib_flags']
    cfg.env.LINKFLAGS_cxxshlib = toolset['shlib_flags']
    if 'shlib_flags_' + cfg.options.config in toolset:
        cfg.env.LINKFLAGS_cshlib += toolset['shlib_flags_' + cfg.options.config]
        cfg.env.LINKFLAGS_cxxshlib += toolset['shlib_flags_' + cfg.options.config]
    #endif

    cfg.env.LIBPATH = toolset['shlib_path']
    if 'shlib_path_' + cfg.options.config in toolset:
        cfg.env.LIBPATH += toolset['shlib_path_' + cfg.options.config]
    #endif

    cfg.env.LINKFLAGS_EXE = toolset['exe_flags']
    if 'exe_flags_' + cfg.options.config in toolset:
        cfg.env.LINKFLAGS_EXE += toolset['exe_flags_' + cfg.options.config]
    #endif

    cfg.env.LDFLAGS = toolset['ld_flags']
    if 'ld_flags_' + cfg.options.config in toolset:
        cfg.env.LDFLAGS += toolset['ld_flags_' + cfg.options.config]
    #endif

    # Configure use flags
    configure_use(cfg)
#enddef

def summary(bld):
    lst = getattr(bld, 'utest_results', [])
    if lst:
        total = len(lst)
        tfail = len([x for x in lst if x[1]])

        val = 100 * (total - tfail) / (1.0 * total)
        Logs.pprint('CYAN', 'Test report: %3.0f%% success' % val)

        Logs.pprint('CYAN', '  Tests that succeed: %d/%d' % (total - tfail, total))
        Logs.pprint('CYAN', '  Tests that fail: %d/%d' % (tfail, total))
        for (f, code, out, err) in lst:
            if code:
                Logs.pprint('CYAN', '    %s' % f)
                Logs.pprint('RED', 'Status: %r' % code)
                if out: Logs.pprint('RED', 'out: %r' % out)
                if err: Logs.pprint('RED', 'err: %r' % err)
            #endif
        #endfor
    #endif
#enddef

def build(bld):
    import sysconfig

    if sysconfig.get_platform() == 'mingw':
        Logs.enable_colors(2)
    #endif

    global run_tests
    if run_tests:
        bld.options.all_tests = True
        bld.options.no_tests = False
    else:
        bld.options.all_tests = False
        bld.options.no_tests = True
    #endif

    bld.options.clear_failed_tests = True
    bld.add_post_fun(summary)
    bld.add_post_fun(waf_unit_test.set_exit_code)
#enddef

def test(bld):
    global run_tests
    run_tests = True

    from waflib import Options
    Options.commands = ['build'] + Options.commands
#enddef

from waflib.Build import BuildContext
class TestContext(BuildContext):
    '''Build and execute unit tests'''
    cmd = 'test'
    fun = 'test'

# Loads, parses, and builds a project file
@conf
def project(self, project_file):
    import json, os, sys

    config = get_config(self)
    toolset = get_toolset(self)

    # Load the project file and store it in a dictionary
    project = []
    file = os.path.normcase(os.path.normpath(os.path.join(self.path.srcpath(), \
        project_file + '.lotus_project')))
    with open(file, encoding='utf-8') as project_file_:
        project = json.loads(project_file_.read())
    #endwith

    target = project['target']
    target = os.path.normpath( \
        os.path.join( \
            self.out_dir, \
            os.path.relpath(self.path.abspath(), self.top_dir), \
            target))

    # Change the path from unix style to windows style if we're running on cmd.exe
    # Other terminals, MSYS2 and the likes, need a unix style path
    if os.environ.get('TERM') == 'vt100' and sys.platform == 'win32':
        target = target.replace('/', '\\')
    #endif

    defines = []
    if 'defines' in project:
        if 'base' in project['defines']:
            defines += project['defines']['base']
        #endif

        if self.env.cur_conf in project['defines']:
            defines += project['defines'][self.env.cur_conf]
        #endif

        if project['type'] in project['defines']:
            defines += project['defines'][project['type']]
        #endif

        if (project['type'] + '_' + self.env.cur_conf) in project['defines']:
            defines += project['defines'][project['type'] + '_' + self.env.cur_conf]
        #endif
    #endif

    includes = project['includes']

    lib = []
    if 'shlib_link' in project:
        lib += project['shlib_link']
    #endif

    lib_path = []
    if 'shlib_path' in project:
        lib_path += project['shlib_path']
    #endif

    stlib = []
    if 'stlib_link' in project:
        stlib += project['stlib_link']
    #endif

    stlib_path = []
    if 'stlib_path' in project:
        stlib_path += project['stlib_path']
    #endif

    use = []
    if 'use' in project:
        use += project['use']
    #endif

    # These are use variables which are NOT propagated to the project use flag
    # This means that you should put extra compile flag uses in this
    uselib = []
    if 'uselib' in project:
        uselib += project['uselib']
    #endif

    cc_flags = []
    if self.env.cur_platform in project:
        if 'defines' in project[self.env.cur_platform]:
            if 'base' in project[self.env.cur_platform]['defines']:
                defines += project[self.env.cur_platform]['defines']['base']
            #endif

            if self.env.cur_conf in project[self.env.cur_platform]['defines']:
                defines += project[self.env.cur_platform]['defines'][self.env.cur_conf]
            #endif

            if project['type'] in project[self.env.cur_platform]['defines']:
                defines += project[self.env.cur_platform]['defines'][project['type']]
            #endif

            if (project['type'] + '_' + self.env.cur_conf) in \
                    project[self.env.cur_platform]['defines']:
                defines += project[self.env.cur_platform]['defines'][project['type'] + \
                        '_' + self.env.cur_conf]
            #endif

            if 'includes' in project[self.env.cur_platform]:
                includes += project[self.env.cur_platform]['includes']
            #endif

            if 'shlib_link' in project[self.env.cur_platform]:
                lib += project[self.env.cur_platform]['shlib_link']
            #endif

            if 'shlib_path' in project[self.env.cur_platform]:
                lib_path += project[self.env.cur_platform]['shlib_path']
            #endif

            if 'stlib_link' in project[self.env.cur_platform]:
                stlib += project[self.env.cur_platform]['stlib_link']
            #endif

            if 'stlib_path' in project[self.env.cur_platform]:
                stlib_path += project[self.env.cur_platform]['stlib_path']
            #endif
        #endif
    #endif

    include_flags = None
    if 'system_include_flags' in toolset:
        include_flags = toolset['system_include_flags']

        if include_flags == '' or include_flags == []:
            include_flags = None
        #endif
    #endif

    def make_flags_absolute(relative_path):
        return os.path.normcase( \
            os.path.normpath( \
                os.path.join(self.path.abspath(), relative_path)))
    #enddef

    export_includes = []
    export_system_includes = []
    if 'export_includes' in project:
        project['export_includes'] = list(map( \
            make_flags_absolute,
            project['export_includes']))

        if include_flags == None:
            export_includes += project['export_includes']
        else:
            def add_system_flag(path):
                return include_flags + [path]
            #enddef

            project['export_includes'] = list( \
                map(add_system_flag, project['export_includes']))

            flatten = lambda l: [item for sublist in l for item in sublist]

            project['export_includes'] = flatten(project['export_includes'])
            export_system_includes = project['export_includes']
        #endif
    #endif

    # If a project is in unity build mode, we pass the unity feature.
    # This will call all functions with @feature('unity')
    feature = 'nounity'
    if project['unity_build'] == True:
        feature = 'unity'
    #endif

    version = project['version']
    if sys.platform == 'win32':
        version = ''
    #endif

    task_gen = None
    if project['type'] == 'shlib':
        self.shlib( \
            name=project['name'], \
            source=project['sources'], \
            target=target, \
            vnum=version, \
            defines=defines, \
            includes=includes,\
            lib=lib, \
            libpath=lib_path, \
            stlib=stlib, \
            stlibpath=stlib_path, \
            rpath=project['rpath'], \
            use=use, \
            uselib=use + uselib, \
            features=feature, \
            export_includes=export_includes, \
            # Add an extra define that can be checked to see if a project is built as a DLL or not.
            # Needed for dllimport on windows.
            export_defines=[project['name'].upper() + '_AS_DLL'])
    elif project['type'] == 'stlib':
        self.stlib( \
            name=project['name'], \
            source=project['sources'], \
            target=target, \
            vnum=version, \
            defines=defines, \
            includes=includes, \
            lib=lib, \
            libpath=lib_path, \
            stlib=stlib, \
            stlibpath=stlib_path, \
            rpath=project['rpath'], \
            use=use, \
            uselib=use + uselib, \
            features=feature, \
            export_includes=export_includes, \
            # Add an extra define that can be checked to see if a project is built as a
            # static library or not.
            # This has been added because of the one above,
            # if this is for whatever reason ever needed.
            export_defines=[project['name'].upper() + '_AS_LIB'])
    elif project['type'] == 'exe':
        self.program( \
            name=project['name'], \
            source=project['sources'], \
            target=target, \
            vnum=version, \
            defines=defines, \
            includes=includes, \
            lib=lib, \
            libpath=lib_path, \
            stlib=stlib, \
            stlibpath=stlib_path, \
            rpath=project['rpath'], \
            use=use + ['EXE'], \
            uselib=use + uselib, \
            features=feature, \
            export_includes=export_includes)
    elif project['type'] == 'test':
        self.program( \
            name=project['name'], \
            source=project['sources'], \
            target=target, \
            vnum=version, \
            defines=defines, \
            includes=includes, \
            lib=lib, \
            libpath=lib_path, \
            stlib=stlib, \
            stlibpath=stlib_path, \
            rpath=project['rpath'], \
            use=use + ['EXE'], \
            uselib=use + uselib, \
            features=feature + ' test', \
            export_includes=export_includes)
    #endif

    self.env['CFLAGS_' + project['name']] = export_system_includes
    self.env['CXXFLAGS_' + project['name']] = export_system_includes
#enddef

from waflib.TaskGen import feature
@feature('nounity')
def no_unity(self):
    pass
#enddef

from waflib.TaskGen import feature
@feature('unity')
def unity(self):
    pass
#enddef

#Override unity's batch_size function so we can control unity builds per project
from waflib.extras import unity
from waflib import TaskGen, Options
@TaskGen.taskgen_method
def batch_size(self):
    if 'nounity' in self.features:
        return 0;
    else: # 'unity'
        return getattr(Options.options, 'batchsize', unity.MAX_BATCH)
    #endif
#enddef
