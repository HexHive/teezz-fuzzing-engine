#!/usr/bin/env python
"""
hal and ioctl dump ids should correspond to each other.
sometimes there are situations where on the hal level we dump data and the software below does not trigger an ioctl.
this leads to a mismatch of hal and ioctl dump ids.
this script tries to resolve this mismatch.
"""
import sys
import os
import logging
from shutil import rmtree, move
import pickle
from utils import find_files, us32

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def del_erroneous_import_key(haldumps):
    """ on huawei, we dump hal data that never trigger an ioctl. we can see this from a negative ret val.
        this function simply deletes dumps that have a negative ret val.
    """
    for haldump in haldumps:
        if "import_key_" in haldump:
            try:
                with open(os.path.join(haldump, "onleave", "ret")) as f:
                    data = pickle.load(f)
                if data[0][0] != 'keymaster_error_t':
                    log.error(
                        "ret should be of type keymaster_error_t, but it is {}"
                        .format(data[0][0]))
                    import ipdb
                    ipdb.set_trace()
                retval = us32(data[0][1])
                if retval < 0:
                    log.debug("deleting {}".format(haldump))
                    rmtree(haldump)

            except Exception as e:
                log.error(e)
                import ipdb
                ipdb.set_trace()


def fix_dumpids(haldumps):
    """ deleting dumps results in dump id gaps. we just shift dump ids down for each deleted item """
    haldumps.sort(key=lambda dump: int(dump.split("_")[-1]))
    for i, dump in enumerate(haldumps):
        dump_id = int(dump.split("_")[-1])
        if dump_id != i:
            log.debug("dump {} should have dump id {}".format(dump, i))
            src_dir = dump
            dst_dir = "{}_{}".format("_".join(dump.split("_")[:-1]), i)
            log.debug("mv {} to {}".format(src_dir, dst_dir))
            move(src_dir, dst_dir)


def main(ioctldump_dir, haldump_dir):
    paths = find_files(ioctldump_dir, ".*/TC_NS_ClientContext")
    if not paths:
        log.error("no files found.")
        return
    paths = [path for path in paths if "onenter" in path]

    haldumps = [os.path.join(haldump_dir, d) for d in os.listdir(haldump_dir)]

    if len(paths) != len(haldumps):
        log.debug(
            "dumpids do not match ({} ioctl dumps vs {} hal dumps)".format(
                len(paths), len(haldumps)))
        del_erroneous_import_key(haldumps)

    # we deleted dumps before, so we get a new listing
    haldumps = [os.path.join(haldump_dir, d) for d in os.listdir(haldump_dir)]
    fix_dumpids(haldumps)

    haldumps = [os.path.join(haldump_dir, d) for d in os.listdir(haldump_dir)]
    paths = find_files(ioctldump_dir, ".*/TC_NS_ClientContext")
    paths = [path for path in paths if "onenter" in path]
    if len(paths) != len(haldumps):
        log.error(
            "dumpids still do not match ({} ioctl dumps vs {} hal dumps)".
            format(len(paths), len(haldumps)))
    else:
        log.info("Good to go!")

    return


def usage():
    print("Usage:\n\t{} <ioctldump_dir> <haldump_dir>".format(sys.argv[0]))


if __name__ == "__main__":
    if len(sys.argv) < 3 or not os.path.isdir(
            sys.argv[1]) or not os.path.isdir(sys.argv[2]):
        usage()
    else:
        main(sys.argv[1], sys.argv[2])
