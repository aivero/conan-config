# Conan config
Aivero conan configuration

## Install
### Install config
`conan config install https://gitlab.com/aivero/open-source/conan-config/-/archive/master/conan-config-master.tar.gz -sf conan-config-master`

### Set platform profile
- x86_64: `conan config set general.default_profile=linux_x86_64`
- armv8: `conan config set general.default_profile=linux_armv8`
- NVIDIA TX2/Xavier: `conan config set general.default_profile=linux_armv8_l4t_t186_release`
- NVIDIA TX1/Nano: `conan config set general.default_profile=linux_armv8_l4t_t210_release`


## Overview:
- `conan.conf`: Global configuration for Conan.
- `remotes.txt`: Configuration for Conan repositories.
- `settings.yml`: Collection of all possible Conan settings. E.g build_type, os, compiler
- `profiles`: Configuration for specific setups.
- `hooks`: Configuration scripts that run before or after Conan methods.
