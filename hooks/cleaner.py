import glob
import os
import shutil


def remove_folder(folder):
    if os.path.isdir(folder):
        shutil.rmtree(folder)


def post_package(output, conanfile, conanfile_path, **kwargs):
    assert conanfile
    # Delete libtool files
    for f in glob.glob(
        os.path.join(conanfile.package_folder, "**", "*.la"), recursive=True
    ):
        os.remove(f)
    # Delete unneeded folders in share
    for folder in ("man", "doc"):
        remove_folder(os.path.join(conanfile.package_folder, "share", folder))
