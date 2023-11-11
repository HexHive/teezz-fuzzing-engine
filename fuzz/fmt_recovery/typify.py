import sys
import os
import logging
import pickle
from fuzz.seed.seedtemplate import SeedTemplate
from fuzz.utils import find_files


logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def typify(tee: str, ioctldump_dir: str):
    if tee == "qsee":
        # shouldn't match on 'ret' files
        paths = find_files(ioctldump_dir, ".*/\(resp\|req\)")
        shared = find_files(ioctldump_dir, ".*/shared")
        if shared:
            paths.extend(shared)
    elif tee == "tc":
        paths = find_files(ioctldump_dir, ".*/param_.*")
    elif tee == "optee":
        paths = find_files(ioctldump_dir, ".*/param_.*")
    else:
        log.error("Unknown tee {}".format(tee))
        sys.exit()

    if not paths:
        log.error("no files found.")
        return

    # create .types file for every ioctl dump
    for path in paths:
        with open("{}.types".format(path.decode()), "wb") as f:
            pickle.dump(SeedTemplate(os.path.getsize(path)), f)


def usage():
    print("Usage:\n\t{} <tc|qsee|optee> <ioctldump_dir>".format(sys.argv[0]))


if __name__ == "__main__":
    if len(sys.argv) < 3 or not os.path.isdir(sys.argv[2]):
        usage()
    else:
        typify(sys.argv[1], sys.argv[2])
