import os
import re
import shutil
import sys
import pathlib

template = """
import os
from conans import *

class Conan(ConanFile):
    name = "{0}-dbg"
    version = "{1}"
    license ={2}
    description = "{0} debug files"
    settings ={3}
    exports_sources = ["files/*"]
    requires = (
        "{0}/{1}"
    )

    def package(self):
        self.copy("*", src="files")

    def package_info(self):
        self.env_info.SOURCE_MAP.append("%s|%s" % (self.name, os.path.join(self.package_folder, "src")))
        self.env_info.DEBUG_PATH.append(os.path.join(self.package_folder, "dbg"))
        self.cpp_info.srcsdirs = ["src"]
"""


def env_prepend(var, val, sep=os.pathsep):
    os.environ[var] = val + (sep + os.environ[var] if var in os.environ else "")


def pre_build(output, conanfile, **kwargs):
    assert conanfile
    # Set debug prefix flags
    if not hasattr(conanfile, "source_folder"):  # Needs source directory
        return
    env_prepend(
        "CFLAGS",
        "-fdebug-prefix-map=%s=%s" % (conanfile.source_folder, conanfile.name),
        " ",
    )
    env_prepend(
        "CXXFLAGS",
        "-fdebug-prefix-map=%s=%s" % (conanfile.source_folder, conanfile.name),
        " ",
    )
    env_prepend(
        "RUSTFLAGS",
        "--remap-path-prefix=%s=%s" % (conanfile.source_folder, conanfile.name),
        " ",
    )


def post_package(output, conanfile, conanfile_path, **kwargs):
    assert conanfile

    # Don't create dbg package for packages already ending with -dev or -dbg
    if conanfile.name.endswith("-dev") or conanfile.name.endswith("-dbg"):
        return

    # Don't create dev package for bootstrap packages
    if conanfile.name.startswith("bootstrap-"):
        return

    build_folder = conanfile.build_folder
    recipe_folder = os.path.join(
        build_folder, f"{conanfile.name}-{conanfile.version}-dbg"
    )
    lockfile = os.path.join(recipe_folder, "lockfile")
    files_folder = os.path.join(recipe_folder, "files")

    # Create folder for dbg package files
    if not os.path.exists(os.path.dirname(files_folder)):
        os.makedirs(files_folder)

    # Create lockfile
    pathlib.Path(lockfile).touch()

    # Strip binaries and create debug files
    paths = (
        ("lib", r".*\.so.*"),
        ("bin", r".*"),
        ("libexec", r".*"),
    )
    for path in paths:
        regex = re.compile(path[1])
        for root, _, files in os.walk(os.path.join(conanfile.package_folder, path[0])):
            for file in files:
                if regex.match(file):
                    debug_path = os.path.join(files_folder, "dbg", root[1:])
                    if not os.path.exists(os.path.dirname(debug_path)):
                        os.makedirs(debug_path)
                    bin_file = os.path.join(root, file)
                    debug_file = f"{os.path.join(debug_path, file)}.debug"
                    os.system(f"objcopy --only-keep-debug {bin_file} {debug_file}")
                    os.system(f"strip -g {bin_file}")
                    os.system(f"objcopy --add-gnu-debuglink={debug_file} {bin_file}")

    # Copy sources to package
    regex = re.compile(r".*\.(c|C|cc|cpp|cxx|c\+\+|h|H|hh|hpp|hxx|h\+\+|rs|y|l)$")
    for root, _, files in os.walk(build_folder):
        for file in files:
            if (
                regex.match(file)
                and not f"{conanfile.name}-{conanfile.version}-dbg" in root
            ):
                rel_path = os.path.relpath(root, build_folder)
                file_path = os.path.join(build_folder, rel_path, file)
                file_dest_path = os.path.join(files_folder, "src", rel_path, file)
                if not os.path.exists(os.path.dirname(file_dest_path)):
                    os.makedirs(os.path.dirname(file_dest_path))
                shutil.move(file_path, file_dest_path)


def license_to_str(license):
    res = ""
    if type(license) == str:
        license = [license]
    for l in license:
        res += f' "{l}",'
    return res


def setting_to_str(setting):
    res = ""
    for (key, val) in setting.items():
        if not "." in key:
            res += f' "{key}",'
    return res


def post_package_info(output, conanfile, reference, **kwargs):
    assert conanfile

    # Don't create dev package for bootstrap packages
    if conanfile.name.startswith("bootstrap-"):
        return

    build_folder = conanfile.package_folder.replace("/package/", "/build/")
    recipe_folder = os.path.join(
        build_folder, f"{conanfile.name}-{conanfile.version}-dbg"
    )
    files_folder = os.path.join(recipe_folder, "files")
    lockfile = os.path.join(recipe_folder, "lockfile")
    if os.path.exists(lockfile) and os.listdir(files_folder):
        os.remove(lockfile)
        with open(os.path.join(recipe_folder, "conanfile.py"), "w") as cfile:
            content = template.format(
                conanfile.name,
                conanfile.version,
                license_to_str(conanfile.license),
                setting_to_str(conanfile.settings),
            )
            cfile.write(content)
        os.system(f"{sys.argv[0]} create {recipe_folder}")
