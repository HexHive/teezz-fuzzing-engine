from __future__ import annotations
import sys
import os
import logging
import pickle
import glob
import shutil

from dataclasses import dataclass
from pprint import pprint
from fuzz.utils import find_dirs
from fuzz.huawei.tc.tcdata import TC_NS_ClientContext, TC_NS_ClientParam
from fuzz.huawei.tc import tc
from fuzz.optee.opteedata import TeeIoctlInvokeArg, TeeIoctlParam
from fuzz.seed.seedtemplate import SeedTemplate, SeedTemplateElement
from fuzz.apidependency import IoctlCallSequence, IoctlCall, ValueDependency

from typing import List

################################################################################
# LOGGING
################################################################################

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

################################################################################
# LOGGING
################################################################################

MATCHING_WINDOW = 16

CALL_DEPENDENCIES = "dep_chains.pickle"

EXCLUDED_TYPES = [
    "keymaster_error_t",
    "keymaster_tag_t",
    "keymaster_key_format_t",
    "keymaster_key_param_t::(anonymous union at ./aosp/libhardware/include/hardware/keymaster_defs.h:315:5)",
]

SPECIAL_DEP_IDX = 0
SPECIAL_DEP_BASE = 0xDEAD0000

DEPENDENCY_FILE = "dependencies.pickle"

SPECIAL_DEP_BASE = 0xDEAD0000

################################################################################
# CODE
################################################################################


@dataclass
class Match:
    resp_nr: int
    resp_name: str
    resp_tmpl_elem: SeedTemplateElement
    resp_func_name: str

    req_nr: int
    req_name: str
    req_tmpl_elem: SeedTemplateElement
    req_func_name: str

    def req_collides(self, match: Match) -> bool:
        return self.req_tmpl_elem.is_collision(match.req_tmpl_elem)


def is_relevant_file_tc(param_path):
    ctx = TC_NS_ClientContext.deserialize_raw_from_path(os.path.dirname(param_path))

    param = os.path.basename(param_path)
    i = int(param.split("_")[1])

    param_type = tc.get_param_type(i, ctx.param_types)
    if "onleave" in param_path:
        if (
            param_type in TC_NS_ClientParam.MEMREF_OUTPUT_TYPES
            or param_type in TC_NS_ClientParam.VALUE_OUTPUT_TYPES
        ):
            return True
    if "onenter" in param_path:
        if (
            param_type in TC_NS_ClientParam.MEMREF_INPUT_TYPES
            or param_type in TC_NS_ClientParam.VALUE_INPUT_TYPES
        ):
            return True

    return False


def is_relevant_file_optee(param_dir):
    invoke_arg_path = os.path.join(os.path.dirname(param_dir), "tee_ioctl_invoke_arg")

    invoke = TeeIoctlInvokeArg.deserialize_raw_from_path(invoke_arg_path)

    param = os.path.basename(param_dir)
    i = int(param.split("_")[1])

    param_type = invoke.params[i].attr
    if "onleave" in param_dir:
        if (
            param_type in TeeIoctlParam.MEMREF_OUTPUT_TYPES
            or param_type in TeeIoctlParam.VALUE_OUTPUT_TYPES
        ):
            return True
    if "onenter" in param_dir:
        if (
            param_type in TeeIoctlParam.MEMREF_INPUT_TYPES
            or param_type in TeeIoctlParam.VALUE_INPUT_TYPES
        ):
            return True

    return False


def match_parameter(resp_path: str, req_path: str) -> List[Match]:
    resp_nr = int(os.path.basename(os.path.dirname(os.path.dirname(resp_path))))
    req_nr = int(os.path.basename(os.path.dirname(os.path.dirname(req_path))))

    # open the *.type file for the response
    with open("{}.types".format(resp_path), "rb") as f:
        resp_tmpl: SeedTemplate = pickle.load(f)
        resp_types = resp_tmpl.listify()

    # open the *.type file for the request
    with open("{}.types".format(req_path), "rb") as f:
        req_tmpl: SeedTemplate = pickle.load(f)
        req_types = req_tmpl.listify()

    # open the response itself
    with open(resp_path, "rb") as f:
        resp = f.read()

    # open the request itself
    with open(req_path, "rb") as f:
        req = f.read()

    resp_func = "UNKNOWN"
    req_func = "UNKNOWN"

    # try to find the corresponding hal function name for the response
    found_dirs = find_dirs(os.path.dirname(resp_path), "hal_*")
    if found_dirs:
        resp_func = os.path.basename(found_dirs[0])
        resp_func = resp_func[resp_func.find(b"_") + 1 : resp_func.rfind(b"_")]

    # try to find the corresponding hal function name for the request
    found_dirs = find_dirs(os.path.dirname(req_path), "hal_*")
    if found_dirs:
        req_func = os.path.basename(found_dirs[0])
        req_func = req_func[req_func.find(b"_") + 1 : req_func.rfind(b"_")]

    # lists for the dependencies
    matches: List[Match] = []

    # go through the list of types we know for this response
    for resp_tmpl_elem in resp_types:
        # skip the type in these cases
        if resp_tmpl_elem.type in ["off_t", "size_t"]:
            continue

        # go through the list of types for this request
        for req_tmpl_elem in req_types:
            # for a value dependency, the size has to match
            if resp_tmpl_elem.size != req_tmpl_elem.size:
                continue

            check = set(resp[resp_tmpl_elem.start : resp_tmpl_elem.end])

            # do not consider sequences of nullbytes
            if len(check) == 1 and check.pop() == 0:
                continue

            # do not consider sequences up to a length of two bytes
            # where one byte is a nullbyte
            if len(check) <= 2 and 0 in check:
                continue

            # do not consider these blacklists of types
            if (
                resp_tmpl_elem.type in EXCLUDED_TYPES
                or req_tmpl_elem.type in EXCLUDED_TYPES
            ):
                continue

            if (
                resp[resp_tmpl_elem.start : resp_tmpl_elem.end]
                == req[req_tmpl_elem.start : req_tmpl_elem.end]
            ):
                log.info("MATCH!")
                resp_name = os.path.basename(resp_path)
                req_name = os.path.basename(req_path)
                match = Match(
                    resp_nr,
                    resp_name,
                    resp_tmpl_elem,
                    resp_func,
                    req_nr,
                    req_name,
                    req_tmpl_elem,
                    req_func,
                )

                matches.append(match)

    if len(matches) == 0:
        return None

    for match in matches:
        if match.resp_tmpl_elem.size != match.req_tmpl_elem.size:
            import ipdb

            ipdb.set_trace()

    return matches


def match_fp_calls(tee, onleave_param, onenter_param):
    global SPECIAL_DEP_BASE, SPECIAL_DEP_IDX
    param_out = os.path.basename(onleave_param)
    param_in = os.path.basename(onenter_param)
    dir_out = os.path.dirname(onleave_param)
    dir_in = os.path.dirname(onenter_param)

    if "param_1_a" != param_out and "resp" != param_out:
        return None
    if "param_1_a" != param_in and "req" != param_in:
        return None

    if find_dirs(dir_out, "hal_*") is None:
        return None
    if find_dirs(dir_in, "hal_*") is None:
        return None

    respFunc = os.path.basename(find_dirs(dir_out, "hal_*")[0])
    respFunc = respFunc[respFunc.find("_") + 1 : respFunc.rfind("_")]

    reqFunc = os.path.basename(find_dirs(dir_in, "hal_*")[0])
    reqFunc = reqFunc[reqFunc.find("_") + 1 : reqFunc.rfind("_")]

    respNr = int(os.path.basename(os.path.dirname(dir_out)))
    reqNr = int(os.path.basename(os.path.dirname(dir_out)))

    # TODO is the distance between pre_enroll and enroll ioctl always 3 on tc?
    if (
        tee == "tc"
        and respFunc == "pre_enroll"
        and reqFunc == "enroll"
        and respNr == (reqNr - 3)
    ):
        log.info("Found get_auth_token ")
        MAGIC_GET_AUTH_TOKEN_NR = SPECIAL_DEP_BASE | SPECIAL_DEP_IDX  # TODO: refactor
        SPECIAL_DEP_IDX += 1

        callDep1 = (
            (respFunc, respNr, [(0, 8, "param_1_a")]),
            ("get_auth_token", MAGIC_GET_AUTH_TOKEN_NR, [(0, 8, "param_1_a")]),
        )

        callDep2 = (
            ("get_auth_token", MAGIC_GET_AUTH_TOKEN_NR, [(0, 0x45, "param_3_a")]),
            (reqFunc, reqNr, [(1, 0x45, "param_1_a")]),
        )
        return (callDep1, callDep2)
    return None


def match_params(param_pairs):
    value_dependencies: List[Match] = []

    # go through the onleave indices. the last index is the second last
    # because we do not have anything to match after.
    for onleave_param_idx in range(len(param_pairs) - 1):
        # go through the onenter indices. the first index is the one
        # following the current `onleave_param_idx` to respect the
        # ordering dependence (i.e., a value from an earlier request
        # cannot depend on a value from a later request
        for onenter_param_idx in range(onleave_param_idx + 1, len(param_pairs)):
            # we want a sliding window of responses that we match to
            # later requests. if we observe a response that matches to a
            # later request (say 16 requests later), this request has to
            # be within the MATCHING_WINDOW. the intuition is that calls
            # that have value dependencies are close to each other.
            if onleave_param_idx - onenter_param_idx > MATCHING_WINDOW:
                break

            _, onleave_params = param_pairs[onleave_param_idx]
            onenter_params, _ = param_pairs[onenter_param_idx]

            # go through the responses and check if they are re-used
            # later in a request
            for onleave_param in onleave_params:
                for onenter_param in onenter_params:
                    log.debug("Doing {} and {}".format(onenter_param, onleave_param))

                    if not os.path.isfile(onleave_param) or not os.path.isfile(
                        "{}.types".format(onleave_param)
                    ):
                        log.error("resp files missing: {}".format(onleave_param))
                        continue
                    if not os.path.isfile(onenter_param) or not os.path.isfile(
                        "{}.types".format(onenter_param)
                    ):
                        log.error("req files missing: {}".format(onenter_param))
                        continue

                    # TODO: why do we do this for all TAs and not just fp?
                    # if tee == "tc":
                    #    call_dep = matchFpCalls(tee, onleave_param, onenter_param)
                    #    if call_dep is not None:
                    #        # This is a dirty hack, but still the best solution so far
                    #        cd1, cd2 = call_dep
                    #        call_deps.append(cd1)
                    #        call_deps.append(cd2)
                    #        #appendCallDeps(cd1, callDeps)
                    #        #appendCallDeps(cd2, callDeps)
                    #        continue

                    valdep_candidates = match_parameter(onleave_param, onenter_param)
                    if valdep_candidates != None:
                        # remove overlapping dependencies within current resp/req pair
                        valdep_candidates = remove_overlapping(valdep_candidates)
                        # append to total value deps and remove overlapping
                        append_call_deps(valdep_candidates, value_dependencies)
    return value_dependencies


def remove_overlapping(valdep_candidates: List[Match]) -> List[Match]:
    """Remover overlapping value dependencies in the request. Keep the larger
    element."""

    del_indices: List[int] = []
    for idx_a, match_a in enumerate(valdep_candidates):
        sz_a = match_a.req_tmpl_elem.size
        for idx_b, match_b in enumerate(valdep_candidates):
            if idx_a == idx_b:
                continue
            sz_b = match_b.req_tmpl_elem.size
            # b starts within a
            # OR
            # b ends witihn a
            if match_a.req_collides(match_b):
                if sz_a >= sz_b:
                    # keep a delete b
                    del_indices.append(idx_b)
                else:
                    # keep b delete a
                    del_indices.append(idx_a)

    for idx in del_indices:
        del valdep_candidates[idx]
    return valdep_candidates


def append_call_deps(valdep_candidates: List[Match], value_dependencies: List[Match]):
    """Merge the candidates to the existing list. Give priority to the larger
    dependency in case of a collision."""

    dst_exists = False
    for idx, valdep in enumerate(value_dependencies):
        for valdep_cand in valdep_candidates:
            # if the destination is not the same request, continue
            if not (
                (valdep.req_nr == valdep_cand.req_nr)
                and (valdep.req_func_name == valdep_cand.req_func_name)
                and (valdep.req_name == valdep_cand.req_name)
            ):
                continue
            dst_exists = True

            # if the destinations do not overlap, continue
            if not valdep.req_collides(valdep_cand):
                continue

            # we have a collision, take the larger dependency
            if valdep.req_tmpl_elem.size >= valdep_cand.req_tmpl_elem.size:
                # the candidate is smaller, drop it
                continue
            else:
                # substitute for candidate, since it's larger
                value_dependencies[idx] = valdep_cand

    if not dst_exists:
        # we have not seen this destination request yet, add the candidate
        value_dependencies.extend(valdep_candidates)


def create_dependency(
    sequence_dir: str, seq_ids: List[int], value_dependencies: List[Match]
) -> IoctlCallSequence:
    dump_group_id = int(os.path.basename(sequence_dir))

    # create dump sequence
    sequence = IoctlCallSequence()
    for d in seq_ids:
        sequence.append(IoctlCall(dump_group_id, int(d)))

    for valdep in value_dependencies:
        if valdep.req_nr & 0xFFFF0000 == SPECIAL_DEP_BASE:
            sequence.insert(
                valdep.resp_nr + 1,
                IoctlCall(dump_group_id, valdep.req_nr, is_dump_backed=False),
            )

        try:
            src: IoctlCall = sequence.get_elem_by_dump_id(valdep.resp_nr)
            dst: IoctlCall = sequence.get_elem_by_dump_id(valdep.req_nr)
        except Exception as e:
            import ipdb

            ipdb.set_trace()
            sys.exit()

        src_off: int = valdep.resp_tmpl_elem.start
        src_sz: int = valdep.resp_tmpl_elem.size
        src_param_identifier: str = valdep.resp_name

        dst_off: int = valdep.req_tmpl_elem.start
        dst_sz: int = valdep.req_tmpl_elem.size
        dst_param_identifier: str = valdep.req_name

        assert src_sz == dst_sz, "value dep src/dst sizes mismatch"

        if not dst or not src:
            import ipdb

            ipdb.set_trace()

        if (dst.dump_id <= src.dump_id) or (
            src.dump_id & 0xFFFF0000 == SPECIAL_DEP_BASE
        ):
            log.error(
                "value dependency found that does not correspond"
                " to ordering dependence"
            )
            import ipdb

            ipdb.set_trace()

        val_dep = ValueDependency(
            src,
            src_param_identifier,
            src_off,
            src_sz,
            dst_param_identifier,
            dst_off,
            dst_sz,
        )
        dst.value_dependencies.append(val_dep)

    return sequence


def retrieve_req_resp_pairs_qsee(seq_dir: str, seq_ids: List[int]):
    """retrieve the filenames of the requests and responses for qsee."""
    req_resp_pairs = []
    for e in seq_ids:
        type_dict = {"onenter": [], "onleave": []}
        for pType in ["onenter", "onleave"]:
            filenames = []
            if pType == "onleave":
                filenames.extend(["resp", "shared"])
            else:
                filenames.extend(["req", "shared"])
            for filename in filenames:
                for param_path in glob.glob(
                    os.path.join(seq_dir, str(e), pType, filename)
                ):
                    type_dict[pType].append(param_path)
        req_resp_pairs.append((type_dict["onenter"], type_dict["onleave"]))
    return req_resp_pairs


def retrieve_req_resp_pairs_tc(seq_dir: str, seq_ids: List[int]):
    """retrieve the filenames of the requests and responses for tc."""
    req_resp_pairs = []
    for e in seq_ids:
        type_dict = {"onenter": [], "onleave": []}
        for pType in ["onenter", "onleave"]:
            # For tc, buffers are stored in `param_{0,1,2,3}_a``
            # TODO: we neglect `param_?_b` and `param_?_c` here
            for param_path in glob.glob(
                os.path.join(seq_dir, str(e), pType, "param_?_a")
            ):
                if is_relevant_file_tc(param_path):
                    type_dict[pType].append(param_path)
        req_resp_pairs.append((type_dict["onenter"], type_dict["onleave"]))
    return req_resp_pairs


def retrieve_req_resp_pairs_optee(seq_dir: str, seq_ids: List[int]):
    """retrieve the filenames of the requests and responses for optee."""
    req_resp_pairs = []
    for e in seq_ids:
        type_dict = {"onenter": [], "onleave": []}
        for pType in ["onenter", "onleave"]:
            # For optee, buffers are stored in param_{0,1,2,3}_data
            # and we only consider buffers here.
            for param_path in glob.glob(
                os.path.join(seq_dir, str(e), pType, "param_?_data")
            ):
                type_dict[pType].append(param_path)
        req_resp_pairs.append((type_dict["onenter"], type_dict["onleave"]))
    return req_resp_pairs


def collect_seq_ids(seq_dir: str) -> List[int]:
    # retrieve the sequence of calls
    seq_ids = [int(seq_id) for seq_id in os.listdir(seq_dir) if "pickle" not in seq_id]
    # sort the sequence (this overapproximates an ordering dependence)
    seq_ids.sort()
    return seq_ids


def remove_seq_id_gaps(seq_dir: str) -> None:
    seq_ids = collect_seq_ids(seq_dir)
    for idx, seq_id in enumerate(seq_ids):
        assert idx <= seq_id, "The sequence id cannot be smaller than the idx."
        if seq_id > idx:
            src_dir = os.path.join(seq_dir, str(seq_id))
            dst_dir = os.path.join(seq_dir, str(idx))
            shutil.move(src_dir, dst_dir)


def find_value_deps(tee: str, seq_dir: str):
    # the group directory contains multiple directories where each
    # contains the data sent to and received from the TA from the
    # perspective of the ioctl-interface of the Linux kernel.

    # remove gaps between sequence ids
    remove_seq_id_gaps(seq_dir)

    seq_ids = collect_seq_ids(seq_dir)

    if tee == "qsee":
        req_resp_pairs = retrieve_req_resp_pairs_qsee(seq_dir, seq_ids)
    elif tee == "tc":
        req_resp_pairs = retrieve_req_resp_pairs_tc(seq_dir, seq_ids)
    elif tee == "optee":
        req_resp_pairs = retrieve_req_resp_pairs_optee(seq_dir, seq_ids)
    else:
        log.error("tee {} not known. aborting.".format(tee))
        sys.exit()

    if not req_resp_pairs:
        log.error("no files found.")
        return

    value_dependencies: List[Match] = match_params(req_resp_pairs)
    sequence = create_dependency(seq_dir, seq_ids, value_dependencies)
    with open(os.path.join(seq_dir, DEPENDENCY_FILE), "wb") as f:
        pickle.dump(sequence, f)


def usage():
    print("Usage:\n\t{} <qsee|tc|optee> <group_dir>".format(sys.argv[0]))


if __name__ == "__main__":
    if len(sys.argv) < 3 or not os.path.isdir(sys.argv[2]):
        usage()
    else:
        find_value_deps(sys.argv[1], sys.argv[2])
