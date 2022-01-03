import os
import shutil
import pathlib
import glob
import re
import json
import yaml
import toml
import subprocess
import sys
from conans import *
import conans.client.tools as tools

METADATA_FILE = "metadata.yml"
DEVOPS_FILE = "devops.yml"


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


def env_prepend(var, val, sep=os.pathsep):
    os.environ[var] = val + (sep +
                             os.environ[var] if var in os.environ else "")


def file_contains(file, strings):
    if strings is str:
        strings = [strings]
    with open(file, "r", encoding="utf-8") as f:
        content = f.read()
        for string in strings:
            if not string in content:
                return False
    return True


def read_metadata(key):
    metadata = {}
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as metadata_file:
            return yaml.load(metadata_file)[key]


_commit = None


def commit():
    global _commit
    if _commit:
        return _commit
    if "GITHUB_SHA" in os.environ:
        _commit = os.environ["GITHUB_SHA"]
        return _commit
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as metadata_file:
            _commit = yaml.load(metadata_file)["commit"]
            return _commit
    _commit = call("git", ["rev-parse", "HEAD"])[:-1]
    return _commit


_branch = None


def branch():
    global _branch
    if _branch:
        return _branch
    if "GIT_REF" in os.environ:
        _branch = os.environ["GIT_REF"]
        return _branch
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE) as metadata_file:
            _branch = yaml.load(metadata_file)["branch"]
            return _branch
    _branch = call("git", ["rev-parse", "--abbrev-ref", "HEAD"])[:-1]
    if _branch == "":
        _branch = "detached-head"
    return _branch


class Recipe(ConanFile):
    settings = "build_type", "compiler", "arch", "os", "libc"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    _conan_home = None
    _conan_storage = None
    requires = (("generators/[^1.0.0]", "private"), )

    @property
    def conan_home(self):
        if self._conan_home:
            return self._conan_home
        self._conan_home = call(sys.argv[0], ["config", "home"])[:-1]
        return self._conan_home

    @property
    def conan_storage(self):
        if self._conan_storage:
            return self._conan_storage
        self._conan_storage = call(sys.argv[0],
                                   ["config", "get", "storage.path"])[:-1]
        return self._conan_storage

    def set_name(self):
        os.environ["ORIGIN_FOLDER"] = self.recipe_folder
        # Get name from argument
        if self.name:
            return
        # Get name from devops.yml
        conf_path = os.path.join(self.recipe_folder, DEVOPS_FILE)
        if os.path.exists(conf_path):
            with open(conf_path, "r") as conf_file:
                conf = yaml.safe_load(conf_file)
                if conf[0] and "name" in conf[0]:
                    self.name = conf[0]["name"]
                    return
        # Get name from folder
        self.name = os.path.basename(self.recipe_folder)

    def set_version(self):
        # Get version from argument
        if self.version:
            return
        # Get version from devops.yml
        conf_path = os.path.join(self.recipe_folder, DEVOPS_FILE)
        if os.path.exists(conf_path):
            with open(conf_path, "r") as conf_file:
                conf = yaml.safe_load(conf_file)
                if conf[0] and "version" in conf[0]:
                    self.version = conf[0]["version"]
                    return
        # Get version from git
        self.version = commit()

    def set_env(self):
        env_prepend(
            "CFLAGS",
            "-fdebug-prefix-map=%s=%s" % (self.build_folder, self.name),
            " ",
        )
        env_prepend(
            "CXXFLAGS",
            "-fdebug-prefix-map=%s=%s" % (self.build_folder, self.name),
            " ",
        )

    @property
    def src(self):
        return f"{self.name}-{self.version}.src"

    def exe(self, command, args=None, cwd=None):
        if not args:
            args = []
        if not cwd:
            cwd = self.src
        self.run(f"{command} {' '.join(args)}", cwd=cwd)

    def download(self, url, filename, dest_folder=None):
        if not dest_folder:
            dest_folder = self.src
        tools.download(url, filename)
        shutil.move(filename, os.path.join(dest_folder, filename))

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

    def rmdir(self, dir_name):
        shutil.rmtree(dir_name)

    def extract(self, archive):
        tools.untargz(os.path.join(self.src, archive))

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

    def meson(self, opts=None, source_folder=None, opt_check=True):
        self.set_env()
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
        if opt_check:
            opts_data = json.loads(
                call("meson", ["introspect", "--buildoptions", meson_file]))
            for (opt_name, opt_val) in opts.items():
                opt_data = next(
                    (opt_data for opt_data in opts_data
                     if opt_name == opt_data["name"]),
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
                        elif "yes" in opt_data["choices"]:
                            opt_val = "yes"
                    elif opt_val == "False":
                        if "disabled" in opt_data["choices"]:
                            opt_val = "disabled"
                        elif "false" in opt_data["choices"]:
                            opt_val = "false"
                        elif "no" in opt_data["choices"]:
                            opt_val = "no"
                    if opt_val not in opt_data["choices"]:
                        raise Exception(f"Invalid {opt_name} value: {opt_val}")
                if opt_data["type"] == "boolean":
                    if opt_val not in ("True", "False"):
                        raise Exception(f"Invalid {opt_name} value: {opt_val}")
                args.append(f"-D{opt_name}={opt_val}")
        else:
            for (opt_name, opt_val) in opts.items():
                opt_val = str(opt_val)
                if opt_val == "True":
                    opt_val = "true"
                elif opt_val == "False":
                    opt_val = "false"
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
        self.set_env()
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
        self.set_env()
        if source_folder is None:
            source_folder = self.src
        py_path = os.path.join(self.package_folder, "lib",
                               f"python{self.settings.python}",
                               "site-packages")
        os.makedirs(py_path)
        if "PYTHONPATH" in os.environ:
            os.environ["PYTHONPATH"] += os.pathsep + py_path
        else:
            os.environ["PYTHONPATH"] = py_path
        os.environ["SETUPTOOLS_SCM_PRETEND_VERSION"] = self.version
        self.run(
            f'python setup.py install --optimize=1 --prefix= --root="{self.package_folder}"',
            cwd=source_folder,
        )

    def pip(self):
        self.set_env()
        self.run(f"pip install --prefix={self.package_folder} -r requirements.txt")
        py_path = os.path.join(self.package_folder, "lib",
                               f"python{self.settings.python}",
                               "site-packages")
        os.environ["PYTHONPATH"] += os.pathsep + py_path


    def npm(self):
        self.set_env()
        self.run(
            f'npm install -g --user root --prefix "{self.package_folder}" "{self.name}-{self.version}"'
        )

    def autotools(self,
                  args=None,
                  source_folder=None,
                  target="",
                  make_args=None,
                  env=None):
        self.set_env()
        if args is None:
            args = []
        if make_args is None:
            make_args = []
        if source_folder is None:
            source_folder = self.src
        if env is None:
            env = {}
        with tools.environment_append(env):
            files = tuple(os.listdir(source_folder))
            if "configure" not in files:
                # Don't run configure twice
                os.environ["NOCONFIGURE"] = "1"
                if "autogen.sh" in files:
                    self.run("sh autogen.sh", cwd=source_folder)
                elif "configure.ac" in files:
                    self.run("autoreconf -ifv", cwd=source_folder)
                else:
                    raise Exception(
                        "No configure or autogen.sh in source folder")
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
                    autotools.make(make_args, target=target)
                else:
                    autotools.make(make_args)
                    autotools.install(make_args)

    def make(self, args=None, source_folder=None, target="", env=None):
        self.set_env()
        if args is None:
            args = []
        if source_folder is None:
            source_folder = self.src
        if env is None:
            env = {}
        with tools.chdir(source_folder), tools.environment_append(env):
            autotools = AutoToolsBuildEnvironment(self)
            if target:
                autotools.make(args, target=target)
            else:
                autotools.make(args)
                autotools.install(args)

    def cargo(self, args=None, source_folder=None, clean=None):
        self.set_env()
        if args is None:
            args = []
        cache_folder = os.path.join(self.conan_home, "cache", "cargo")
        if not os.path.exists(cache_folder):
            os.makedirs(cache_folder)
        if clean:
            for pkg in clean:
                self.exe("cargo clean -p", [pkg])
        if self.settings.build_type in ("Release", "RelWithDebInfo"):
            args.append("--release")
        if source_folder is None:
            source_folder = self.src
        self.exe("cargo build", args)


class RustRecipe(Recipe):
    settings = Recipe.settings + ("rust", )

    def package(self):
        cargo_toml = os.path.join(self.src, "Cargo.toml")
        if not os.path.exists(cargo_toml):
            return

        manifest_raw = call("cargo",
                            ["read-manifest", "--manifest-path", cargo_toml])
        manifest = json.loads(manifest_raw)

        metadata_raw = call("cargo",
                            ["metadata", "--manifest-path", cargo_toml])
        metadata = json.loads(metadata_raw)

        target_folder = metadata["target_directory"]

        # Automatically add cdylibs and bins
        for target in manifest["targets"]:
            if "cdylib" in target["kind"] or "dylib" in target["kind"]:
                name = target["name"].replace("-", "_")
                target = f"lib{name}.so"
                dest_folder = "lib"
            elif "bin" in target["kind"]:
                target = target["name"]
                dest_folder = "bin"
            else:
                continue

            if self.settings.build_type in ("Release", "RelWithDebInfo"):
                build_dir = "release"
            else:
                build_dir = "debug"
            target_path = os.path.join(target_folder, build_dir, target)
            dest_path = os.path.join(self.package_folder, dest_folder)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            if os.path.exists(target_path):
                shutil.copy(target_path, os.path.join(dest_path, target))


class PythonRecipe(Recipe):
    settings = Recipe.settings + ("python", )


class GstRecipe(Recipe):
    settings = Recipe.settings + ("gstreamer", )


class Project(Recipe):
    @property
    def src(self):
        return "."


class GstProject(Project, GstRecipe):
    pass


class RustProject(Project, RustRecipe):
    exports_sources = [
        "Cargo.toml",
        "src/*",
        "build.rs",
        "examples/*",
        "benches/*",
    ]

    @property
    def src(self):
        return self.name

    def build(self):
        self.cargo()


class GstRustProject(GstProject, RustProject):
    def package(self):
        target_folder = os.path.join(self.conan_home, "cache", "cargo")
        cargo_toml = os.path.join(self.src, "Cargo.toml")
        if not os.path.exists(cargo_toml):
            return
        manifest_raw = call("cargo",
                            ["read-manifest", "--manifest-path", cargo_toml])
        manifest = json.loads(manifest_raw)
        # (Copy gstreamer elements to lib/streamer-1.0)
        for target in manifest["targets"]:
            if "cdylib" in target["kind"]:
                name = target["name"].replace("-", "_")
                target = f"lib{name}.so"
                dest_folder = os.path.join("lib", "gstreamer-1.0")
            elif "dylib" in target["kind"]:
                name = target["name"].replace("-", "_")
                target = f"lib{name}.so"
                dest_folder = "lib"
            elif "bin" in target["kind"]:
                target = target["name"]
                dest_folder = "bin"
            else:
                continue

            if self.settings.build_type in ("Release", "RelWithDebInfo"):
                build_dir = "release"
            else:
                build_dir = "debug"
            target_path = os.path.join(target_folder, build_dir, target)
            dest_path = os.path.join(self.package_folder, dest_folder)
            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            if os.path.exists(target_path):
                shutil.copy(target_path, os.path.join(dest_path, target))
