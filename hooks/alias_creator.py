from build import *


def write_metadata(path, key, val):
    metadata = {}
    metadata_path = os.path.join(path, METADATA_FILE)
    if os.path.exists(metadata_path):
        with open(metadata_path) as metadata_file:
            metadata = yaml.load(metadata_file, Loader=yaml.Loader)
    metadata[key] = val
    with open(metadata_path, "w") as metadata_file:
        yaml.dump(metadata, metadata_file, Dumper=yaml.Dumper)


def pre_export(output, conanfile, conanfile_path, **kwargs):
    assert conanfile
    # Create branch alias for sha commit versions
    if re.match("^[0-9a-f]{40}$", conanfile.version):
        output.info(
            f"Creating alias '{conanfile.name}/{branch()}' to '{conanfile.name}/{conanfile.version}'"
        )
        os.system(
            f"conan alias {conanfile.name}/{branch()} {conanfile.name}/{conanfile.version}"
        )
    else:
        output.info(f"Not creating alias for '{conanfile.name}/{conanfile.version}'")


def post_export(output, conanfile, conanfile_path, **kwargs):
    export_path = os.path.dirname(conanfile_path)
    write_metadata(export_path, "commit", commit())
    write_metadata(export_path, "branch", branch())
