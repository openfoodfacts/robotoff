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

# 
TF_NUTRISCORE_URL="https://github.com/openfoodfacts/robotoff-models/releases/download/tf-nutriscore-1.0/saved_model.tar.gz"
TF_NUTRISCORE_DIR_PATH="./tf_models/nutriscore/1"
TF_NUTRISCORE_TARGZ_PATH="${TF_NUTRISCORE_DIR_PATH}/saved_model.tar.gz"
TF_NUTRISCORE_MODEL_PATH="${TF_NUTRISCORE_DIR_PATH}/saved_model/"

if [ ! -d "$TF_NUTRISCORE_DIR_PATH" ]; then
    echo "$TF_NUTRISCORE_DIR_PATH does not exist. Creating it."
    mkdir -p $TF_NUTRISCORE_DIR_PATH
fi

if [ ! -d "$TF_NUTRISCORE_MODEL_PATH" ]; then
    echo "$TF_NUTRISCORE_MODEL_PATH does not exist."
    
    if [ ! -f "$TF_NUTRISCORE_TARGZ_PATH" ]; then
        echo "$TF_NUTRISCORE_TARGZ_PATH does not exist."
        echo "Saved model will be downloaded from $TF_NUTRISCORE_URL"

        wget $TF_NUTRISCORE_URL -O $TF_NUTRISCORE_TARGZ_PATH
    fi

    echo "Saved model is downloaded. Uncompressing it."
    tar zxf $TF_NUTRISCORE_TARGZ_PATH -C $TF_NUTRISCORE_DIR_PATH

    echo "Deleting compressed model."
    rm $TF_NUTRISCORE_TARGZ_PATH
fi


if [ ! -d "$TF_NUTRISCORE_MODEL_PATH" ]; then
    echo "An error occurred: saved model should now be located at $TF_NUTRISCORE_MODEL_PATH but is not."
    exit 1
fi

echo "Nutriscore model is ready to be used !"
exit 0


