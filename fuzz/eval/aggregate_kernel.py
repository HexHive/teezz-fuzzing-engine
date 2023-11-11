#!/usr/bin/env python
from __future__ import print_function
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import logging
import json
import struct


from qsee import QSEE_CMDID_dict
from huawei.tc import TC_CMDID, TC_CMDID_dict, TC_CMDID_P20Lite, TC_CMDID_P20Lite_dict
from optee import OPTEE_CMDID_dict
from utils import p32, us32, u32

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)

TEEs = ['qsee', 'tc', 'tc-p20lite', 'optee']

IOCTL_TOTAL = 'ioctl_total'
IOCTL_ERROR = 'ioctl_error'
IOCTL_SUCCESS = 'ioctl_success'
SMC_TOTAL = 'smc_total'
SMC_VALID = 'smc_valid'

CMDID_dicts = {
    'qsee': QSEE_CMDID_dict,
    'tc': TC_CMDID_dict,
    'tc-p20lite': TC_CMDID_P20Lite_dict,
    'optee': OPTEE_CMDID_dict
}

"""
Format:
<time>;<cmd>;<ioctl_ret>;<status>;<origin>;<smc_flag>\n

Where time:
hh:mm:ss:ns

For QSEE:
origin = 
enum qseecom_qceos_cmd_status {
	QSEOS_RESULT_SUCCESS = 0,
	QSEOS_RESULT_INCOMPLETE,
	QSEOS_RESULT_FAILURE  = 0xFFFFFFFF
};

status = 
#define SCM_ENOMEM		-5
#define SCM_EOPNOTSUPP		-4
#define SCM_EINVAL_ADDR		-3
#define SCM_EINVAL_ARG		-2
#define SCM_ERROR		-1
#define SCM_INTERRUPTED		1
#define SCM_EBUSY		-55
#define SCM_V2_EBUSY		-12
"""


def main(tee, tzlog):

    stats = {IOCTL_TOTAL: 0, IOCTL_ERROR: 0, IOCTL_SUCCESS: 0, SMC_TOTAL: 0, SMC_VALID: 0}
    with open(tzlog) as f:
        for line in f:
            if '0:0:0:0;0x0;0x0;0x0;0x0;0x0' in line:
                continue
            split_line = line.split(';')
            if len(split_line) != 6:
                log.error("malformed line: {}".format(line))
                continue
            try:
                #time_ = split_line[0]
                cmd = u32(p32(int(split_line[1], 16)))
                ioctl_ret = int(split_line[2], 16)
                status_code = int(split_line[3], 16)
                origin = int(split_line[4], 16)
                smc_flag = int(split_line[5], 16)
            except ValueError:
                log.error("malformed line: {}".format(line))
                continue
            except struct.error:
                log.error("malformed line: {}".format(line))
                continue

            if cmd not in CMDID_dicts[tee]:
                # apparently, syzkaller mutates the cmdid sometimes (kinda rarely)
                # therefore, it is legit to find cmdids here that we do not know
                log.error("cmd id {} should be in here!".format(hex(cmd)))
                cmd_key = hex(cmd)
            else:
                cmd_key = CMDID_dicts[tee][cmd]

            if cmd_key not in stats:
                stats[cmd_key] = {IOCTL_TOTAL: 0, IOCTL_ERROR: 0, IOCTL_SUCCESS: 0, SMC_TOTAL: 0, SMC_VALID: 0}

            stats[IOCTL_TOTAL] += 1

            # if ioctl <0 it's an error
            signed_ret = us32(p32(ioctl_ret))
            if signed_ret < 0:
                stats[IOCTL_ERROR] += 1
                stats[cmd_key][IOCTL_TOTAL] += 1
                stats[cmd_key][IOCTL_ERROR] += 1
            else:
                stats[IOCTL_SUCCESS] += 1
                stats[cmd_key][IOCTL_TOTAL] += 1
                stats[cmd_key][IOCTL_SUCCESS] += 1

            if smc_flag:
                stats[SMC_TOTAL] += 1
                stats[cmd_key][SMC_TOTAL] += 1
                if tee == 'qsee' and origin == 0x0 and status_code == 0x0:
                    """ status should be QSEOS_RESULT_SUCCESS and origin 0 (non-error) """
                    stats[SMC_VALID] += 1
                    stats[cmd_key][SMC_VALID] += 1
                elif (tee == 'tc' or tee == 'tc-p20lite') and origin in [0x0, 0x3, 0x4] and not status_code in [0x1, 0x2, 0x3]:
                    """ valid smc if we hit TEE or TA """
                    stats[SMC_VALID] += 1
                    stats[cmd_key][SMC_VALID] += 1
                elif tee == 'optee' and origin in [0x0, 0x3, 0x4]:
                    """ valid smc if we hit TEE or TA """
                    stats[SMC_VALID] += 1
                    stats[cmd_key][SMC_VALID] += 1

    return stats


def usage():
    print("{} <tee> <tzlogger.log>".format(sys.argv[0]))
    return


if __name__ == "__main__":

    if len(sys.argv) < 3 or not os.path.exists(sys.argv[2]) or \
            sys.argv[1] not in TEEs:
        usage()
        sys.exit(0)

    print(json.dumps(main(sys.argv[1], sys.argv[2])))
