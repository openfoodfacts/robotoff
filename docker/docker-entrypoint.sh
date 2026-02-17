#!/bin/bash

set -e

# activate our virtual environment here
. /opt/robotoff/.venv/bin/activate

PRE_ARGS=()

# add uv run for robotoff-cli, because we are lazy
if [[ "$1" == "robotoff-cli" ]]
then
  PRE_ARGS=( uv run )
fi

# You can put other setup logic here

# Evaluating passed command:
exec "${PRE_ARGS[@]}" "$@"
