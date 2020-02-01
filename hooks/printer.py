def pre_export(output, conanfile, conanfile_path, reference, **kwargs):
    print("Running: pre_export")


def post_export(output, conanfile, conanfile_path, reference, **kwargs):
    print("Running: post_export")


def pre_source(output, conanfile, conanfile_path, **kwargs):
    print("Running: pre_source")


def post_source(output, conanfile, conanfile_path, **kwargs):
    print("Running: post_source")


def pre_build(output, conanfile, **kwargs):
    print("Running: pre_build")


def post_build(output, conanfile, **kwargs):
    print("Running: post_build")


def pre_package(output, conanfile, conanfile_path, **kwargs):
    print("Running: pre_package")


def post_package(output, conanfile, conanfile_path, **kwargs):
    print("Running: post_package")


def pre_upload(output, conanfile_path, reference, remote, **kwargs):
    print("Running: pre_upload")


def post_upload(output, conanfile_path, reference, remote, **kwargs):
    print("Running: post_upload")


def pre_upload_recipe(output, conanfile_path, reference, remote, **kwargs):
    print("Running: pre_upload_recipe")


def post_upload_recipe(output, conanfile_path, reference, remote, **kwargs):
    print("Running: post_upload_recipe")


def pre_upload_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    print("Running: pre_upload_package")


def post_upload_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    print("Running: post_upload_package")


def pre_download(output, reference, remote, **kwargs):
    print("Running: pre_download")


def post_download(output, conanfile_path, reference, remote, **kwargs):
    print("Running: post_download")


def pre_download_recipe(output, reference, remote, **kwargs):
    print("Running: pre_download_recipe")


def post_download_recipe(output, conanfile_path, reference, remote, **kwargs):
    print("Running: post_download_recipe")


def pre_download_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    print("Running: pre_download_package")


def post_download_package(output, conanfile_path, reference, package_id, remote, **kwargs):
    print("Running: post_download_package")


def pre_package_info(output, conanfile, reference, **kwargs):
    print("Running: pre_package_info")


def post_package_info(output, conanfile, reference, **kwargs):
    print("Running: post_package_info")
