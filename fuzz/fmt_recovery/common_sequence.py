"""
Script to find common sequences originating from responses consumed by requests.
"""
import sys
import logging
import pickle
import os
import string
from difflib import SequenceMatcher
from collections import OrderedDict
from multiprocessing import Pool
from fuzz.utils import find_files
from fuzz.seed.seedtemplate import SeedTemplate, SeedTemplateElement

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

alphabet = list(string.ascii_letters + string.digits)


def is_junk_sequence(x):
    """treat these sequences as junk
    * seqs smaller than 4 bytes
    * seqs only containing \x00
    """

    if (
        len(x) < 4
        or set(x).pop() == b"\x00"
        or len(set(x)) < 3
        or (len(x) not in [4, 8] and len(x) < 8)
    ):
        return True
    return False


def find_padding(buf: bytes, padding: bytes = b"\x00"):
    """Return start idx of padding bytes and -1 if there is no padding."""

    assert len(padding) == 1, "`padding` length needs to be 1"

    idx = 0
    while True:
        idx = buf.find(padding, idx)
        if idx == -1:
            # no padding
            break

        # check if remaining bytes are padding too
        s = set(buf[idx:])
        if len(s) == 1 and s.pop() == ord(padding):
            break

        idx += 1  # not a padding byte, advance
    return idx


def get_matches(req, req_path, resp, resp_path):
    match_list = []
    s = SequenceMatcher(lambda x: x == b"\x00", resp, req, autojunk=False)
    for match in s.get_matching_blocks():
        if match.size == 0 or is_junk_sequence(resp[match.a : (match.a + match.size)]):
            continue
        match_list.append((resp_path, match.a, req_path, match.b, match.size))
    return match_list


def common_sequence(tee, ioctldir):
    if tee == "qsee":
        # re* for req and resp
        ioctl_param_dumps = [
            dump
            for dump in find_files(ioctldir, ".*/\(resp\|req\)")
            if not dump.endswith(b".types")
        ]
        shared_bufs = find_files(ioctldir, ".*/shared")
        if shared_bufs:
            ioctl_param_dumps.extend(
                [dump for dump in shared_bufs if not dump.endswith(b".types")]
            )
    elif tee == "tc":
        ioctl_param_dumps = [
            dump
            for dump in find_files(ioctldir, ".*/param_.*")
            if not dump.endswith(b".types")
        ]
    elif tee == "optee":
        ioctl_param_dumps = [
            dump
            for dump in find_files(ioctldir, ".*/param_.*")
            if not dump.endswith(b".types")
        ]
    else:
        log.error("tee {} unknown.".format(tee))
        sys.exit(0)

    if not ioctl_param_dumps:
        log.error("no ioctl param dumps.")
        return

    # get requests and responses
    # TODO: since we dump the requests in onleave too, all reqs are part of
    #       responses. Get back to this here if it turns out to be a problem.
    ioctl_req_params = [req.decode() for req in ioctl_param_dumps if b"onenter" in req]
    ioctl_resp_params = [
        resp.decode() for resp in ioctl_param_dumps if b"onleave" in resp
    ]

    resps_by_id = OrderedDict()
    for resp_path in ioctl_resp_params:
        id_ = int(os.path.basename(os.path.dirname(os.path.dirname(resp_path))))
        if id_ not in resps_by_id:
            resps_by_id[id_] = []
        resps_by_id[id_].append(resp_path)

    reqs_by_id = OrderedDict()
    for req_path in ioctl_req_params:
        id_ = int(os.path.basename(os.path.dirname(os.path.dirname(req_path))))
        if id_ not in reqs_by_id:
            reqs_by_id[id_] = []
        reqs_by_id[id_].append(req_path)

    match_results = []
    resp_ids = list(resps_by_id.keys())
    resp_ids.sort()
    req_ids = list(reqs_by_id.keys())
    req_ids.sort()
    matches = []

    resps_blob_by_path = {}
    reqs_blob_by_path = {}
    for resp_id in resp_ids:
        pool = Pool(processes=os.cpu_count() * 2)
        log.info(resp_id)
        for req_id in req_ids:
            if req_id <= resp_id:
                continue

            for resp_path in resps_by_id[resp_id]:
                if resp_path not in resps_blob_by_path:
                    with open(resp_path, "rb") as f:
                        resp = f.read()
                        padding_idx = find_padding(resp)
                        resp = resp[:padding_idx]
                    resps_blob_by_path[resp_path] = resp
                else:
                    resp = resps_blob_by_path[resp_path]

                for req_path in reqs_by_id[req_id]:
                    log.info(f"{resp_path} --?> {req_path}")
                    if req_path not in reqs_blob_by_path:
                        with open(req_path, "rb") as f:
                            req = f.read()
                        reqs_blob_by_path[req_path] = req
                    else:
                        req = reqs_blob_by_path[req_path]

                    result = pool.apply_async(
                        get_matches, (req, req_path, resp, resp_path)
                    )
                    match_results.append(result)
                    del req
                del resp

        for result in match_results:
            res = result.get()
            if res != []:
                matches.extend(res)

        pool.close()
        pool.join()
        match_results = []

    for match in matches:
        log.info(match)
        resp_path, resp_begin, req_path, req_begin, size = match
        req_type_name = "uint8_t*"  # the default type is "uint8_t*"
        resp_type_name = "uint8_t*"

        with open("{}.types".format(resp_path), "rb") as f:
            resp_tmpl: SeedTemplate = pickle.load(f)

        if resp_begin >= resp_tmpl._size or resp_begin + size >= resp_tmpl._size:
            import ipdb

            ipdb.set_trace()

        resp_tmpl_elem = SeedTemplateElement(
            resp_begin, resp_begin + size, resp_type_name
        )

        try:
            resp_tmpl.add_elem(resp_tmpl_elem)
        except ValueError as e:
            log.warning(e)

        with open("{}.types".format(resp_path), "wb") as f:
            pickle.dump(resp_tmpl, f)

        with open("{}.types".format(req_path), "rb") as f:
            req_tmpl: SeedTemplate = pickle.load(f)

        if req_begin >= req_tmpl._size or req_begin + size > req_tmpl._size:
            import ipdb

            ipdb.set_trace()

        req_tmpl_elem = SeedTemplateElement(req_begin, req_begin + size, req_type_name)
        try:
            req_tmpl.add_elem(req_tmpl_elem)
        except ValueError as e:
            log.warning(e)
            continue

        with open("{}.types".format(req_path), "wb") as f:
            pickle.dump(req_tmpl, f)


def usage():
    print("Usage:\n\t{} <tc|qsee|optee> <dump_dir>".format(sys.argv[0]))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and os.path.isdir(sys.argv[2]):
        common_sequence(sys.argv[1], sys.argv[2])
    else:
        usage()
