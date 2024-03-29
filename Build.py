#!/usr/bin/env python3
# encoding: utf-8

import sysconfig

from waflib import Logs, Options
from waflib.Build import BuildContext
from waflib.Configure import conf
from waflib.TaskGen import feature, before_method, after_method, taskgen_method
from waflib.Tools import waf_unit_test
from waflib.Tools.ccroot import USELIB_VARS

from Common import *

run_tests = False

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
            #endif
        #endfor
    #endif
#enddef

def build(bld):
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
    features = []

    read_option(includes, 'includes')
    read_option(export_force_includes, 'export_force_includes')
    read_option(lib, 'shlib_link')
    read_option(lib_path, 'shlib_path')
    read_option(stlib, 'stlib_link')
    read_option(stlib_path, 'stlib_path')
    read_option(use, 'use')
    read_option(features, 'features')

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
    features.append('nounity')
    if project['unity_build'] == True:
        features.append('unity')
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
            features=features,
            export_system_includes=export_includes,
            export_force_includes=export_force_includes,
            # Add an extra define that can be checked to see if a project is
            # built as a DLL or not. Needed for dllimport on windows.
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
            features=features,
            export_system_includes=export_includes,
            export_force_includes=export_force_includes,
            # Add an extra define that can be checked to see if a project is
            # built as a static library or not. This has been added because of
            # the one above, if this is for whatever reason ever needed.
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
            features=features,
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
            features=features + ['test'],
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

# Override unity's batch_size function so we can control unity builds per project
from waflib.extras import unity
@taskgen_method
def batch_size(self):
    if 'nounity' in self.features:
        return 0;
    else: # 'unity'
        return getattr(Options.options, 'batchsize', unity.MAX_BATCH)
    #endif
#enddef
