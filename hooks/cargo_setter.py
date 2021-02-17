import os
import shutil
from distutils.dir_util import copy_tree
import semver
import toml
from build import RustProject


def copy_dependency(project_path, origin):
    deps = [project_path]
    cargo_path = os.path.join(project_path, "Cargo.toml")
    cargo = toml.load(cargo_path)
    if "dependencies" in cargo:
        for _, dep in cargo["dependencies"].items():
            if "path" in dep and ".." in dep["path"]:
                src = os.path.realpath(os.path.join(
                    origin, dep["path"]))
                dst = os.path.realpath(os.path.join(project_path, dep["path"]))
                copy_tree(src, dst)
                deps += copy_dependency(dst, src)
    return deps


def post_source(output, conanfile, **kwargs):
    assert conanfile
    if not isinstance(conanfile, RustProject):
        return

    # Copy project files to subdir
    project_files = os.listdir(conanfile.source_folder)
    src = os.path.join(conanfile.source_folder, conanfile.src)
    os.mkdir(src)
    for pfile in project_files:
        shutil.move(pfile, src)

    # Load cargo project file
    cargo_path = os.path.join(src, "Cargo.toml")
    cargo = toml.load(cargo_path)

    # Set version
    version = str(conanfile.version)
    if not semver.parse(version, loose=True):
        version = f"0.0.0-{version}"
    cargo["package"]["version"] = version
    with open(cargo_path, 'w') as f:
        toml.dump(cargo, f)


def pre_build(output, conanfile, **kwargs):
    assert conanfile
    if not isinstance(conanfile, RustProject):
        return

    # Copy dependency source files to source folder
    src = os.path.join(conanfile.source_folder, conanfile.src)
    deps = copy_dependency(src, os.environ["ORIGIN_FOLDER"])

    # Get relative path to deps
    deps = list(map(lambda dep: os.path.relpath(
        dep, conanfile.source_folder), deps))

    # Create workspace
    workspace_path = os.path.join("Cargo.toml")
    workspace = {
        "workspace": {
            "members": deps
        }
    }
    with open(workspace_path, 'w') as f:
        toml.dump(workspace, f)
