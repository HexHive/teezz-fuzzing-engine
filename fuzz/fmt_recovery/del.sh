#!/usr/bin/env bash

set -e

if [[ $# -ne 1 ]] ; then
    echo 'Call with <ioctl-folder>'
    exit 1
fi

IOCTL_ABS=$(realpath $1)

find $IOCTL_ABS -type f -name "*.types" -delete
find $IOCTL_ABS -type f -name "*.pickle" -delete
find $IOCTL_ABS -type f -name "*.stats" -delete
#find $IOCTL_ABS -type d -name "hal_*" -exec rm -rf {} \;
