import os
import shutil
import pathlib
import glob
import re
import json
import subprocess
from conans import *
import conans.client.tools as tools


def call(cmd, args, show=False):
    child = subprocess.Popen([cmd] + args, stdout=subprocess.PIPE)
    fulloutput = b""
    while True:
        output = child.stdout.readline()
        if output == b"" and child.poll() is not None:
            break
        if output:
            if show:
                print(output.decode("utf-8"), end="")
            fulloutput += output
    fulloutput = fulloutput.decode("utf-8")
    if child.poll() != 0:
        raise RuntimeError(fulloutput)
    return fulloutput


def file_contains(file, strings):
    if strings is str:
        strings = [strings]
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
        for string in strings:
            if not string in content:
                return False
    return True


class Recipe(ConanFile):
    settings = "build_type", "compiler", "arch", "os", "libc"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def __init__(self, output, runner, display_name="", user=None, channel=None):
        super().__init__(output, runner, display_name, user, channel)

    @property
    def src(self):
        return f"{self.name}-{self.version}"

    def exe(self, command, args=None, cwd=None):
        if not args:
            args = []
        if not cwd:
            cwd = self.src
        self.run(f"{command} {' '.join(args)}", cwd=cwd)

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
        if folder != self.src:
            shutil.move(folder, self.src)

    def patch(self, patch, folder=None):
        if not folder:
            folder = self.src
        tools.patch(folder, patch)

    def build(self):
        if not os.path.exists(self.src):
            return
        files = tuple(os.listdir(self.src))
        if "meson.build" in files:
            self.meson()
        elif "CMakeLists.txt" in files:
            self.cmake()
        elif "setup.py" in files:
            self.setuptools()
        elif "package.json" in files:
            self.npm()
        elif "configure.ac" in files or "configure" in files:
            self.autotools()
        elif "Makefile" in files:
            self.make()
        elif "Cargo.toml" in files:
            self.cargo()
        else:
            raise Exception("Cannot detect build system.")

    def package(self):
        pass

    def meson(self, opts=None, source_folder=None):
        args = [
            "--auto-features=disabled",
            "--wrap-mode=nofallback",
        ]
        if opts is None:
            opts = {}
        if source_folder is None:
            source_folder = self.src

        meson_file = os.path.join(source_folder, "meson.build")
        if not os.path.exists(meson_file):
            raise Exception(f"meson.build not found: {meson_file}")
        opts_data = json.loads(
            call("meson", ["introspect", "--buildoptions", meson_file])
        )
        for (opt_name, opt_val) in opts.items():
            opt_data = next(
                (opt_data for opt_data in opts_data if opt_name == opt_data["name"]),
                None,
            )
            if not opt_data:
                raise Exception(f"Unrecognized Meson option: {opt_name}")
            # Value checking
            opt_val = str(opt_val)
            if opt_data["type"] == "combo":
                if "enabled" in opt_data["choices"] and opt_val == "True":
                    opt_val = "enabled"
                elif "disabled" in opt_data["choices"] and opt_val == "False":
                    opt_val = "disabled"
                else:
                    if opt_val not in opt_data["choices"]:
                        raise Exception(f"Invalid {opt_name} value: {opt_val}")
            if opt_data["type"] == "boolean":
                if opt_val not in ("True", "False"):
                    raise Exception(f"Invalid {opt_name} value: {opt_val}")
            args.append(f"-D{opt_name}={opt_val}")

        meson = Meson(self)
        meson.configure(
            args,
            source_folder=source_folder,
            pkg_config_paths=os.environ["PKG_CONFIG_PATH"].split(":"),
        )
        meson.install()

    def cmake(self, definitions=None, source_folder=None):
        if definitions is None:
            definitions = {}
        cmake = CMake(self)
        for key, val in definitions.items():
            cmake.definitions[key] = val
        if source_folder is None:
            source_folder = self.src
        cmake.configure(source_folder=source_folder)
        cmake.build()
        cmake.install()

    def setuptools(self, source_folder=None):
        if source_folder is None:
            source_folder = self.src
        py_path = os.path.join(
            self.package_folder, "lib", f"python{self.settings.python}", "site-packages"
        )
        os.makedirs(py_path)
        os.environ["PYTHONPATH"] += py_path
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION"] = self.version
        self.run(
            f'python setup.py install --optimize=1 --prefix= --root="{self.package_folder}"',
            cwd=source_folder,
        )

    def npm(self):
        self.run(
            f'npm install -g --user root --prefix "{self.package_folder}" "{self.name}-{self.version}.tgz"'
        )

    def autotools(self, args=None, source_folder=None, target=""):
        if args is None:
            args = []
        if source_folder is None:
            source_folder = self.src
        files = tuple(os.listdir(source_folder))
        if "configure" not in files:
            os.environ["NOCONFIGURE"] = "1"
            if "autogen.sh" in files:
                self.run("sh autogen.sh", cwd=source_folder)
            elif "configure.ac" in files:
                self.run("autoreconf -ifv", cwd=source_folder)
            else:
                raise Exception("No configure or autogen.sh in source folder")
        lib_type_works = file_contains(
            os.path.join(source_folder, "configure"),
            ["--enable-shared", "--enable-static"],
        )
        if lib_type_works and "shared" in self.options:
            if self.options.shared:
                args.append("--enable-shared")
                args.append("--disable-static")
            else:
                args.append("--enable-static")
                args.append("--disable-shared")
        with tools.chdir(source_folder):
            autotools = AutoToolsBuildEnvironment(self)
            autotools.configure(args=args)
            if target:
                autotools.make(target=target)
            else:
                autotools.make()
                autotools.install()

    def make(self, args=None, source_folder=None, target=""):
        if args is None:
            args = []
        if source_folder is None:
            source_folder = self.src
        with tools.chdir(source_folder):
            autotools = AutoToolsBuildEnvironment(self)
            if target:
                autotools.make(args, target=target)
            else:
                autotools.make(args)
                autotools.install(args)

    def cargo(self, args=None, source_folder=None):
        if args is None:
            args = []
        if self.settings.build_type in ("Release", "RelWithDebInfo"):
            args.append("--release")
        if source_folder is None:
            source_folder = self.src
        self.exe("cargo build", args)


class RustRecipe(Recipe):
    settings = Recipe.settings + ("rust",)


class PythonRecipe(Recipe):
    settings = Recipe.settings + ("python",)


class GstreamerRecipe(Recipe):
    settings = Recipe.settings + ("gstreamer",)
