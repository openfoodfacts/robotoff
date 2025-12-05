#!/bin/bash

# http://redsymbol.net/articles/unofficial-bash-strict-mode/
set -euo pipefail
IFS=$'\n\t'

# -----------------------------------------------
# First step: copy-paste README.md to docs folder
# -----------------------------------------------

cp ./README.md ./docs/README.md

# Build mkdocs
poetry run mkdocs build --strict
