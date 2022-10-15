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

run_tests = False

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

# Load the toolset passed to waf via --toolset and return it as a dictionary
def get_toolset(cfg):
    toolset = []
    file = str()
    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.normcase(
                os.path.normpath(
                    os.path.join(
                        'Toolsets',
                        cfg.env.cur_toolset + '.lotus_toolset')))
    else:
        file = os.path.normcase(
                os.path.normpath(
                    os.path.join(
                        cfg.top_dir,
                        'Toolsets',
                        cfg.env.cur_toolset + '.lotus_toolset')))
    #endif

    with open(file, encoding='utf-8') as toolset_file:
        return json.loads(toolset_file.read())
    #endwith
#enddef

# Load the project configurations and return it as a dictionary
def get_config(cfg):
    file = str()
    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.normcase(
                os.path.normpath(
                    os.path.join('project_configurations.lotus_config')))
    else:
        file = os.path.normcase(
                os.path.normpath(
                    os.path.join(
                        cfg.top_dir,
                        'project_configurations.lotus_config')))
    #endif

    with open(file, encoding='utf-8') as config_file:
        return json.loads(config_file.read())
    #endwith
#enddef

# Load the use flags file and return it as a dictionary
def get_use(cfg):

    file = str()
    if type(cfg) is ConfigurationContext or type(cfg) is OptionsContext:
        file = os.path.normcase(
                os.path.normpath(
                    os.path.join('UseFlags', 'use_flags.lotus_use')))
    else:
        file = os.path.normcase(
                os.path.normpath(
                    os.path.join(
                        cfg.top_dir,
                        'UseFlags',
                        'use_flags.lotus_use')))
    #endif

    with open(file, encoding='utf-8') as config_file:
        return json.loads(config_file.read())
    #endwith
#enddef

# Standard waf options function, called when --help is passed
def options(opt):
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
    config = get_config(opt)

    load_configuration_options(config, opt)
    load_use_options(config, opt)
#enddef

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
def configure(cfg):
    USELIB_VARS['c'].add('SYSINCLUDES')
    USELIB_VARS['cxx'].add('SYSINCLUDES')

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

    if not 'forced_include_flag' in toolset:
        cfg.fatal('Toolset requires a forced_include_flag attribute')
    #endif

    if toolset['forced_include_flag'] == None \
        or toolset['forced_include_flag'] == '' \
        or toolset['forced_include_flag'] == []:
        cfg.fatal('forced_include_flag cannot be empty')
    #endif
    cfg.env.FORCEINCFLAG = toolset['forced_include_flag']
    cfg.env.FORCEINCLUDES = []

    def read_optional_flag(target, option, obj = toolset):
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

    system_include_flag = None
    if not 'system_include_flag' in toolset:
        cfg.fatal('system_include_flag is required!')
    #endif

    system_include_flag = toolset['system_include_flag']

    if system_include_flag == '' or system_include_flag == []:
        system_include_flags = None
    #endif
    cfg.env.SYSINCFLAG = system_include_flag
    cfg.env.SYSINCLUDES = []

    for path in toolset['system_includes']:
            flag = [os.path.normcase(
                os.path.normpath(os.path.join(cfg.path.abspath(), path)))]
            cfg.env.SYSINCLUDES += flag
    #endfor

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
    USELIB_VARS['c'].add('SYSINCLUDES')
    USELIB_VARS['cxx'].add('SYSINCLUDES')

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

    Options.commands = ['build'] + Options.commands
#enddef

class TestContext(BuildContext):
    '''Build and execute unit tests'''
    cmd = 'test'
    fun = 'test'

# Loads, parses, and builds a project file
@conf
def project(self, project_file):
    config = get_config(self)
    toolset = get_toolset(self)
    cur_conf = self.env.cur_conf
    cur_platform = self.env.cur_platform

    # Load the project file and store it in a dictionary
    project = []
    file = os.path.normcase(os.path.normpath(os.path.join(self.path.srcpath(), \
        project_file + '.lotus_project')))
    with open(file, encoding='utf-8') as project_file_:
        project = json.loads(project_file_.read())
    #endwith

    if 'platforms' in project:
        if not self.env.cur_platform in project['platforms']:
            return
        #endif
    #endif

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

    def read_option(var, option, obj = project):
        if option in obj:
            var += obj[option]
        #endif
    #enddef

    defines = []
    if 'defines' in project:
        read_option(defines, 'base', project['defines'])
        read_option(defines, cur_conf, project['defines'])
        read_option(defines, project['type'], project['defines'])
        read_option(
            defines,
            project['type'] + '_' + self.env.cur_conf,
            project['defines'])
    #endif

    includes = []
    export_force_includes = []
    lib = []
    lib_path = []
    stlib = []
    stlib_path = []
    use = []

    read_option(includes, 'includes')
    read_option(export_force_includes, 'export_force_includes')
    read_option(lib, 'shlib_link')
    read_option(lib_path, 'shlib_path')
    read_option(stlib, 'stlib_link')
    read_option(stlib_path, 'stlib_path')
    read_option(use, 'use')

    # These are use variables which are NOT propagated to the project use flag
    # This means that you should put extra compile flag uses in this
    uselib = []
    rpath = []

    read_option(uselib, 'uselib')
    read_option(rpath, 'rpath')

    if self.env.cur_platform in project:
        if 'defines' in project[self.env.cur_platform]:
            def read_option(var, option, obj = project[cur_platform]):
                if option in obj:
                    var += obj
                #endif
            #enddef

            def read_option2(var, option, obj):
                read_option(var, option, project[cur_platform][obj])
            #enddef

            read_option2(defines, 'base', 'defines')
            read_option2(defines, cur_conf, 'defines')
            read_option2(defines, project['type'], 'defines')
            read_option2(defines, project['type'] + '_' + cur_conf, 'defines')

            read_option(includes, 'includes')
            read_option(export_force_includes, 'export_force_includes')
            read_option(lib, 'shlib_link')
            read_option(lib_path, 'shlib_path')
            read_option(stlib, 'stlib_link')
            read_option(stlib_path, 'stlib_path')
        #endif
    #endif

    def make_flags_absolute(relative_path):
        return os.path.normcase(
            os.path.normpath(os.path.join(self.path.abspath(), relative_path)))
    #enddef

    export_includes = []
    if 'export_includes' in project:
        project['export_includes'] = list(
            map(make_flags_absolute, project['export_includes']))

        export_includes = project['export_includes']
    #endif

    # If a project is in unity build mode, we pass the unity feature.
    # This will call all functions with @feature('unity')
    feature = 'nounity'
    if project['unity_build'] == True:
        feature = 'unity'
    #endif

    version = project['version']
    if self.env.cur_platform.startswith('win32'):
        version = ''
    #endif

    sources = project['sources']

    platform_sources = self.env.cur_platform + '_sources'
    if platform_sources in project:
        if isinstance(project[platform_sources], str):
            platform_sources = project[platform_sources]
        #endif

        sources += project[platform_sources]
    #endif

    toolset_sources = self.env.cur_toolset + '_sources'
    if toolset_sources in project:
        if isinstance(project[toolset_sources], str):
            toolset_sources = project[toolset_sources]
        #endif

        sources += project[toolset_sources]
    #endif

    task_gen = None
    if project['type'] == 'shlib':
        self.shlib(
            name=project['name'],
            source=sources,
            target=target,
            vnum=version,
            defines=defines,
            includes=includes,
            lib=lib,
            libpath=lib_path,
            stlib=stlib,
            stlibpath=stlib_path,
            rpath=rpath,
            use=use,
            uselib=use + uselib,
            features=feature,
            export_system_includes=export_includes,
            export_force_includes=export_force_includes,
            # Add an extra define that can be checked to see if a project is built as a DLL or not.
            # Needed for dllimport on windows.
            export_defines=[project['name'].upper() + '_AS_DLL'])
    elif project['type'] == 'stlib':
        self.stlib(
            name=project['name'],
            source=sources,
            target=target,
            vnum=version,
            defines=defines,
            includes=includes,
            lib=lib,
            libpath=lib_path,
            stlib=stlib,
            stlibpath=stlib_path,
            rpath=rpath,
            use=use,
            uselib=use + uselib,
            features=feature,
            export_system_includes=export_includes,
            export_force_includes=export_force_includes,
            # Add an extra define that can be checked to see if a project is built as a
            # static library or not.
            # This has been added because of the one above,
            # if this is for whatever reason ever needed.
            export_defines=[project['name'].upper() + '_AS_LIB'])
    elif project['type'] == 'exe':
        self.program(
            name=project['name'],
            source=sources,
            target=target,
            vnum=version,
            defines=defines,
            includes=includes,
            lib=lib,
            libpath=lib_path,
            stlib=stlib,
            stlibpath=stlib_path,
            rpath=rpath,
            use=use + ['EXE'],
            uselib=use + uselib,
            features=feature,
            export_system_includes=export_includes)
    elif project['type'] == 'test':
        self.program(
            name=project['name'],
            source=sources,
            target=target,
            vnum=version,
            defines=defines,
            includes=includes,
            lib=lib,
            libpath=lib_path,
            stlib=stlib,
            stlibpath=stlib_path,
            rpath=rpath,
            use=use + ['EXE'],
            uselib=use + uselib,
            features=feature + ' test',
            export_system_includes=export_includes)
    #endif
#enddef

@feature('nounity')
def no_unity(self):
    pass
#enddef

@feature('unity')
def unity(self):
    pass
#enddef

#Override unity's batch_size function so we can control unity builds per project
from waflib.extras import unity
@taskgen_method
def batch_size(self):
    if 'nounity' in self.features:
        return 0;
    else: # 'unity'
        return getattr(Options.options, 'batchsize', unity.MAX_BATCH)
    #endif
#enddef

@feature('c', 'cxx', 'use')
@before_method('apply_incpaths', 'propagate_uselib_vars')
@after_method('process_use')
def process_extra_use(self):
    """
    Process the ``use`` attribute which contains a list of task generator names::

        def build(bld):
            bld.shlib(source='a.c', target='lib1')
            bld.program(source='main.c', target='app', use='lib1')

    See :py:func:`waflib.Tools.ccroot.use_rec`.
    """

    #from waflib.Tools import ccroot

    use_not = self.tmp_use_not = set()
    self.tmp_use_seen = [] # we would like an ordered set
    use_prec = self.tmp_use_prec = {}
    self.system_includes = self.to_list(getattr(self, 'system_includes', []))
    self.force_includes = self.to_list(getattr(self, 'force_includes', []))
    names = self.to_list(getattr(self, 'use', []))

    for x in names:
        self.use_rec(x)
    #endfor

    for x in use_not:
        if x in use_prec:
            del use_prec[x]
        #endif
    #endfor

    # topological sort
    out = self.tmp_use_sorted = []
    tmp = []
    for x in self.tmp_use_seen:
        for k in use_prec.values():
            if x in k:
                break
            #endif
        else:
            tmp.append(x)
        #endfor
    #endfor

    while tmp:
        e = tmp.pop()
        out.append(e)
        try:
            nlst = use_prec[e]
        except KeyError:
            pass
        else:
            del use_prec[e]
            for x in nlst:
                for y in use_prec:
                    if x in use_prec[y]:
                        break
                    #endif
                else:
                    tmp.append(x)
                #endfor
            #endfor
        #endtry
    #endwhile

    if use_prec:
        raise Errors.WafError('Cycle detected in the use processing %r' \
            % use_prec)
    #endif
    out.reverse()

    for x in out:
        y = self.bld.get_tgen_by_name(x)
        if getattr(y, 'export_system_includes', None):
            # self.system_includes may come from a global variable #2035
            self.system_includes = self.system_includes \
                + y.to_incnodes(y.export_system_includes)
        #endif

        if getattr(y, 'export_force_includes', None):
            self.force_includes = self.force_includes \
                + y.to_nodes(y.export_force_includes)
        #endif
    #endfor
#enddef

@feature('c', 'cxx', 'system_includes')
@after_method('propagate_uselib_vars', 'process_source', 'apply_incpaths')
@before_method('add_pdb_per_object')
def apply_sysinc(self):
    nodes = self.to_incnodes(
        self.to_list(getattr(self, 'system_includes', [])) \
        + self.env.SYSINCLUDES)
    self.includes_nodes += nodes
    cwd = self.get_cwd()

    if self.env.SYSINCFLAG:
        for node in nodes:
            self.env.append_value(
                'CFLAGS',
                [self.env.SYSINCFLAG] + [node.path_from(cwd)])

            self.env.append_value(
                'CXXFLAGS',
                [self.env.SYSINCFLAG] + [node.path_from(cwd)])
        #endfor
    else:
        self.env.INCPATHS = [x.path_from(cwd) for x in nodes]
    #endif
#enddef

@feature('c', 'cxx', 'system_includes')
@after_method('propagate_uselib_vars', 'process_source', 'apply_incpaths')
@before_method('add_pdb_per_object')
def apply_forceinc(self):
    if not hasattr(self, 'compiled_tasks'):
        return
    #endif

    nodes = self.to_nodes(self.to_list(getattr(self, 'force_includes', [])) \
        + self.env.FORCEINCLUDES)

    cwd = self.get_cwd()

    for node in nodes:
        self.env.append_value(
            'CFLAGS',
            [self.env.FORCEINCFLAG] + [node.path_from(cwd)])

        self.env.append_value(
            'CXXFLAGS',
            [self.env.FORCEINCFLAG] + [node.path_from(cwd)])
    #endfor

    for task in self.compiled_tasks:
        [task.dep_nodes.append(node) for node in nodes]
    #endfor
#enddef
