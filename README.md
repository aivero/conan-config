# Conan config
This repository contains all the shared conan configuration.

## Install
### Install config
`conan config install git@gitlab.com:aivero/public/conan/conan-config.git`

### Set platform profile
- x86_64: `conan config set general.default_profile=linux_x86_64`
- armv8: `conan config set general.default_profile=linux_armv8`


## Overview:
- `conan.conf`: Global configuration for Conan.
- `remotes.txt`: Configuration for Conan repositories.
- `settings.yml`: Collection of all possible Conan settings. E.g build_type, os, compiler
- `profiles`: Configuration for specific setups.
- `hooks`: Configuration scripts that run before or after Conan methods.
