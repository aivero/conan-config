import os
import shutil
from conans import *
import conans.client.tools as tools


class ConanTemplate(ConanFile):
    settings = "build_type", "compiler", "arch_build", "os_build", "libc_build"

    def __init__(self, output, runner, display_name="", user=None, channel=None):
        super().__init__(output, runner, display_name, user, channel)

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
        files = tuple(os.listdir("."))
        if "meson.build" in files:
            self.meson()
        elif "CMakeLists.txt" in files:
            self.cmake()
        elif "setup.py" in files:
            self.setuptools()
        elif "configure.ac" in files:
            self.autotools()
        else:
            self.make()

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
        self.run(
            f'python setup.py install --optimize=1 --prefix= --root="{self.package_folder}"',
            cwd=f"{self.name}-{self.version}",
        )

    def autotools(self, args=None):
        if args is None:
            args = []
        files = tuple(os.listdir(f"{self.name}-{self.version}"))
        if "configure" not in files:
            if "autogen.sh" in files:
                env = {
                    "NOCONFIGURE": "1",
                }
                with tools.environment_append(env):
                    self.run("sh autogen.sh", cwd=f"{self.name}-{self.version}")
            else:
                raise Exception("No configure or autogen.sh in source folder")
        autotools = AutoToolsBuildEnvironment(self)
        autotools.configure(f"{self.name}-{self.version}", args)
        autotools.make()
        autotools.install()

    def make(self, args=None):
        if args is None:
            args = []
        with tools.chdir(f"{self.name}-{self.version}"):
            autotools = AutoToolsBuildEnvironment(self)
            autotools.make(args)
            autotools.install(args)
