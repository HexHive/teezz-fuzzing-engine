#!/bin/bash

set -e

if [[ $# -ne 3 ]] ; then
    echo 'Call with <Tee> <ioctl-folder> <hal-folder>'
    exit 1
fi

# get absolute pathes from relative ones
IOCTL_ABS=$(realpath $2)
HAL_ABS=$(realpath $3)

# change workingdir to tzzz_fuzzer dir
cd "../.."

function call {
    echo -e "\e[1;32m running $1 script! \e[0m"
    time python -m fuzz.fmt_recovery.$1 $2 $3 $4
}

call typify $1 $IOCTL_ABS
#call sort $1 $IOCTL_ABS $HAL_ABS
call match $1 $IOCTL_ABS
call common_sequence $1 $IOCTL_ABS
call sz_off $1 $IOCTL_ABS
call find_value_deps $1 $IOCTL_ABS
call gen_deps $IOCTL_ABS
