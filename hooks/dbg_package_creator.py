import os
import re
import shutil
import subprocess

TEMPLATE = """
from build import *

class Debug(ConanFile):
    name = "{0}-dbg"
    version = "{1}"
    license = {2}
    description = "{0} debug files"
    settings = {3}
    build_requires = "{0}/{1}"

    def build(self):
        pass

    def package(self):
        pkg_rootpath = self.deps_cpp_info["{0}"].rootpath

        # Copy src and dbg
        for folder in ("src", "dbg"):
            path = os.path.join(pkg_rootpath, folder)
            if os.path.exists(path):
               shutil.copytree(path, os.path.join(self.package_folder, folder))


    def package_info(self):
        self.env_info.SOURCE_MAP.append("{0}|%s" % os.path.join(self.package_folder, "src"))
        self.env_info.DEBUG_PATH.append(os.path.join(self.package_folder, "dbg"))
"""


def post_export(output, conanfile, conanfile_path, reference, **kwargs):
    # Only create debug package when ending with -dbg
    if not conanfile.name.endswith("-dbg"):
        return

    with open(conanfile_path, "w") as cfile:
        content = TEMPLATE.format(
            conanfile.name[:-4],
            conanfile.version,
            repr(conanfile.license),
            repr(conanfile.settings),
        )
        cfile.write(content)


def run(exe, args=None, env=None):
    if not args:
        args = []
    if not shutil.which(exe):
        return (bytes("", "utf8"), bytes(f"Command '{exe}' not found", "utf8"), 127)
    cmd = f"{exe} {' '.join(args)}"
    if env or env == {}:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, env=env)
    else:
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    return (stdout, stderr, proc.wait())


def post_package(output, conanfile, conanfile_path, **kwargs):
    assert conanfile

    # Don't create debug files in debug packages
    if conanfile.name.endswith("-dbg"):
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
                if not regex.match(file):
                    continue
                bin_file = os.path.join(root, file)
                # see https://www.zeuthen.desy.de/dv/documentation/unixguide/infohtml/gdb/Separate-Debug-Files.html
                # `...gdb looks up the named file in the directory of the executable file, 
                #  then in a subdirectory of that directory named .debug,...`
                dbg_path = os.path.join(os.path.dirname(bin_file), ".debug")
                if not os.path.exists(dbg_path):
                    os.makedirs(dbg_path)
                dbg_file = f"{os.path.join(dbg_path, file)}.debug"
                # Check if file has debug_info
                stdout, _, _ = run("file", [bin_file])
                if not b"debug_info" in stdout:
                    # Some files without debug_info can still be stripped
                    if b"not stripped" in stdout:
                        run("strip", ["--strip-all", bin_file])
                    continue
                print("Stripping file: " + bin_file +"\nDebug file at: " + dbg_file)
                # Extract debug info to debug file
                run("objcopy", ["--only-keep-debug", bin_file, dbg_file])
                # Strip binary
                run("strip", ["--strip-debug", "--strip-unneeded", bin_file])
                # Link binary to debug file
                run("objcopy", [f"--add-gnu-debuglink={dbg_file}", bin_file])

    # Copy sources to package
    regex = re.compile(r".*\.(c|C|cc|cpp|cxx|c\+\+|h|H|hh|hpp|hxx|h\+\+|rs|y|l)$")
    for root, _, files in os.walk(conanfile.build_folder):
        for file in files:
            if regex.match(file):
                rel_path = os.path.relpath(root, conanfile.build_folder)
                file_path = os.path.join(conanfile.build_folder, rel_path, file)
                file_dest_path = os.path.join(conanfile.package_folder, "src", rel_path, file)
                if not os.path.exists(os.path.dirname(file_dest_path)):
                    os.makedirs(os.path.dirname(file_dest_path))
                shutil.copy(file_path, file_dest_path)


def pre_upload_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    package_folder = conanfile_path.replace("export/conanfile.py", f"package/{package_id}")

    # Don't cleanup package for debug packages
    if reference.name.endswith("-dbg"):
        return

    # Delete src, dbg
    for folder in ("src", "dbg"):
        path = os.path.join(package_folder, folder)
        if os.path.exists(path):
            shutil.rmtree(path)
