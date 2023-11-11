#!/usr/bin/env bash

################################################################################
# GLOBALS & ENV
################################################################################

MODE=${MODE}
DURATION=${DURATION}
IN_DIR=/teezz-in
OUT_DIR=/teezz-out
PORT=${PORT}
TEE=${TEE}
CONFIG=${CONFIG}
DEVICE_ID=${DEVICE_ID}

set -eu

################################################################################
# ENTRYPOINT LOGIC
################################################################################

source /root/.venv/bin/activate
make -C /src fuzz-adb MODE=$MODE DURATION=$DURATION IN=$IN_DIR OUT=$OUT_DIR \
	PORT=$PORT TEE=$TEE CONFIG=$CONFIG DEVICE_ID=$DEVICE_ID
