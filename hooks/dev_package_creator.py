import os
import re
import shutil
import sys
import pathlib

template = """
from conans import *

class Conan(ConanFile):
    name = "{0}-dev"
    version = "{1}"
    license ={2}
    description = "{0} development files"
    settings ={3}
    exports_sources = ["files/*"]
    requires = (
        "{0}/{1}"
    )

    def package(self):
        self.copy("*", src="files")
"""


def post_package(output, conanfile, conanfile_path, **kwargs):
    assert conanfile
    # Don't create dev package for packages already ending with -dev
    if conanfile.name.endswith("-dev"):
        return

    # Don't create dev package for bootstrap packages
    if conanfile.name.startswith("bootstrap-"):
        return

    package_folder = conanfile.package_folder
    recipe_folder = os.path.join(
        conanfile.build_folder, f"{conanfile.name}-{conanfile.version}-dev"
    )
    dev_lockfile = os.path.join(recipe_folder, "lockfile")
    files_folder = os.path.join(recipe_folder, "files")

    # Create folder for dev package files
    if not os.path.exists(os.path.dirname(files_folder)):
        os.makedirs(files_folder)

    # Create lockfile
    pathlib.Path(dev_lockfile).touch()

    # Move include
    include_folder = os.path.join(package_folder, "include")
    if os.path.exists(include_folder):
        shutil.move(include_folder, os.path.join(files_folder, "include"))

    # Move static libs
    regex = re.compile(".*\.a")
    lib_folder = os.path.join(package_folder, "lib")
    for root, dirs, files in os.walk(lib_folder):
        for file in files:
            if regex.match(file):
                rel_path = os.path.relpath(root, lib_folder)
                file_path = os.path.join(lib_folder, rel_path, file)
                file_dest_path = os.path.join(files_folder, "lib", rel_path, file)
                if not os.path.exists(os.path.dirname(file_dest_path)):
                    os.makedirs(os.path.dirname(file_dest_path))
                shutil.move(file_path, file_dest_path)

    # Move pkg-config files
    regex = re.compile(".*\.pc")
    for root, dirs, files in os.walk(package_folder):
        for file in files:
            if regex.match(file):
                rel_path = os.path.relpath(root, package_folder)
                file_path = os.path.join(package_folder, rel_path, file)
                file_dest_path = os.path.join(files_folder, rel_path, file)
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
    c = conanfile

    # Don't create dev package for bootstrap packages
    if c.name.startswith("bootstrap-"):
        return

    build_folder = c.package_folder.replace("/package/", "/build/")
    recipe_folder = os.path.join(build_folder, f"{c.name}-{c.version}-dev")
    files_folder = os.path.join(recipe_folder, "files")
    dev_lockfile = os.path.join(recipe_folder, "lockfile")
    if os.path.exists(dev_lockfile) and os.listdir(files_folder):
        os.remove(dev_lockfile)
        with open(os.path.join(recipe_folder, "conanfile.py"), "w") as cfile:
            content = template.format(
                c.name, c.version, license_to_str(c.license), setting_to_str(c.settings)
            )
            cfile.write(content)
        os.system(f"{sys.argv[0]} create {recipe_folder}")
