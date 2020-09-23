import os
import re
import shutil

TEMPLATE = """
import os
import shutil
from conans import *

class Conan(ConanFile):
    name = "{0}-dbg"
    version = "{1}"
    license = {2}
    description = "{0} debug files"
    settings = {3}
    build_requires = "{0}/{1}"

    def package(self):
        pkg_rootpath = self.deps_cpp_info["{0}"].rootpath

        # Move src, dbg
        for folder in ("src", "dbg"):
            path = os.path.join(pkg_rootpath, folder)
            if os.path.exists(path):
               shutil.copytree(path, os.path.join(self.package_folder, folder))


    def package_info(self):
        self.env_info.SOURCE_MAP.append("%s|%s" % (self.name, os.path.join(self.package_folder, "src")))
        self.env_info.DEBUG_PATH.append(os.path.join(self.package_folder, "dbg"))
"""


def env_prepend(var, val, sep=os.pathsep):
    os.environ[var] = val + (sep + os.environ[var] if var in os.environ else "")


def post_export(output, conanfile, conanfile_path, reference, **kwargs):
    # Only create debug package when ending with -dbg
    if not conanfile.name.endswith("-dbg"):
        return

    # Don't create dev package for bootstrap packages
    if conanfile.name.startswith("bootstrap-"):
        return

    with open(conanfile_path, "w") as cfile:
        content = TEMPLATE.format(
            conanfile.name[:-4],
            conanfile.version,
            repr(conanfile.license),
            repr(conanfile.settings),
        )
        cfile.write(content)


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
                    debug_path = os.path.join(conanfile.package_folder, "dbg", root[1:])
                    if not os.path.exists(os.path.dirname(debug_path)):
                        os.makedirs(debug_path)
                    debug_file = f"{os.path.join(debug_path, file)}.debug"
                    # Extract debug info to debug file
                    os.system(
                        f"objcopy --only-keep-debug {os.path.join(root, file)} {debug_file}"
                    )
                    # Strip binary
                    os.system(
                        f"strip --strip-debug --strip-unneeded {os.path.join(root, file)}"
                    )
                    # Link binary to debug file
                    os.system(
                        f"objcopy --add-gnu-debuglink={debug_file} {os.path.join(root, file)}"
                    )

    # Copy sources to package
    regex = re.compile(r".*\.(c|C|cc|cpp|cxx|c\+\+|h|H|hh|hpp|hxx|h\+\+|rs|y|l)$")
    for root, _, files in os.walk(conanfile.build_folder):
        for file in files:
            if regex.match(file):
                rel_path = os.path.relpath(root, conanfile.build_folder)
                file_path = os.path.join(conanfile.build_folder, rel_path, file)
                file_dest_path = os.path.join(
                    conanfile.package_folder, "src", rel_path, file
                )
                if not os.path.exists(os.path.dirname(file_dest_path)):
                    os.makedirs(os.path.dirname(file_dest_path))
                shutil.copy(file_path, file_dest_path)


def pre_upload_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    package_folder = conanfile_path.replace(
        "export/conanfile.py", f"package/{package_id}"
    )

    # Don't cleanup package for bootstrap, development and debug packages
    if (
        reference.name.startswith("bootstrap-")
        and reference.name.endswith("-dev")
        and reference.name.endswith("-dbg")
    ):
        return

    # Move src, dbg
    for folder in ("src", "dbg"):
        path = os.path.join(package_folder, folder)
        if os.path.exists(path):
            shutil.rmtree(path)
