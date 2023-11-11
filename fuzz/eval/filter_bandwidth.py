#!/usr/bin/env python
from __future__ import print_function
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import logging
import struct

from qsee import QSEE_ReturnCodes, QSEE_ReturnCodes_dict

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)

"""
Format:
<ioctl_ret>;<smc_return_code>;<smc_origin>;<smc_called_flag>\n

Notes:
* smc_origin not used for QSEE
* init value for smc_return_code is 0xdeadbeef
* init value for smc_origin is 0xcafebabe (but not used here)
"""


def main(tzzz_log, out_log):

    PATTERN = '0x0;0xdeadbeef;0xcafebabe;0x0'
    with open(tzzz_log) as f, open(out_log, "w") as out_f:

        idx = 0
        l1 = f.readline()
        l2 = f.readline()
        l3 = f.readline()
        while l3:

            if PATTERN in l1 and PATTERN not in l2 and PATTERN in l3:
                out_f.write(l2)
                l1 = f.readline()
                l2 = f.readline()
                l3 = f.readline()
            else:
                out_f.write(l1)
                l1 = l2
                l2 = l3
                l3 = f.readline()
                idx += 1
    return


def usage():
    print("{} <tzzz_log> <out_log>".format(sys.argv[0]))
    return


if __name__=="__main__":

    if len(sys.argv) < 3 or not os.path.exists(sys.argv[1]):
        usage()
        sys.exit(0)

    main(sys.argv[1], sys.argv[2])
