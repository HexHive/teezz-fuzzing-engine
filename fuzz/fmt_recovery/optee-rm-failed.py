#!/usr/bin/env python
import sys
import os
import logging
import shutil
import glob

from fuzz.const import TEEID

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def get_seed_cls(target_tee):
    if target_tee == TEEID.OPTEE:
        from fuzz.optee.opteedata import TeeIoctlInvokeArg as cls
    elif target_tee == TEEID.TC:
        from fuzz.huawei.tc.tcdata import TC_NS_ClientContext as cls
    elif target_tee == TEEID.QSEE:
        raise NotImplementedError()
    else:
        log.error(f"Unknown TEE {target_tee}")
        import ipdb; ipdb.set_trace()
    return cls


def listdir_abs(dir_):
    return [os.path.join(dir_, d) for d in os.listdir(dir_)]


def main(dir_):
    invoke_arg_dirs = []
    for d in glob.glob(os.path.join(dir_, '*/*/onleave/tee_ioctl_invoke_arg')):
        invoke_arg_dirs.append(os.path.dirname(d))

    SeedCls = get_seed_cls("optee")
    for invoke_arg_dir in invoke_arg_dirs:
        invoke_arg = SeedCls.deserialize_raw_from_path(invoke_arg_dir)
        if invoke_arg.ret != 0:
            # delete the interaction
            shutil.rmtree(os.path.dirname(invoke_arg_dir))


def usage():
    print(f"Usage:\n\t{sys.argv[0]} <seed_base_dir>")


if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        usage()
    else:
        main(sys.argv[1])
