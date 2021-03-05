import os
import re
import shutil
import semver
import toml
from build import RustProject


def copytree(src_dir, dst_dir):
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    for item in os.listdir(src_dir):
        src = os.path.join(src_dir, item)
        dst = os.path.join(dst_dir, item)
        if os.path.isdir(src):
            copytree(src, dst)
        else:
            shutil.copy2(src, dst)


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
                copytree(src, dst)
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

    # Set version if it is not a git commit sha
    if not re.match("^[0-9a-f]{40}$", conanfile.version):
        cargo_path = os.path.join(src, "Cargo.toml")
        cargo = toml.load(cargo_path)
        version = str(conanfile.version)
        if not semver.parse(version, loose=True):
            version = f"0.0.0-{version}"
        cargo["package"]["version"] = version.replace("_", "-")
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
    workspace_path = "Cargo.toml"
    workspace = {
        "workspace": {
            "members": deps
        }
    }
    with open(workspace_path, 'w') as f:
        toml.dump(workspace, f)
