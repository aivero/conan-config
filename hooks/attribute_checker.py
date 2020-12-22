def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    # Add warning if license and description is missing
    for field in ["license", "description"]:
        field_value = getattr(conanfile, field, None)
        if not field_value:
            output.warn(f"Conanfile doesn't have '{field}'. It is recommended to add it as attribute")
