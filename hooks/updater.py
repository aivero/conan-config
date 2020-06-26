import os


def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    os.system("conan config install https://codeload.github.com/aivero/conan-config/zip/master -sf conan-config-master")
