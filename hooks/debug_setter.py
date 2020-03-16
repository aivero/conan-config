import os


def env_prepend(var, val, sep=os.pathsep):
    os.environ[var] = val + (sep + os.environ[var] if var in os.environ else "")


def pre_build(output, conanfile, **kwargs):
    assert conanfile
    # Set debug prefix flags
    if not (hasattr(conanfile, "source_folder")  # Needs source directory
            and "build_type" in conanfile.settings.fields  # Needs build_type setting
            and conanfile.settings.build_type == "Debug"  # Only for Debug build_type
            ):
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
    # Copy sources to package
    if not ("build_type" in conanfile.settings.fields  # Needs build_type setting
            and conanfile.settings.build_type == "Debug"  # Only for Debug build_type
            ):
        return
    for ext in ("c", "cpp", "cpp", "h", "hpp", "hxx", "rs", "y", "l"):
        conanfile.copy("*." + ext, "src")


def pre_package_info(output, conanfile, reference, **kwargs):
    assert conanfile
    # Set source mapping env var
    if not ("build_type" in conanfile.settings.fields  # Needs build_type setting
            and conanfile.settings.build_type == "Debug"  # Only for Debug build_type
            ):
        return
    conanfile.env_info.SOURCE_MAP.append("%s|%s" % (conanfile.name, os.path.join(conanfile.package_folder, "src")))
    conanfile.cpp_info.srcsdirs = ["src"]
