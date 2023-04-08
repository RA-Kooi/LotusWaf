#!/usr/bin/env python3
# encoding: utf-8

import sysconfig

from waflib.Tools.ccroot import USELIB_VARS

from Common import *

# Parse the use flags file and command line options
def configure_use(cfg):
    use = get_use(cfg)

    for use_flag in use:
        configure_single_use(cfg, use, use_flag)
    #endfor
#enddef

# Parse a single use flag and the corresponding command line options
def configure_single_use(cfg, use, use_flag):
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
        cfg.fatal(use_flag \
            + ': An "optional" directive is required in a common' \
            + ' block, where the type is not "flags"!')
    #endif

    if type != 'flags' and not 'code' in use[use_flag]['common']:
        cfg.fatal(use_flag \
            + ': A "code" directive is required in a common' \
            + ' block, where the type is not "flags"!')
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
            cfg.msg('Checking for library <' + use_flag + '>', 'Disabled, skipping...', color='YELLOW')
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
        flags[toolset].setdefault('forced_includes', [])
    #endfor

    if type != 'flags':
        file = os.path.normcase(
            os.path.normpath(
                os.path.join('UseFlags', use[use_flag]['common']['code'])))
        with open(file, encoding='utf-8') as source_file:
            source = source_file.read();
        #endwith
    #endif

    for toolset in [cfg.env.cur_platform, cfg.env.cur_toolset, 'common']:
        if not toolset in use[use_flag]:
            continue
        #endif

        toolset_is_platform = False
        if toolset == cfg.env.cur_platform:
            toolset_is_platform = True
        #endif

        if toolset == 'common':
            skip_common = False

            if cfg.env.cur_platform in use[use_flag]:
                cur_platform = cfg.env.cur_platform

                if isinstance(use[use_flag][cfg.env.cur_platform], str):
                    cur_platform = use[use_flag][cfg.env.cur_platform]
                #endif

                if 'no_common' in use[use_flag][cur_platform]:
                    skip_common = use[use_flag][cur_platform]['no_common']
                #endif
            #endif

            if cfg.env.cur_toolset in use[use_flag]:
                cur_toolset = cfg.env.cur_toolset

                if isinstance(use[use_flag][cfg.env.cur_toolset], str):
                    cur_toolset = use[use_flag][cfg.env.cur_toolset]
                #endif

                if 'no_common' in use[use_flag][cur_toolset]:
                    skip_common = use[use_flag][cur_toolset]['no_common']
                #endif
            #endif

            if skip_common:
                continue
            #endif
        #endif

        if isinstance(use[use_flag][toolset], str):
            toolset = use[use_flag][toolset]

            # Toolset might be a toolset of another platform, so do this again.
            flags.setdefault(toolset, dict())
            flags[toolset].setdefault('defines', [])
            flags[toolset].setdefault('includes', [])
            flags[toolset].setdefault('cc_flags', [])
            flags[toolset].setdefault('cxx_flags', [])
            flags[toolset].setdefault('ld_flags', [])
            flags[toolset].setdefault('lib_paths', [])
            flags[toolset].setdefault('libs', [])
            flags[toolset].setdefault('use', [])
            flags[toolset].setdefault('forced_includes', [])
        #endif

        def read_option(write_option, variation_option, obj):
            if variation_option in obj:
                flags[toolset][write_option] += obj[variation_option]
            #endif
        #enddef

        if type != 'flags' \
                and cfg.options.__dict__[use_flag + '_includes'] != None:
            flags[toolset]['includes'] = cfg.options.__dict__[use_flag + '_includes']
        elif 'includes' in use[use_flag][toolset]:
            flags[toolset]['includes'] = use[use_flag][toolset]['includes']
        #endif

        current_toolset = get_toolset(cfg)
        cur_conf = cfg.env.cur_conf

        def make_flags_absolute(relative_path):
            return os.path.normcase(
                os.path.normpath(
                    os.path.join(cfg.path.abspath(), relative_path)))
        #enddef

        flags[toolset]['includes'] = list(
                map(make_flags_absolute, flags[toolset]['includes']))

        if 'defines' in use[use_flag][toolset]:
            read_option('defines', 'base', use[use_flag][toolset]['defines'])
            read_option('defines', cur_conf, use[use_flag][toolset]['defines'])

            for option in ['stlib', 'shlib']:
                read_option('defines', option, use[use_flag][toolset]['defines'])
                read_option(
                    'defines',
                    option + '_' + cur_conf,
                    use[use_flag][toolset]['defines'])
            #endfor
        #endif

        for option in ['cc_flags', 'cxx_flags', 'ld_flags']:
            read_option(option, option, use[use_flag][toolset])
            read_option(option, option + '_' + cur_conf, use[use_flag][toolset])
        #endfor
        read_option('use', 'use', use[use_flag][toolset])

        # This should probably be made more readable somehow,
        # but idk how to check for the options without horrible hacks
        if type == 'lib':
            # we either have a dynamic or static lib
            default_shared = True
            if 'shared' in use[use_flag][toolset]:
                default_shared = use[use_flag][toolset]['shared']
            #endif

            if cfg.options.__dict__['with_' + use_flag] == 'dynamic':
                default_shared = True
            elif cfg.options.__dict__['with_' + use_flag] == 'static':
                default_shared = False
            #endif

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
                    flags[toolset]['lib_paths'] = cfg.options.__dict__[use_flag + '_stlibpath']
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
                flags[toolset]['lib_paths'][i] = os.path.normcase(
                    os.path.normpath(
                        os.path.join(
                            cfg.path.abspath(),
                            flags[toolset]['lib_paths'][i])))
            #endfor
        #endif

        if not toolset in [cfg.env.cur_platform, cfg.env.cur_toolset, 'common']:
            if toolset_is_platform:
                flags[cfg.env.cur_platform] = flags[toolset]
            else:
                flags[cfg.env.cur_toolset] = flags[toolset]
            #endif
        #endif
    #endfor

    if not source and type != 'flags':
        cfg.fatal('Source of test file for <' + use_flag + '> is empty.')
    #endif

    # These flags are additive
    defines = flags[cfg.env.cur_toolset]['defines'] \
        + flags[cfg.env.cur_platform]['defines'] \
        + flags['common']['defines']

    includes = flags[cfg.env.cur_toolset]['includes'] \
        + flags[cfg.env.cur_platform]['includes'] \
        + flags['common']['includes']

    cc_flags = flags[cfg.env.cur_toolset]['cc_flags'] \
        + flags[cfg.env.cur_platform]['cc_flags'] \
        + flags['common']['cc_flags']

    cxx_flags = flags[cfg.env.cur_toolset]['cxx_flags'] \
        + flags[cfg.env.cur_platform]['cxx_flags'] \
        + flags['common']['cxx_flags']

    use = flags[cfg.env.cur_toolset]['use'] \
        + flags[cfg.env.cur_platform]['use'] \
        + flags['common']['use']

    # Linking related flags however are not
    ld_flags = []

    if flags[cfg.env.cur_toolset]['ld_flags'] != []:
        ld_flags = flags[cfg.env.cur_toolset]['ld_flags']
    elif flags[cfg.env.cur_platform]['ld_flags'] != []:
        ld_flags = flags[cfg.env.cur_platform]['ld_flags']
    else:
        ld_flags = flags['common']['ld_flags']
    #endif

    lib_paths = []

    if flags[cfg.env.cur_toolset]['lib_paths'] != []:
        lib_paths = flags[cfg.env.cur_toolset]['lib_paths']
    elif flags[cfg.env.cur_platform]['lib_paths'] != []:
        lib_paths = flags[cfg.env.cur_platform]['lib_paths']
    else:
        lib_paths = flags['common']['lib_paths']
    #endif

    libs = []

    if flags[cfg.env.cur_toolset]['libs'] != []:
        libs = flags[cfg.env.cur_toolset]['libs']
    elif flags[cfg.env.cur_platform]['libs'] != []:
        libs = flags[cfg.env.cur_platform]['libs']
    else:
        libs = flags['common']['libs']
    #endif

    # remove duplicates from the list
    for toolset in flags:
        for sublist in flags[toolset]:
            flags[toolset][sublist] = list(dict.fromkeys(flags[toolset][sublist]))
        #endfor
    #endfor

    if type == 'lib':
        if cfg.options.__dict__['with_' + use_flag] == 'dynamic':
            cfg.check_cxx(
                fragment=source,
                use=use + [use_flag] + ['EXE'],
                uselib_store=use_flag,
                cxxflags=cxx_flags,
                cflags=cc_flags,
                ldflags=ld_flags,
                libpath=lib_paths,
                lib=libs,
                defines=defines,
                system_includes=includes,
                msg='Checking for dynamic library <' + use_flag + '>',
                mandatory=not optional)
        elif cfg.options.__dict__['with_' + use_flag] == 'static':
            cfg.check_cxx(
                fragment=source,
                use=use + [use_flag] + ['EXE'],
                uselib_store=use_flag,
                cxxflags=cxx_flags,
                cflags=cc_flags,
                ldflags=ld_flags,
                stlibpath=lib_paths,
                stlib=libs,
                defines=defines,
                system_includes=includes,
                msg='Checking for static library <' + use_flag + '>',
                mandatory=not optional)
        #endif
    elif type == 'headers': # header only lib
        cfg.check_cxx(
            fragment=source,
            use=use + [use_flag] + ['EXE'],
            uselib_store=use_flag,
            defines=defines,
            cxxflags=cxx_flags,
            cflags=cc_flags,
            ldflags=ld_flags,
            system_includes=includes,
            msg='Checking for header only library <' + use_flag + '>',
            mandatory=not optional)
    elif type == 'flags':
        cfg.msg('Adding extra flags for <' + use_flag + '>', '✔')
        cfg.env['CFLAGS_' + use_flag] = cc_flags
        cfg.env['CXXFLAGS_' + use_flag] = cxx_flags
        cfg.env['LDFLAGS_' + use_flag] = ld_flags
        cfg.env['SYSINCLUDES_' + use_flag] = includes
    #endif
#enddef

# Standard waf configuration function, called when configure is passed
# Here we load, parse and cache the toolset passed to waf
def configure(cfg: ConfigurationContext):
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

    cfg.env.FORCEINCLUDES = []

    def read_optional_flag(
            target: str,
            option: str,
            obj: JSONType = toolset) -> None:
        if option in obj:
            cfg.env.append_value(target, obj[option])
        #endif
    #enddef

    # Parse compiler flags, defines and system includes
    for env_flag, toolset_flag in \
        [ \
            ('CFLAGS', 'cc_flags'), \
            ('CXXFLAGS', 'cxx_flags'), \
            ('ARFLAGS', 'stlib_flags'), \
            ('STLIBPATH', 'stlib_path'), \
            ('LINKFLAGS_cshlib', 'shlib_flags'), \
            ('LINKFLAGS_cxxshlib', 'shlib_flags'), \
            ('LIBPATH', 'shlib_path'), \
            ('LINKFLAGS_EXE', 'exe_flags'), \
            ('LDFLAGS', 'ld_flags')
        ]:
        cfg.env[env_flag] = toolset[toolset_flag]
        read_optional_flag(env_flag, toolset_flag + '_' + cfg.options.config)
    #endfor

    if cfg.options.development:
        cfg.env.CFLAGS += toolset['dev_cc_flags']
        cfg.env.CXXFLAGS += toolset['dev_cxx_flags']
    #endif

    cfg.env.DEFINES += toolset['defines']['base']
    read_optional_flag('DEFINES', cfg.options.config, toolset['defines'])

    cfg.env.SYSINCLUDES = []

    for path in toolset['system_includes']:
            flag = [normalized_join2(cfg.path.abspath(), path)]
            cfg.env.SYSINCLUDES += flag
    #endfor

    # Configure use flags
    configure_use(cfg)
#enddef
