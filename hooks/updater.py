import os
import sys


def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    os.system(
        f"{sys.argv[0]} config install https://github.com/aivero/conan-config/archive/master.zip -sf conan-config-master"
    )
