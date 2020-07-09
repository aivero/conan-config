import os
import re


def env_prepend(var, val, sep=os.pathsep):
    os.environ[var] = val + (sep + os.environ[var] if var in os.environ else "")


def pre_build(output, conanfile, **kwargs):
    assert conanfile
    # Set debug prefix flags
    if not hasattr(conanfile, "source_folder"):  # Needs source directory
        return
    env_prepend(
        "CFLAGS",
        "-fdebug-prefix-map=%s=%s" % (conanfile.source_folder, conanfile.name),
        " ",
    )
    env_prepend(
        "CXXFLAGS",
        "-fdebug-prefix-map=%s=%s" % (conanfile.source_folder, conanfile.name),
        " ",
    )
    env_prepend(
        "RUSTFLAGS",
        "--remap-path-prefix=%s=%s" % (conanfile.source_folder, conanfile.name),
        " ",
    )


def post_package(output, conanfile, conanfile_path, **kwargs):
    assert conanfile
    # Strip lib
    regex = re.compile(".*\.(so|a)")
    for root, dirs, files in os.walk(os.path.join(conanfile.package_folder, "lib")):
        for file in files:
            if regex.match(file):
                os.system(f"strip --strip-unneeded {os.path.join(root, file)}")

    # Strip bin
    for root, dirs, files in os.walk(os.path.join(conanfile.package_folder, "bin")):
        for file in files:
            os.system(f"strip --strip-unneeded {os.path.join(root, file)}")

    # Strip libexec
    for root, dirs, files in os.walk(os.path.join(conanfile.package_folder, "libexec")):
        for file in files:
            os.system(f"strip --strip-unneeded {os.path.join(root, file)}")

    # Copy sources to package
    # for ext in ("c", "cpp", "cpp", "h", "hpp", "hxx", "rs", "y", "l"):
    #    conanfile.copy("*." + ext, "src")


def pre_package_info(output, conanfile, reference, **kwargs):
    assert conanfile
    # Set source mapping env var
    conanfile.env_info.SOURCE_MAP.append(
        "%s|%s" % (conanfile.name, os.path.join(conanfile.package_folder, "src"))
    )
    conanfile.cpp_info.srcsdirs = ["src"]
