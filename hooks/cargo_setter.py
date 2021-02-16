import toml
import os
import semver


def pre_build(output, conanfile, **kwargs):
    assert conanfile
    if not os.path.exists("Cargo.toml"):
        return
    version = str(conanfile.version)
    if not semver.parse(version, loose=True):
        version = f"0.0.0-{version}"
    cargo = toml.load("Cargo.toml")
    if "dependencies" in cargo:
        for name, dep in cargo["dependencies"].items():
            if "path" in dep and ".." in dep["path"]:
                dep["path"] = dep["path"].replace(
                    "..", os.path.dirname(os.environ["ORIGIN_FOLDER"]))

    cargo["package"]["version"] = version
    cargo["workspace"] = {}
    with open('Cargo.toml', 'w') as f:
        toml.dump(cargo, f)
