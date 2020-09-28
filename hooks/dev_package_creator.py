import os
import re
import shutil

TEMPLATE = """
import os
import re
import shutil
from conans import *

class Conan(ConanFile):
    name = "{0}-dev"
    version = "{1}"
    license = {2}
    description = "{0} development files"
    settings = {3}
    build_requires = "{0}/{1}"
    requires = {4}

    # Avoid warning about missing build method
    def build(self):
        pass

    def package(self):
        pkg_rootpath = self.deps_cpp_info["{0}"].rootpath

        # Copy include
        include_folder = os.path.join(pkg_rootpath, "include")
        if os.path.exists(include_folder):
           shutil.copytree(include_folder, os.path.join(self.package_folder, "include"))

        # Copy static libs
        regex = re.compile(".*\.a")
        lib_folder = os.path.join(pkg_rootpath, "lib")
        for root, dirs, files in os.walk(lib_folder):
            for file in files:
                if regex.match(file):
                    rel_path = os.path.relpath(root, lib_folder)
                    file_path = os.path.join(lib_folder, rel_path, file)
                    file_dest_path = os.path.join(self.package_folder, "lib", rel_path, file)
                    if not os.path.exists(os.path.dirname(file_dest_path)):
                        os.makedirs(os.path.dirname(file_dest_path))
                    shutil.copy(file_path, file_dest_path)

        # Copy pkg-config files
        regex = re.compile(".*\.pc")
        for root, dirs, files in os.walk(pkg_rootpath):
           for file in files:
               if regex.match(file):
                   rel_path = os.path.relpath(root, pkg_rootpath)
                   file_path = os.path.join(pkg_rootpath, rel_path, file)
                   file_dest_path = os.path.join(self.package_folder, rel_path, file)
                   if not os.path.exists(os.path.dirname(file_dest_path)):
                       os.makedirs(os.path.dirname(file_dest_path))
                   shutil.copy(file_path, file_dest_path)
"""


def post_export(output, conanfile, conanfile_path, reference, **kwargs):
    # Only create developement package when ending with -dev
    if not conanfile.name.endswith("-dev"):
        return

    # Check if dev package is disabled by conanfile
    if getattr(conanfile, "no_dev_pkg", False):
        return

    # Find debug package requirements
    reqs = getattr(conanfile, "requires", ()) + getattr(conanfile, "build_requires", ())
    dev_reqs = set()
    for req in reqs:
        name, version = req.split("/")
        if name.endswith("-dev"):
            dev_reqs.add(f"{name}/{version}")

    with open(conanfile_path, "w") as cfile:
        content = TEMPLATE.format(
            conanfile.name[:-4],
            conanfile.version,
            repr(conanfile.license),
            repr(conanfile.settings),
            repr(tuple(dev_reqs)),
        )
        cfile.write(content)


def pre_upload_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    package_folder = conanfile_path.replace(
        "export/conanfile.py", f"package/{package_id}"
    )

    # Don't cleanup package for development and debug packages
    if reference.name.endswith("-dev") or reference.name.endswith("-dbg"):
        return

    # Check if dev package is disabled by conanfile
    with open(conanfile_path) as conanfile:
        if conanfile.read().find("no_dev_pkg = True"):
            return

    # Delete include
    include_folder = os.path.join(package_folder, "include")
    if os.path.exists(include_folder):
        shutil.rmtree(include_folder)

    # Delete static libs
    regex = re.compile(r".*\.a")
    lib_folder = os.path.join(package_folder, "lib")
    for root, _, files in os.walk(lib_folder):
        for file in files:
            if regex.match(file):
                rel_path = os.path.relpath(root, lib_folder)
                file_path = os.path.join(lib_folder, rel_path, file)
                os.remove(file_path)

    # Delete pkg-config files
    regex = re.compile(r".*\.pc")
    for root, _, files in os.walk(package_folder):
        for file in files:
            if regex.match(file):
                rel_path = os.path.relpath(root, package_folder)
                file_path = os.path.join(package_folder, rel_path, file)
                os.remove(file_path)
