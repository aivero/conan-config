import os

from conans import tools


def pre_package_info(output, conanfile, reference, **kwargs):
    assert conanfile

    conanfile.env_info.CMAKE_PREFIX_PATH.append(conanfile.cpp_info.rootpath)

    bin_path = os.path.join(conanfile.cpp_info.rootpath, "bin")
    if os.path.isdir(bin_path):
        conanfile.env_info.PATH.append(bin_path)

    lib_path = os.path.join(conanfile.cpp_info.rootpath, "lib")
    if os.path.isdir(lib_path):
        conanfile.env_info.LIBRARY_PATH.append(lib_path)
        conanfile.env_info.LD_LIBRARY_PATH.append(lib_path)

    share_path = os.path.join(conanfile.cpp_info.rootpath, "share")
    if os.path.isdir(share_path):
        conanfile.env_info.XDG_DATA_DIRS.append(share_path)

    pc_paths = [
        os.path.join(conanfile.cpp_info.rootpath, "lib", "pkgconfig"),
        os.path.join(conanfile.cpp_info.rootpath, "share", "pkgconfig"),
    ]
    for pc_path in pc_paths:
        if os.path.isdir(pc_path):
            conanfile.env_info.PKG_CONFIG_PATH.append(pc_path)
