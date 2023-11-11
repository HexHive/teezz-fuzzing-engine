#!/usr/bin/env bash

################################################################################
# GLOBALS & ENV
################################################################################

TEE=${TEE}
CONFIG=${CONFIG}
DEVICE_ID=${DEVICE_ID}

IN_DIR=/seeds-dirty
CLEANED_DIR=/teezz-in
TMP_DIR=`mktemp -d`

set -eu

################################################################################
# ENTRYPOINT LOGIC
################################################################################

source /root/.venv/bin/activate
make -C /src probe-valdep-adb TEE=${TEE} DEVICE_ID=${DEVICE_ID} \
        CONFIG=${CONFIG} IN=$IN_DIR OUT=$CLEANED_DIR
