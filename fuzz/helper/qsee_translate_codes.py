#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import logging
import json

class QSEEErrno(object):
    EOK	        = 0
    EPERM		= 1
    ENOENT		= 2
    ESRCH		= 3
    EINTR		= 4
    EIO		    = 5
    ENXIO		= 6
    E2BIG		= 7
    ENOEXEC		= 8
    EBADF		= 9
    ECHILD		=10
    EAGAIN		=11
    ENOMEM		=12
    EACCES		=13
    EFAULT		=14
    ENOTBLK		=15
    EBUSY		=16
    EEXIST		=17
    EXDEV		=18
    ENODEV		=19
    ENOTDIR		=20
    EISDIR		=21
    EINVAL		=22
    ENFILE		=23
    EMFILE		=24
    ENOTTY		=25
    ETXTBSY		=26
    EFBIG		=27
    ENOSPC		=28
    ESPIPE		=29
    EROFS		=30
    EMLINK		=31
    EPIPE		=32
    EDOM		=33
    ERANGE		=34

    ESCM_ENOMEM	= 42 # ENOMEM
    ESCM_EOPNOTSUPP	 = 43 # SCM_EOPNOTSUP
    ESCM_EINVAL_ADDR	= 44 # EINVAL
    ESCM_EINVAL_ARG	= 45 # EINVAL
    ESCM_ERROR	= 46 # EIO
    ESCM_INTERRUPTED	= 47
    ESCM_EBUSY	= 48 # SCM_BUSY
    ESCM_V2_EBUSY	= 49 # SCM_V2_BUSY

QSEEErrno_dict = \
    {v: k for k,v in QSEEErrno.__dict__.iteritems()}

log = logging.getLogger(__file__)


def main(tzzzlog):
    with open(tzzzlog) as f:
        data = f.read()

    entries = data.split('\n')
    #import ipdb; ipdb.set_trace()

    positive_codes = [-int(entry.split(";")[1], 16) & 0xffffffff for entry in entries if entry]
    stats = dict()
    for code in positive_codes:
        if QSEEErrno_dict[code] not in stats:
            stats[QSEEErrno_dict[code]] = 0
        stats[QSEEErrno_dict[code]] += 1

    # do mapping to ioctl error codes
    if QSEEErrno_dict[QSEEErrno.ESCM_ENOMEM] in stats:
        count = stats[QSEEErrno_dict[QSEEErrno.ESCM_ENOMEM]]
        if QSEEErrno_dict[QSEEErrno.ENOMEM] not in stats:
            stats[QSEEErrno_dict[QSEEErrno.ENOMEM]] = 0
        stats[QSEEErrno_dict[QSEEErrno.ENOMEM]] += count

    if QSEEErrno_dict[QSEEErrno.ESCM_EINVAL_ADDR] in stats:
        count = stats[QSEEErrno_dict[QSEEErrno.ESCM_EINVAL_ADDR]]
        if QSEEErrno_dict[QSEEErrno.EINVAL] not in stats:
            stats[QSEEErrno_dict[QSEEErrno.EINVAL]] = 0
        stats[QSEEErrno_dict[QSEEErrno.EINVAL]] += count

    if QSEEErrno_dict[QSEEErrno.ESCM_EINVAL_ARG] in stats:
        count = stats[QSEEErrno_dict[QSEEErrno.ESCM_EINVAL_ARG]]
        if QSEEErrno_dict[QSEEErrno.EINVAL] not in stats:
            stats[QSEEErrno_dict[QSEEErrno.EINVAL]] = 0
        stats[QSEEErrno_dict[QSEEErrno.EINVAL]] += count

    if QSEEErrno_dict[QSEEErrno.ESCM_ERROR] in stats:
        count = stats[QSEEErrno_dict[QSEEErrno.ESCM_ERROR]]
        if QSEEErrno_dict[QSEEErrno.EIO] not in stats:
            stats[QSEEErrno_dict[QSEEErrno.EIO]] = 0
        stats[QSEEErrno_dict[QSEEErrno.EIO]] += count

    smc_invalid_count = 0
    for k in stats.keys():
        if k.startswith('ESCM'):
            smc_invalid_count += stats[k]

    ioctl_invalid_count = 0
    for k in stats.keys():
        if not k.startswith('ESCM') and "OK" not in k:
            ioctl_invalid_count += stats[k]

    smc_ioctl_valid_count = 0
    if QSEEErrno_dict[QSEEErrno.EOK] in stats:
        smc_ioctl_valid_count += stats[QSEEErrno_dict[QSEEErrno.EOK]]

    TOTAL_IOCTL_KEY = "#ioctl"
    INVALID_IOCTL_KEY = "#invalid_ioctl"
    VALID_IOCTL_KEY = "#valid_ioctl"

    TOTAL_SMC_KEY = "#smc"
    INVALID_SMC_KEY = "#invalid_smc"
    VALID_SMC_KEY = "#valid_smc"

    stats[TOTAL_IOCTL_KEY] = ioctl_invalid_count + smc_ioctl_valid_count
    stats[INVALID_IOCTL_KEY] = ioctl_invalid_count
    stats[VALID_IOCTL_KEY] = smc_ioctl_valid_count

    stats[TOTAL_SMC_KEY] = smc_ioctl_valid_count + smc_ioctl_valid_count
    stats[INVALID_SMC_KEY] = smc_invalid_count
    stats[VALID_SMC_KEY] = smc_ioctl_valid_count


    print(json.dumps(stats))
    return

def usage():
    print("{} <tzzz.log>".format(sys.argv[0]))
    return


if __name__=="__main__":

    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        usage()
        sys.exit(0)

    main(sys.argv[1])

