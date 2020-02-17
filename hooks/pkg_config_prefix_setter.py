import os


def replace_prefix_in_pc_file(pc_file, prefix):
    with open(pc_file) as f:
        old_prefix = ""
        # Get old prefix
        for l in f:
            if l == "prefix=":
                return f.read().replace("prefix=", "prefix=%s".format(prefix))
            if "prefix=" in l:
                old_prefix = l.split("=")[1][:-1]
                break
        f.seek(0)
        if not old_prefix:
            for l in f:
                if "libdir=" in l:
                    old_prefix = l.split("=")[1][:-5]
                    break
                if "includedir=" in l:
                    old_prefix = l.split("=")[1][:-9]
                    break
        if not old_prefix:
            raise Exception("Could not find package prefix in '%s'" % pc_file)
        f.seek(0)
        content = f.read().replace(old_prefix, prefix)
    with open(pc_file, 'w') as f:
        f.write(content)


def post_download_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    # Fix prefix in pc files
    rootpath = os.path.join(conanfile_path.split("export")[0], "package", package_id)
    pc_paths = [
        os.path.join(rootpath, "lib", "pkgconfig"),
        os.path.join(rootpath, "share", "pkgconfig"),
    ]
    for pc_path in pc_paths:
        if not os.path.isdir(pc_path):
            continue
        for pc in os.listdir(pc_path):
            replace_prefix_in_pc_file(os.path.join(pc_path, pc), rootpath)
