def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    # Set url if it does not exist
    if not hasattr(conanfile, "url"):
        conanfile.url = f"https://github.com/aivero/conan-{conanfile.name}"
