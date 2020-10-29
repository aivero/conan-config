import os
import shutil
import pathlib
import glob
import re
from conans import *
import conans.client.tools as tools


def file_contains(file, string):
    with open(file, "r", encoding="utf-8") as f:
        return string in f.read()


class Recipe(ConanFile):
    settings = "build_type", "compiler", "arch", "os", "libc"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def __init__(self, output, runner, display_name="", user=None, channel=None):
        super().__init__(output, runner, display_name, user, channel)

    def exe(self, command, cwd=None):
        if not cwd:
            cwd = f"{self.name}-{self.version}"
        self.run(command, cwd=cwd)

    def get(self, url, folder=None):
        tools.get(url)
        for _, folders, _ in os.walk("."):
            if len(folders) > 1 and not folder:
                raise Exception(
                    "Cannot determine which folder to rename. Please set folder argument."
                )
            else:
                folder = folders[0]
                break
        if folder != f"{self.name}-{self.version}":
            shutil.move(folder, f"{self.name}-{self.version}")

    def patch(self, patch, folder=None):
        if not folder:
            folder = f"{self.name}-{self.version}"
        tools.patch(folder, patch)

    def build(self):
        if not os.path.exists(f"{self.name}-{self.version}"):
            return
        files = tuple(os.listdir(f"{self.name}-{self.version}"))
        if "meson.build" in files:
            self.meson()
        elif "CMakeLists.txt" in files:
            self.cmake()
        elif "setup.py" in files:
            self.setuptools()
        elif "package.json" in files:
            self.npm()
        elif "configure.ac" in files:
            self.autotools()
        elif "Makefile" in files:
            self.make()
        else:
            raise Exception("Cannot detect build system.")

    def package(self):
        pass

    def meson(self, args=None):
        base_args = [
            "--auto-features=disabled",
            "--wrap-mode=nofallback",
        ]
        if args is None:
            args = []
        args += base_args
        meson = Meson(self)
        meson.configure(
            args,
            source_folder=f"{self.name}-{self.version}",
            pkg_config_paths=os.environ["PKG_CONFIG_PATH"].split(":"),
        )
        meson.install()

    def cmake(self, definitions=None):
        if definitions is None:
            definitions = {}
        cmake = CMake(self)
        for key, val in definitions.items():
            cmake.definitions[key] = val
        cmake.configure(source_folder=f"{self.name}-{self.version}")
        cmake.build()
        cmake.install()

    def setuptools(self):
        py_path = os.path.join(
            self.package_folder, "lib", f"python{self.settings.python}", "site-packages"
        )
        os.makedirs(py_path)
        os.environ["PYTHONPATH"] += py_path
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION"] = self.version
        self.run(
            f'python setup.py install --optimize=1 --prefix= --root="{self.package_folder}"',
            cwd=f"{self.name}-{self.version}",
        )

    def npm(self):
        self.run(
            f'npm install -g --user root --prefix "{self.package_folder}" "{self.name}-{self.version}.tgz"'
        )

    def autotools(self, args=None, source_folder=None, target=""):
        if args is None:
            args = []

        if source_folder is None:
            source_folder = f"{self.name}-{self.version}"
        files = tuple(os.listdir(f"{self.name}-{self.version}"))
        if "configure" not in files:
            env = {
                "NOCONFIGURE": "1",
            }
            if "autogen.sh" in files:
                with tools.environment_append(env):
                    self.run("sh autogen.sh", cwd=source_folder)
            elif "configure.ac" in files:
                with tools.environment_append(env):
                    self.run("autoreconf -ifv", cwd=source_folder)
            else:
                raise Exception("No configure or autogen.sh in source folder")
        lib_type_works = file_contains(
            os.path.join(source_folder, "configure"), "--enable-shared"
        )
        if lib_type_works and "shared" in self.options:
            if self.options.shared:
                args.append("--enable-shared")
                args.append("--disable-static")
            else:
                args.append("--enable-static")
                args.append("--disable-shared")
        autotools = AutoToolsBuildEnvironment(self)
        autotools.configure(source_folder, args)
        if target:
            autotools.make(target=target)
        else:
            autotools.make()
            autotools.install()

    def make(self, args=None, target=""):
        if args is None:
            args = []
        with tools.chdir(f"{self.name}-{self.version}"):
            autotools = AutoToolsBuildEnvironment(self)
            if target:
                autotools.make(args, target=target)
            else:
                autotools.make(args)
                autotools.install(args)
