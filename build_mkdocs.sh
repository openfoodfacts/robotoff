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

# -----------------------------------
# Second step: generate CLI reference
# -----------------------------------

# Path to CLI reference (auto-generated)
cli_md=doc/references/cli.md

# Generate CLI reference
poetry run typer robotoff/cli/main.py utils docs --name robotoff-cli --output $cli_md

# Remove header (first line) in CLI reference
# Taken from https://www.baeldung.com/linux/remove-first-line-text-file#using-thesed-command
sed -i -e '1d' ${cli_md}

# Replace header (first line) in CLI reference
# Taken from https://www.cyberciti.biz/faq/bash-prepend-text-lines-to-file/
first_lines="# CLI Reference\n\nDocumentation auto-generated using [typer-cli](https://github.com/tiangolo/typer-cli).\n\n"
echo -e "$(echo $first_lines) $(cat $cli_md)" > $cli_md

# Build mkdocs
poetry run mkdocs build --strict
