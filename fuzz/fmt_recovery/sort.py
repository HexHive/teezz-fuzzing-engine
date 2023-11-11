#!/usr/bin/env python3
""" Copies a directory of HAL-dumps to its 'corresponding' ioctl-dump directory.

What is a 'correspondence'?
In the beginning, our understanding of this was: if a request passes the HAL and later the ioctl interface,
this HAL-dump corresponds to the ioctl.
The primary goal of having HAL-dumps assigned to ioctl dumps at all, is type recovery.
It does not matter if we precisely assign the HAL-dump to the ioctl later called as long as we can get the maximal
available type information for the ioctl dump from the HAL-dump assigned to it.
Consequently, one HAL-dump can even be assigned to multiple ioctl dumps.

Right now, we take number of matching bytes as a heuristic to calculate a "correspondence value".
This number should give us the best HAL-dump/ioctl-dump assignment in regard to maximal type recovery for the ioctl.
"""
import sys
import os
import logging
import pickle
import binascii
import shutil
from fuzz.utils import find_files

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def corresponds(ioctldump, haldump, tee):
    """ Returns a correspondence value >= 0 depending on common data """
    correspondence_value = 0

    # Get relevant file names
    ioctl_params = None
    if tee == 'tc':
        ioctl_params = find_files(ioctldump, ".*/param_.?_[a-z]")
    elif tee == 'qsee':
        ioctl_params = find_files(ioctldump, ".*/\(resp\|req\)")
        ioctl_params_shared = find_files(ioctldump, ".*/shared")
        if ioctl_params_shared:
            ioctl_params.extend(ioctl_params_shared)
    elif tee == 'optee':
        ioctl_params = find_files(ioctldump, ".*/param_.?_[a-z]")
        ioctl_params += find_files(ioctldump, ".*/param_.?_data")

    if not ioctl_params:
        return 0
    hal_params = find_files(haldump, "*")
    if not hal_params:
        return 0

    ioctl_blob = ""

    for ioctl_param in ioctl_params:
        if b".types" in ioctl_param:
            continue
        # TODO quick fix for QSEE -> what about TC?
        if b"onenter" in ioctl_param and b"resp" in ioctl_param:
            continue
        if b"onleave" in ioctl_param and b"req" in ioctl_param:
            continue
        with open(ioctl_param, "rb") as f:
            ioctl_blob += binascii.hexlify(f.read()).decode()

    for hal_param in hal_params:
        # Only compare return value TODO: Do we really want this?
        #if os.path.basename(hal_param) != "ret":
        #    continue

        with open(hal_param, "rb") as f:
            hal_param_buffer = pickle.load(f)

        for p in hal_param_buffer:
            if not p[1]:
                continue

            param = binascii.hexlify(p[1]).decode()

            # TODO don't use one blob! -> change to list of params
            # TODO TC FP breaks because 4 Bytes in handle are changed
            if param in ioctl_blob:
                # using the number of unique bytes and ignore zero
                bytearr = bytearray.fromhex(param)
                unique = set(bytearr)
                if not (len(unique) == 1 and unique.pop() == '\x00'):
                    correspondence_value += len(unique)

            # no correspondence with complete parameter matching found
            # check for chunks -> needed for TC FP (token bytesequence was mixed)
            if (correspondence_value == 0 and tee == "tc"):
                param_chunks = [
                    param[start:start + 4]
                    for start in range(0, len(param), 8)
                ]
                for param_chunk in param_chunks:
                    empty = 0
                    for x in param_chunk:
                        if x != '0':
                            empty += 1
                            if empty > 2:
                                break
                    if empty <= 2:
                        continue

                    if param_chunk in ioctl_blob:
                        #print(param_chunk)
                        correspondence_value += len(param_chunk) / 2

    if correspondence_value != 0:
        pass
        #log.debug("{} {}".format(correspondence_value, haldump))

    return correspondence_value


def get_hal_index(path):
    """ returns the index/id of the provided HAL-dump path. """
    return int(path.split('_')[-1])


def get_ioctl_index(path):
    """ returns the index/id of the provided ioctl-dump path. """
    return int(os.path.basename(path))


def rearrange(haldumps):
    """ Rearranges `haldumps` in the way we need it for following stages.

    Android's CPP HAL uses callbacks for return parameters.
    In the following dump, we generated a key. The params for this key are
    passed to the `generateKey` HAL function and the function internally calls
    a callback function `generateKey__hidl_cb` to return the `keyBlob` and the
    `keyCharacteristics`. Our preprocessing expects outgoing params to be found
    in `onleave` folders. Hence, we rearrange the folders so that the callback's
    `onenter` is the regular call's `onleave`.
    .
    ├── generateKey_2
    │   ├── onenter
    │   │   └── keyParams
    │   └── onleave
    │       └── keyParams
    ├── generateKey__hidl_cb_3
    │   ├── onenter
    │   │   ├── error
    │   │   ├── keyBlob
    │   │   └── keyCharacteristics
    │   └── onleave

    """
    for idx in range(len(haldumps)):
        curr_name = os.path.basename(haldumps[idx])
        if "hidl_cb" in curr_name:
            # this is a callback folder
            hal_name = curr_name.split("__")[0]
            caller_name = os.path.basename(haldumps[idx - 1])
            if hal_name in caller_name:
                # this is the matching caller
                caller_onleave = os.path.join(haldumps[idx - 1], "onleave")
                shutil.rmtree(caller_onleave)
                cb_onenter = os.path.join(haldumps[idx], "onenter")
                shutil.move(cb_onenter, caller_onleave)
                shutil.rmtree(haldumps[idx])
    # filter for folders that still exist
    return [haldump for haldump in haldumps if os.path.isdir(haldump)]


def sort(tee, ioctldumps, haldumps):
    """Matches the haldumps to the ioctldumps.

    Searches for the biggest correspondence between all given ioctl-
    and haldumps and copies the haldump data to the corresponding
    ioctldump directory.

    Args:
        tee: 'tc' or 'qsee'
        ioctldumps: paths to the numbered ioctldump folders
        haldumps: paths to the named haldump dirs
    """
    haldumps = sorted(haldumps, key=get_hal_index)
    ioctldumps = sorted(ioctldumps, key=get_ioctl_index)

    haldumps = rearrange(haldumps)
    for ioctldump in ioctldumps:
        best_corr = 0
        best_haldump = -1

        for haldump in haldumps:
            tmp_corr = 0
            for event in ["onenter", "onleave"]:
                tmp_corr += corresponds(os.path.join(ioctldump, event),
                                        os.path.join(haldump, event), tee)
                log.debug("{}: {}".format(event, tmp_corr))

            log.debug("Correspondends with \"{}\" is {}".format(
                os.path.basename(haldump), tmp_corr))

            if tmp_corr > best_corr:
                best_haldump = haldump
                best_corr = tmp_corr

        if best_haldump == -1:
            log.info("No corresponding HAL-dump found for ioctldump {}".format(
                ioctldump))
            continue

        log.debug("Using \"{}\" for \"{}\" with {}".format(
            os.path.basename(ioctldump), os.path.basename(best_haldump),
            best_corr))

        log.debug("{} --> {}".format(
            os.path.join(
                os.path.join(os.path.dirname(os.path.dirname(best_haldump)),
                             "onleave"),
                "hal_" + os.path.basename(best_haldump)),
            os.path.join(ioctldump, "onleave")))
        shutil.copytree(
            os.path.join(best_haldump, "onleave"),
            os.path.join(os.path.join(ioctldump, "onleave"),
                         "hal_" + os.path.basename(best_haldump)))

        log.debug("{} --> {}".format(
            os.path.join(ioctldump, "onenter"),
            os.path.join(
                os.path.join(os.path.dirname(os.path.dirname(best_haldump)),
                             "onenter"),
                "hal_" + os.path.basename(best_haldump))))

        shutil.copytree(
            os.path.join(best_haldump, "onenter"),
            os.path.join(os.path.join(ioctldump, "onenter"),
                         "hal_" + os.path.basename(best_haldump)))


def main(tee, ioctldump_dir, haldump_dir):
    # get all directories containing dumps from the HAL-layer
    haldumps = [os.path.join(haldump_dir, d) for d in os.listdir(haldump_dir)]
    # get all directories containing ioctldumps
    # -> search in all sequence directories
    ioctldump_sequences = [os.path.join(ioctldump_dir, d) for d \
            in os.listdir(ioctldump_dir)]

    ioctldumps = []
    for f in ioctldump_sequences:
        ioctldumps.extend([os.path.join(f, d) for d in os.listdir(f)])

    sort(tee, ioctldumps, haldumps)


def usage():
    log.error("Usage:\n\t{} <tc|qsee> <ioctldump_dir> <haldump_dir>".format(
        sys.argv[0]))


if __name__ == "__main__":
    if (len(sys.argv) != 4 or not os.path.isdir(sys.argv[2])
            or not os.path.isdir(sys.argv[3])):
        usage()
    else:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
