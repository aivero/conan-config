import os

from conans import tools


def pre_package_info(output, conanfile, reference, **kwargs):
    assert conanfile

    # Rust editable package support
    if not conanfile.in_local_cache:
        build_type = "%s" % conanfile.settings.build_type
        lib_path = os.path.join(
            conanfile.cpp_info.rootpath, "target", build_type.lower()
        )
        if os.path.isdir(lib_path):
            conanfile.env_info.LIBRARY_PATH.append(lib_path)
            conanfile.env_info.LD_LIBRARY_PATH.append(lib_path)
            conanfile.env_info.GST_PLUGIN_PATH.append(lib_path)
        return

    # Set all well defined environment variables
    conanfile.env_info.CMAKE_PREFIX_PATH.append(conanfile.cpp_info.rootpath)

    bin_path = os.path.join(conanfile.cpp_info.rootpath, "bin")
    if os.path.isdir(bin_path):
        conanfile.env_info.PATH.append(bin_path)

    lib_path = os.path.join(conanfile.cpp_info.rootpath, "lib")
    if os.path.isdir(lib_path):
        conanfile.env_info.LIBRARY_PATH.append(lib_path)
        conanfile.env_info.LD_LIBRARY_PATH.append(lib_path)
        python_lib_paths = [
            f.path
            for f in os.scandir(lib_path)
            if f.is_dir() and f.name.startswith("python")
        ]
        for python_lib_path in python_lib_paths:
            conanfile.env_info.PYTHONPATH.append(
                os.path.join(python_lib_path, "site-packages")
            )

    gir_path = os.path.join(conanfile.cpp_info.rootpath,
                            "lib", "girepository-1.0")
    if os.path.isdir(gir_path):
        conanfile.env_info.GI_TYPELIB_PATH.append(os.path.join(gir_path))

    share_path = os.path.join(conanfile.cpp_info.rootpath, "share")
    if os.path.isdir(share_path):
        conanfile.env_info.XDG_DATA_DIRS.append(share_path)

    gst_plugin_path = os.path.join(conanfile.cpp_info.rootpath, "lib", "gstreamer-1.0")
    if os.path.isdir(gst_plugin_path):
        conanfile.env_info.GST_PLUGIN_PATH.append(gst_plugin_path)

    aclocal_path = os.path.join(conanfile.package_folder, "share", "aclocal")
    if os.path.isdir(aclocal_path):
        conanfile.env_info.ACLOCAL_PATH.append(aclocal_path)

    pc_paths = [
        os.path.join(conanfile.cpp_info.rootpath, "lib", "pkgconfig"),
        os.path.join(conanfile.cpp_info.rootpath, "share", "pkgconfig"),
    ]
    for pc_path in pc_paths:
        if os.path.isdir(pc_path):
            conanfile.env_info.PKG_CONFIG_PATH.append(pc_path)
