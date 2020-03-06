import os


def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    os.system("conan config install https://static-objects.gitlab.net/aivero/public/conan/conan-config/-/archive/1.0.0/conan-config-1.0.0.zip")
