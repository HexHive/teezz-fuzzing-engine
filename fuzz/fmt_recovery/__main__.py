import sys
import os
import logging

from fuzz.fmt_recovery import typify
from fuzz.fmt_recovery import match
from fuzz.fmt_recovery import common_sequence
from fuzz.fmt_recovery import sz_off
from fuzz.fmt_recovery import find_value_deps

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

STAGE_BANNER = """
################################################################################

{}

################################################################################
"""


def main(tee, ioctl_seq_dir, hal_dir):
    print(STAGE_BANNER.format("TYPIFY"))
    for ioctl_dir in os.listdir(ioctl_seq_dir):
        ioctl_dir = os.path.join(ioctl_seq_dir, ioctl_dir)
        typify.typify(tee, ioctl_dir)

    # sort.main(tee, ioctl_seq_dir, hal_dir)
    # print(STAGE_BANNER.format("MATCH"))
    match.main(tee, ioctl_seq_dir)

    for ioctl_dir in os.listdir(ioctl_seq_dir):
        ioctl_dir = os.path.join(ioctl_seq_dir, ioctl_dir)
        print(STAGE_BANNER.format("COMMON_SEQ"))
        common_sequence.common_sequence(tee, ioctl_dir)

        print(STAGE_BANNER.format("SZ_OFF"))
        sz_off.sz_off(tee, ioctl_dir)

        print(STAGE_BANNER.format("VAL_DEPS"))
        find_value_deps.find_value_deps(tee, ioctl_dir)


def usage():
    print(f"{sys.argv[0]} <teec> <ioctl-dir> <hal-dir>")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        usage()
        sys.exit()
    tee = sys.argv[1]
    ioctl_seq_dir = sys.argv[2]
    hal_dir = sys.argv[3]
    main(tee, ioctl_seq_dir, hal_dir)
