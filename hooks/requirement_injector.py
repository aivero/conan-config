import os
import re
import shutil


def post_export(output, conanfile, conanfile_path, reference, **kwargs):
    with open(conanfile_path, "r") as cfile:
        content = cfile.read()

    # Don't add generators req to generators
    if conanfile.name == "generators":
        return

    with open(conanfile_path, "w") as cfile:
        # TODO: create cleaner injection with regex or ast manipulation

        # Multi line requires
        if "    requires = (\n" in content:
            content = content.replace(
                "    requires = (\n",
                '    requires = (\n        ("generators/[^1.0.0]", "private"),\n',
            )
        # Single line requires
        elif "    requires = (" in content:
            content = content.replace(
                "    requires = (",
                '    requires = (("generators/[^1.0.0]", "private"), ',
            )
        elif "    requires = " in content:
            content = content.replace(
                "    requires = ",
                '    requires = ("generators/[^1.0.0]", "private"), ',
            )
        # No requires
        else:
            content = content.replace(
                "(ConanFile):\n",
                '(ConanFile):\n    requires = (("generators/[^1.0.0]", "private"),)\n',
            )

        cfile.write(content)
