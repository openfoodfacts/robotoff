#!/bin/bash

# Script to safely download and uncompress Nutriscore model from Github.
# Usage: run `sh ./deploy/download-nutriscore.sh` from root directory.
#
# If the template is already in place, no action is performed. If the 
# model does not exist, it is downloaded and unzipped. The .tar.gz 
# file is then deleted.

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'

# -----------------------------------
# First step: copy-paste README.md to doc
# -----------------------------------

cp ./README.md ./doc/README.md

# Build mkdocs
poetry run mkdocs build --strict
