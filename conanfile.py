#!/usr/bin/env python
# -*- coding: utf-8 -*-

from multiprocessing import cpu_count
from conans import ConanFile, tools
from conans.errors import ConanException
import os


class BotanConan(ConanFile):
    name = 'botan'
    version = '2.7.0'
    url = "https://github.com/bincrafters/conan-botan"
    license = "BSD 2-clause"
    exports = ["LICENSE.md"]
    description = "Botan is a cryptography library written in C++11."
    settings = (
        'os',
        'arch',
        'compiler',
        'build_type'
    )
    options = {
        'amalgamation': [True, False],
        'bzip2': [True, False],
        'debug_info': [True, False],
        'openssl': [True, False],
        'quiet':   [True, False],
        'shared': [True, False],
        'single_amalgamation': [True, False],
        'sqlite3': [True, False],
        'zlib': [True, False],
    }
    default_options = (
        'amalgamation=True',
        'bzip2=False',
        'debug_info=False',
        'openssl=False',
        'quiet=True',
        'shared=True',
        'single_amalgamation=False',
        'sqlite3=False',
        'zlib=False',
    )

    def requirements(self):
        if self.options.bzip2:
            self.requires('bzip2/[>=1.0]@conan/stable')
        if self.options.openssl:
            self.requires('OpenSSL/[>=1.0.2m]@conan/stable')
        if self.options.zlib:
            self.requires('zlib/[>=1.2]@conan/stable')
        if self.options.sqlite3:
            self.requires('sqlite3/[>=3.18]@bincrafters/stable')

    def config_options(self):
        if self.settings.compiler != 'Visual Studio':
            self.check_cxx_abi_settings()

    def source(self):
        source_url = "https://github.com/randombit/botan/archive"
        tools.get("{0}/{1}.tar.gz".format(source_url, self.version))
        extracted_dir = "botan-" + self.version
        os.rename(extracted_dir, "sources")

    def build(self):
        with tools.chdir('sources'):
            configure_cmd = self.create_configure_cmd()
            self.output.info('Running command: ' + configure_cmd)
            self.run(configure_cmd)

            make_cmd = self.create_make_cmd()
            self.output.info('Running command: ' + make_cmd)
            self.run(make_cmd)

    def package(self):
        self.copy(pattern="license.txt", src="sources")
        with tools.chdir("sources"):
            self.output.info('Files are copied via make/pkg-config')
            make_install_cmd = self.get_make_install_cmd()
            self.output.info('Running command: ' + make_install_cmd)
            self.run(make_install_cmd)

        if self.options.shared and self.settings.compiler != "Visual Studio":
            os.unlink(os.path.join(self.package_folder, 'lib', 'libbotan-2.a'))

    def package_info(self):
        if self.settings.compiler == 'Visual Studio':
            if self.settings.build_type == 'Debug':
                self.cpp_info.libs.append('botand')
            else:
                self.cpp_info.libs.append('botan')
        else:
            self.cpp_info.libs.extend(['botan-2', 'dl'])
            if self.settings.os == 'Linux':
                self.cpp_info.libs.append('rt')
            if self.settings.os == 'Macos':
                self.cpp_info.exelinkflags = ['-framework Security']
            if not self.options.shared:
                self.cpp_info.libs.append('pthread')

        self.cpp_info.libdirs = ['lib']
        self.cpp_info.bindirs = ['lib', 'bin']
        self.cpp_info.includedirs = ['include/botan-2']

    def create_configure_cmd(self):
        if self.settings.compiler in ('clang', 'apple-clang'):
            botan_compiler = 'clang'
        elif self.settings.compiler == 'gcc':
            botan_compiler = 'gcc'
        else:
            botan_compiler = 'msvc'

        botan_abi_flags = []

        if self.is_linux_clang_libcxx():
            botan_abi_flags.extend(["-stdlib=libc++", "-lc++abi"])

        if botan_compiler in ['clang', 'apple-clang', 'gcc']:
            if self.settings.arch == "x86":
                botan_abi_flags.append('-m32')
            elif self.settings.arch == "x86_64":
                botan_abi_flags.append('-m64')

        botan_abi = ' '.join(botan_abi_flags) if botan_abi_flags else ' '

        if self.options.single_amalgamation: self.options.amalgamation = True

        build_flags = []

        if self.options.amalgamation: build_flags.append('--amalgamation')

        if self.options.single_amalgamation: build_flags.append('--single-amalgamation-file')

        if self.options.bzip2: build_flags.append('--with-bzip2')

        if self.options.openssl: build_flags.append('--with-openssl')

        if self.options.quiet: build_flags.append('--quiet')

        if self.options.sqlite3: build_flags.append('--with-sqlite3')

        if self.options.zlib: build_flags.append('--with-zlib')

        if self.options.debug_info: build_flags.append('--with-debug-info')

        if str(self.settings.build_type).lower() == 'debug': build_flags.append('--debug-mode')

        if not self.options.shared: build_flags.append('--disable-shared')

        call_python = 'python' if self.settings.os == 'Windows' else ''

        configure_cmd = ('{python_call} ./configure.py'
                         ' --distribution-info="Conan"'
                         ' --cc-abi-flags="{abi}"'
                         ' --cc={compiler}'
                         ' --cpu={cpu}'
                         ' --prefix={prefix}'
                         ' {build_flags}').format(
                          python_call=call_python,
                          abi=botan_abi,
                          compiler=botan_compiler,
                          cpu=self.settings.arch,
                          prefix=self.package_folder,
                          build_flags=' '.join(build_flags),
                      )

        return configure_cmd

    def create_make_cmd(self):
        if self.settings.os == 'Windows':
            #self.patch_makefile_win()
            make_cmd = self.get_nmake_cmd()
        else:
            make_cmd = self.get_make_cmd()
        return make_cmd

    def check_cxx_abi_settings(self):
        compiler = self.settings.compiler
        version = float(self.settings.compiler.version.value)
        libcxx = compiler.libcxx
        if compiler == 'gcc' and version > 5 and libcxx != 'libstdc++11':
            raise ConanException(
                'Using Botan with GCC > 5 on Linux requires '
                '"compiler.libcxx=libstdc++11"')
        elif compiler == 'clang' and libcxx not in ['libstdc++11', 'libc++']:
            raise ConanException(
                'Using Botan with Clang on Linux requires either '
                '"compiler.libcxx=libstdc++11" '
                'or '
                '"compiler.libcxx=libc++"')

    def get_make_cmd(self):

        if self.is_linux_clang_libcxx():
            make_ldflags = 'LDFLAGS=-lc++abi'
        else:
            make_ldflags = ''

        botan_quiet = '--quiet' if self.options.quiet else ''

        make_cmd = ('{ldflags}'
                    ' make'
                    ' {quiet}'
                    ' -j{cpucount} 1>&1').format(
                        ldflags=make_ldflags,
                        quiet=botan_quiet,
                        cpucount=cpu_count()
                    )
        return make_cmd

    def get_nmake_cmd(self):
        vcvars = tools.vcvars_command(self.settings)
        make_cmd = vcvars + ' && nmake'
        return make_cmd

    def patch_makefile_win(self):
        # Todo: Remove this patch when fixed in trunk, Botan issue #1297
        tools.replace_in_file("Makefile",
                              r"$(SCRIPTS_DIR)\install.py",
                              r"python $(SCRIPTS_DIR)\install.py")

        # Todo: Remove this patch when fixed in trunk, Botan issue #210
        if str.startswith(str(self.settings.compiler.runtime), "MT"):
            tools.replace_in_file("Makefile", r"/MD", r"/MT")

    def get_make_install_cmd(self):
        if self.settings.os == 'Windows':
            vcvars = tools.vcvars_command(self.settings)
            make_install_cmd = vcvars + ' && nmake install'
        else:
            make_install_cmd = 'make install'
        return make_install_cmd

    def is_linux_clang_libcxx(self):
        return (
            self.settings.os == 'Linux' and
            self.settings.compiler == 'clang' and
            self.settings.compiler.libcxx == 'libc++'
        )
