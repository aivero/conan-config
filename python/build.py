import os
import shutil
import pathlib
import glob
import re
import json
import yaml
import toml
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


def env_replace(env_var, string, replace=""):
    os.environ[env_var] = os.environ[env_var].replace(string, replace)


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

    @property
    def conan_home(self):
        if hasattr(self, "_conan_home"):
            return self._conan_home
        self._conan_home = call("conan", ["config", "home"])[:-1]
        return self._conan_home

    def set_name(self):
        if not self.name:
            conf_path = os.path.join(self.recipe_folder, "devops.yml")
            if os.path.exists(conf_path):
                with open(conf_path, "r") as conf_file:
                    conf = yaml.safe_load(conf_file)
                    if "name" in conf[0]:
                        self.name = conf[0]["name"]
            if not self.name:
                self.name = os.path.basename(self.recipe_folder)
        os.environ["ORIGIN_FOLDER"] = self.recipe_folder

    def set_version(self):
        version = None
        conf_path = os.path.join(self.recipe_folder, "devops.yml")
        if os.path.exists(conf_path):
            with open(conf_path, "r") as conf:
                version = yaml.safe_load(conf)[0]["version"]

        self.version = self.version or version

    @property
    def src(self):
        return f"{self.name}-{self.version}.src"

    def exe(self, command, args=None, cwd=None):
        if not args:
            args = []
        if not cwd:
            cwd = self.src
        self.run(f"{command} {' '.join(args)}", cwd=cwd)

    def get(self, url, dest_folder=None, src_folder=None):
        if not dest_folder:
            dest_folder = self.src
        tmp_folder = "get_tmp_folder"
        tools.get(url, destination=tmp_folder)
        for _, folders, _ in os.walk(tmp_folder):
            if len(folders) > 1 and not src_folder:
                raise Exception(
                    "Cannot determine which folder to rename. Please set folder argument."
                )
            else:
                folder = folders[0]
                break
        shutil.move(os.path.join(tmp_folder, folder), dest_folder)
        shutil.rmtree(tmp_folder)

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
                if opt_val == "True":
                    if "enabled" in opt_data["choices"]:
                        opt_val = "enabled"
                    elif "true" in opt_data["choices"]:
                        opt_val = "true"
                elif opt_val == "False":
                    if "disabled" in opt_data["choices"]:
                        opt_val = "disabled"
                    elif "false" in opt_data["choices"]:
                        opt_val = "false"
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

    def cmake(
        self,
        defs=None,
        targets=None,
        source_folder=None,
        build_folder=None,
        install=True,
    ):
        if defs is None:
            defs = {}
        if targets is str:
            targets = [targets]
        cmake = CMake(self)
        for key, val in defs.items():
            cmake.definitions[key] = val
        if source_folder is None:
            source_folder = self.src
        cmake.configure(source_folder=source_folder, build_folder=build_folder)
        if targets:
            for target in targets:
                cmake.build(target=target)
        else:
            cmake.build()
            if install:
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
            f'npm install -g --user root --prefix "{self.package_folder}" "{self.name}-{self.version}"'
        )

    def autotools(self, args=None, source_folder=None, target=""):
        if args is None:
            args = []
        if source_folder is None:
            source_folder = self.src
        files = tuple(os.listdir(source_folder))
        if "configure" not in files:
            # Don't run configure twice
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
        autotools = AutoToolsBuildEnvironment(self)
        # Ignore running as root (For CICD)
        os.environ["FORCE_UNSAFE_CONFIGURE"] = "1"
        autotools.configure(source_folder, args)
        if os.path.exists("Makefile"):
            build_folder = "."
        else:
            build_folder = source_folder
        with tools.chdir(build_folder):
            if target:
                autotools.make(target=target)
            else:
                autotools.make()
                autotools.install()

    def make(self, args=None, source_folder=None, target="", env=None):
        if args is None:
            args = []
        if source_folder is None:
            source_folder = self.src
        if env is None:
            env = {}
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
        cache_folder = os.path.join(self.conan_home, "cache", "cargo")
        if not os.path.exists(cache_folder):
            os.makedirs(cache_folder)
        if self.settings.build_type in ("Release", "RelWithDebInfo"):
            args.append("--release")
        if source_folder is None:
            source_folder = self.src
        self.exe("cargo build", args)


class RustRecipe(Recipe):
    settings = Recipe.settings + ("rust",)

    def package(self):
        target_folder = os.path.join(self.conan_home, "cache", "cargo")
        cargo_toml = os.path.join(self.src, "Cargo.toml")
        if not os.path.exists(cargo_toml):
            return
        manifest_raw = call("cargo", ["read-manifest", "--manifest-path", cargo_toml])
        manifest = json.loads(manifest_raw)
        for target in manifest["targets"]:
            if "cdylib" in target["kind"]:
                target = f"lib{target['name']}.so"
                dest_folder = "lib"
            elif "bin" in target["kind"]:
                target = f"{target['name']}"
                dest_folder = "bin"
            else:
                continue

            target_path = os.path.join(target_folder, target)
            dest_path = os.path.join(self.package_folder, dest_folder)

            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            if os.path.exists(target_path):
                shutil.copy(target_path, os.path.join(dest_path, target))


class PythonRecipe(Recipe):
    settings = Recipe.settings + ("python",)


class GstRecipe(Recipe):
    settings = Recipe.settings + ("gstreamer",)


class Project(Recipe):
    settings = Recipe.settings + ("release",)
    @property
    def src(self):
        return "."

class RustProject(Project, RustRecipe):
    exports_sources = [
        "Cargo.toml",
        "src/*",
        "build.rs",
        "examples/*",
        "benches/*",
    ]

    def build(self):
        self.cargo()

class GstRustProject(RustProject):
    settings = RustProject.settings + ("gstreamer",)