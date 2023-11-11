#!/usr/bin/env python
import sys
import os
import pickle
from utils import u32, find_files
import logging
import string
import hexdump

from StructDictClass import StructDict

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


def is_len_type_sequence(types, len, off):
    keys = types.keys()
    keys.sort()
    type_seq = []
    type_list = []

    prev_sz = None
    prev_k = 0
    for k in keys:
        if off > k:
            prev_k = k
            continue

        if prev_sz and prev_k + prev_sz != k:
            break

        if types[k][1] not in type_seq:
            type_seq.append(types[k][1])

        type_list.append(types[k][1])
        prev_sz = types[k][0]
        prev_k = k

    for t in type_seq:
        if type_list.count(t) != len:
            return False

    return True


def is_printable(s):
    for c in s:
        if c not in string.printable:
            return False
    return True


def process_param(param_path):
    param_types_path = "{}.types".format(param_path)

    # do we have the types?
    if os.path.exists(param_types_path):
        with open(param_types_path) as f:
            # restructure so that we cann access it by offset
            structDict = pickle.load(f)
            dataList = structDict.getAsList()
            types = {e[0][0]: (e[0][1], e[1]) for e in dataList}
    else:
        types = {}

    with open(param_path) as f:
        data = f.read()

    matches = []
    off = 0
    while off + 4 < len(data):
        # check if this member does not have a type itself yet
        if off not in types.keys():
            len_candidate = u32(data[off:off + 4])
            # check if this length describes a succeeding printable string (minimum 3 printable chars)
            if len(data[off + 4:]) >= len_candidate and len_candidate >= 3:
                s = data[off + 4:off + 4 + len_candidate]
                if is_printable(s):
                    matches.append(((off, 4), "size_t"))
                    log.info("{}@{} is len!".format(len_candidate, off + 4))

            # check if this length describes the rest length of this blob
            elif len(data[off + 4:]) == len_candidate:
                matches.append(((off, 4), "size_t"))
                log.info("{}@{} is len!".format(len_candidate, off + 4))

            # check if this length describes length of the entire blob
            elif len(data) == len_candidate:
                matches.append(((off, 4), "size_t"))
                log.info("{}@{} is len!".format(len_candidate, off + 4))

            # check if this length describes succeeding type sequence
            elif off + 4 in types.keys():
                if is_len_type_sequence(types, len_candidate, off + 4):
                    matches.append(((off, 4), "size_t"))
                    log.info("{}@{} is len!".format(len_candidate, off + 4))
        off += 4

    if matches:
        # if we have matches, save to existing types if exists
        if not os.path.exists(param_types_path):
            with open(param_types_path, "w") as f:
                structDict = StructDict(len(data), matches)
                pickle.dump(structDict, f)
        else:
            structDict = StructDict(len(data))
            with open(param_types_path, "r+w") as f:
                unpickled = pickle.load(f)
                structDict.addListOfTypes(unpickled.getAsList())
                structDict.addListOfTypes(matches)
            os.remove(param_types_path)
            with open(param_types_path, "w") as f:
                pickle.dump(structDict, f)


def main(tee, dir_):
    if tee == 'tc':
        param_paths = [
            path for path in find_files(dir_, ".*/param_.*")
            if path and "types" not in path
        ]
    elif tee == 'qsee':
        param_paths = [
            path for path in find_files(dir_, ".*/re*")
            if path and "types" not in path
        ]
    else:
        log.error("tee unknown {}".format(tee))
        sys.exit()

    for param_path in param_paths:
        log.info("processing: {}".format(param_path))
        process_param(param_path)


def usage():
    print("{} <tc|qsee> <dir>".format(sys.argv[0]))


if __name__ == "__main__":
    if len(sys.argv) < 3 or not os.path.isdir(sys.argv[2]):
        usage()
        sys.exit()
    else:
        main(sys.argv[1], sys.argv[2])
