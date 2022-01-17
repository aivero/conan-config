import os
import sys


def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    os.system(
        f"{sys.argv[0]} config install https://gitlab.com/aivero/open-source/conan-config/-/archive/master/conan-config-master.tar.gz -sf conan-config-master"
    )
