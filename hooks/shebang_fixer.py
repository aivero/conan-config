import os


def post_package(output, conanfile, conanfile_path, **kwargs):
    assert conanfile
    # Fix shebangs (Overwrite hardcoded paths in shebangs)
    if not os.path.isdir(os.path.join(conanfile.package_folder, "bin")):
        return
    for exe_name in os.listdir(os.path.join(conanfile.package_folder, "bin")):
        exe_path = os.path.join(conanfile.package_folder, "bin", exe_name)
        if os.path.isdir(exe_path):
            continue
        try:
            with open(exe_path, "r") as exe:
                lines = exe.readlines()
            shebang = lines.pop(0)
            if "python" in shebang:
                interpreter = "python"
            elif "perl" in shebang:
                interpreter = "perl"
            elif "bash" in shebang:
                interpreter = "bash"
            elif "sh" in shebang:
                interpreter = "sh"
            else:
                continue
            lines.insert(0, "#!/usr/bin/env %s\n" % interpreter)
            with open(exe_path, mode="w") as exe:
                exe.writelines(lines)
        except UnicodeDecodeError:
            pass
