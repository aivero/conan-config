import os


def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    os.system("conan config install https://github.com/aivero/conan-config/archive/master.zip -sf conan-config-master")
