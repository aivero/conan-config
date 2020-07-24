import os
import re
import shutil
import sys

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
        self.copy(pattern="*")
"""


def post_package(output, conanfile, conanfile_path, **kwargs):
    assert conanfile
    # Don't create dev package for packages already ending with -dev
    if conanfile.name.endswith("-dev"):
        return

    package_folder = conanfile.package_folder
    recipe_folder = os.path.join(
        conanfile.build_folder, f"{conanfile.name}-{conanfile.version}-dev"
    )
    files_folder = os.path.join(recipe_folder, "files")

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
    for l in license:
        res += f' "{l}",'
    return res


def setting_to_str(setting):
    res = ""
    for (key, val) in setting.items():
        res += f' "{key}",'
    return res


def pre_package_info(output, conanfile, reference, **kwargs):
    c = conanfile

    build_folder = conanfile.package_folder.replace("/package/", "/build/")
    recipe_folder = os.path.join(
        build_folder, f"{conanfile.name}-{conanfile.version}-dev"
    )
    if os.path.exists(recipe_folder):
        with open(os.path.join(recipe_folder, "conanfile.py"), "w") as cfile:
            content = template.format(
                c.name, c.version, license_to_str(c.license), setting_to_str(c.settings)
            )
            cfile.write(content)

        os.system(f"{sys.argv[0]} create {recipe_folder}")
        shutil.rmtree(recipe_folder)
