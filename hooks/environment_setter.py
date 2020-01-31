import os

from conans import tools


def env_prepend(var, val, sep=os.pathsep):
    os.environ[var] = val + (sep + os.environ[var] if var in os.environ else "")


def pre_build(output, conanfile, reference, **kwargs):
    env_prepend("PKG_CONFIG_PATH", conanfile.build_folder, ":")


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
