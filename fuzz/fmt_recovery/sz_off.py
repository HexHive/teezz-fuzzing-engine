#!/usr/bin/env python3
import sys
import os
import pickle
import logging
import string
import hexdump
from fuzz.utils import u32, find_files
from fuzz.seed.seedtemplate import SeedTemplate, SeedTemplateElement

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


# Finds Arrays of Data of 'len' size
def is_len_type_sequence(types, len, off):
    keys = list(types.keys())
    keys.sort()
    type_seq = []
    type_list = []

    prev_sz = None
    prev_k = 0

    for k in keys:
        if off > k:
            prev_k = k
            continue

        if prev_sz and k != prev_k + prev_sz:
            name = "undef_{}".format(k - (prev_k + prev_sz))
            if name not in type_seq:
                type_seq.append(name)
            type_list.append(name)
            # break

        if types[k][1] not in type_seq:
            type_seq.append(types[k][1])

        type_list.append(types[k][1])
        prev_sz = types[k][0]
        prev_k = k

    for t in type_seq:
        if type_list.count(t) == len:
            return True

    return False


def is_printable(s):
    for c in s:
        if str(c) not in string.printable:
            return False
    return True


def process_param(param_path):
    param_types_path = "{}.types".format(param_path.decode())

    # do we have the types?
    if os.path.exists(param_types_path):
        with open(param_types_path, "rb") as f:
            # restructure so that we cann access it by offset
            seed_template: SeedTemplate = pickle.load(f)
            seed_tmpl_elems: List[SeedTemplateElement] = seed_template.listify()
            # structure: (offset, (size, type))
            types = {e.start: (e.size, e.type) for e in seed_tmpl_elems}
    else:
        types = {}

    with open(param_path, "rb") as f:
        data = f.read()

    # find offset and corresponding length information
    len_matches: List[SeedTemplateElement] = []
    off_matches: List[SeedTemplateElement] = []
    off = 0
    while off + 4 < len(data):
        # check if this member does not have a type itself yet
        if off not in types.keys():
            off_candidate = u32(data[off : off + 4])

            if off_candidate > 0 and len(data) >= off_candidate:
                # check if data with this offset exists
                if off_candidate in types.keys() and off_candidate > off:
                    off_matches.append(SeedTemplateElement(off, off + 4, "off_t"))
                    log.info("{:#x}@{:#x} is offset!".format(off_candidate, off))
                    # check previous and next 4 Bytes for length information
                    if off >= 4:
                        len_candidate = u32(data[off - 4 : off])
                        length, _ = types[off_candidate]
                        if len_candidate == length:
                            len_matches.append(
                                SeedTemplateElement(off - 4, off, "size_t")
                            )
                    if (off + 8) <= len(data):
                        len_candidate = u32(data[off + 4 : off + 8])
                        length, _ = types[off_candidate]
                        if len_candidate == length:
                            len_matches.append(
                                SeedTemplateElement(off + 4, off + 8, "size_t")
                            )
        off += 4

    # find additional length information
    off = 0
    while off + 4 < len(data):
        # check if this member does not have a type itself yet
        if off not in types.keys():
            len_candidate = u32(data[off : off + 4])
            # check if this length describes a succeeding
            # printable string (minimum 3 printable chars)
            if len(data[off + 4 :]) >= len_candidate and len_candidate >= 3:
                s = data[off + 4 : off + 4 + len_candidate]
                if is_printable(s):
                    len_matches.append(SeedTemplateElement(off, off + 4, "size_t"))
                    log.info("{}@{} is len!".format(len_candidate, off + 4))

            # check if this length describes the rest length of this blob
            elif len(data[off + 4 :]) == len_candidate:
                len_matches.append(SeedTemplateElement(off, off + 4, "size_t"))
                log.info("{}@{} is len!".format(len_candidate, off + 4))

            # check if this length describes length of the entire blob
            elif len(data) == len_candidate:
                len_matches.append(SeedTemplateElement(off, off + 4, "size_t"))
                log.info("{}@{} is len!".format(len_candidate, off + 4))

            # check if this length describes succeeding type sequence
            elif off + 4 in types.keys():
                if is_len_type_sequence(types, len_candidate, off + 4):
                    len_matches.append(SeedTemplateElement(off, off + 4, "size_t"))
                    log.info("{}@{} is len!".format(len_candidate, off + 4))
        off += 4

    matches: List[SeedTemplateElement] = []
    matches.extend(len_matches)
    matches.extend(off_matches)

    for new_elem in matches:
        print(new_elem)

    if matches:
        # if we have matches, save to existing types if exists
        if not os.path.exists(param_types_path):
            with open(param_types_path, "wb") as f:
                seed_template = SeedTemplate(len(data), matches)
                pickle.dump(seed_template, f)
        else:
            for new_elem in matches:
                print(new_elem)
                with open(param_types_path, "rb") as f:
                    seed_template: SeedTemplate = pickle.load(f)

                try:
                    seed_template.add_elem(new_elem)
                except ValueError as e:
                    log.warning(e)
                    continue

                with open(param_types_path, "wb") as f:
                    pickle.dump(seed_template, f)


def sz_off(tee: str, dir_: str):
    if tee == "tc":
        param_paths = [
            path
            for path in find_files(dir_, ".*/param_.*")
            if path and b"types" not in path
        ]
    elif tee == "qsee":
        param_paths = [
            path
            for path in find_files(dir_, ".*/\(resp\|req\)")
            if path and b"types" not in path
        ]

        shared_bufs = find_files(dir_, "shared")
        if shared_bufs:
            param_paths.extend(
                [path for path in shared_bufs if path and b"types" not in path]
            )
    elif tee == "optee":
        param_paths = [
            path
            for path in find_files(dir_, ".*/param_.*")
            if path and b"types" not in path
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
        sz_off(sys.argv[1], sys.argv[2])
