valid_licenses = (
    "Apache",
    "BSD",
    "EPL",
    "GPL",
    "LGPL",
    "MIT",
    "MPL",
    "PSF",
    "Proprietary",
    "ZLIB",
    "custom",
)

def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    # Add warning if license and description is missing
    for field in ["license", "description"]:
        field_value = getattr(conanfile, field, None)
        if not field_value:
            output.error(f"Conanfile doesn't have '{field}'. Please add it.")
    # Check if license is valid
    licenses = [conanfile.license] if isinstance(conanfile.license, str) else conanfile.license
    for license in licenses:
        if license not in valid_licenses:
            output.error(f"Conanfile license '{license}' is invalid. Please use one of {', '.join(valid_licenses)}.")
