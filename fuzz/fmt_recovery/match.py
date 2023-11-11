from __future__ import annotations
import sys
import logging
import pickle
import os
import glob
from scipy.stats import entropy
from collections import OrderedDict, Counter
from fuzz.seed.seedtemplate import SeedTemplate, SeedTemplateElement

from typing import List, Dict, Tuple, Optional
from fuzz.const import TEEID
from fuzz.utils import find_files

################################################################################
# LOGGING
################################################################################

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

################################################################################
# CODE
################################################################################


def estimate_shannon_entropy(seq):
    """
    kudos https://onestopdataanalysis.com/shannon-entropy/
    """
    bases = Counter([tmp_base for tmp_base in seq])
    # define distribution
    dist = [x / sum(bases.values()) for x in bases.values()]
    entropy_value = entropy(dist, base=2)

    return entropy_value


def get_seed_cls(target_tee: str) -> object:
    # TODO: refactor typing once we have an ABC for these imports
    if target_tee == TEEID.OPTEE:
        from fuzz.optee.opteedata import TeeIoctlInvokeArg as cls
    elif target_tee == TEEID.TC:
        from fuzz.huawei.tc.tcdata import TC_NS_ClientContext as cls
    elif target_tee == TEEID.QSEE:
        from fuzz.qc.qsee.qseedata import QseecomSendCmdReq as cls
    else:
        log.error(f"Unknown TEE {target_tee}")
        import ipdb

        ipdb.set_trace()
    return cls


def get_ioctl_recording_paths(tee, ioctl_recording_dir):
    if tee == "qsee":
        # re* for req and resp
        ioctl_recording_paths = [
            f
            for f in find_files(ioctl_recording_dir, ".*/\(resp\|req\)")
            if not f.endswith(b"types")
        ]
        # if no file named 'shared' exists find_files
        # returns None which can't be iterated
        # -> use glob for shared
        ioctl_recording_paths.extend(
            [
                f
                for f in glob.glob(os.path.join(ioctl_recording_dir, ".*/shared"))
                if not f.endswith(b"types")
            ]
        )
    elif tee == "tc":
        ioctl_recording_paths = [
            f
            for f in find_files(ioctl_recording_dir, ".*/param_.*")
            if not f.endswith(b"types")
        ]
    elif tee == "optee":
        ioctl_recording_paths = [
            f
            for f in find_files(ioctl_recording_dir, ".*/param_.*")
            if not f.endswith(b"types")
        ]
    else:
        log.error("tee {} unknown.".format(tee))
        sys.exit(0)
    return ioctl_recording_paths


def extract_leaf_nodes(
    hal_data: Dict[str, str | object]
) -> List[Optional[Tuple[str, bytes]]]:
    tv: List[Tuple[str, bytes]] = list()

    if "data" in hal_data:
        if isinstance(hal_data["data"], OrderedDict):
            for k in hal_data["data"].keys():
                tv.extend(extract_leaf_nodes(hal_data["data"][k]))
            return tv
        else:
            return [
                (hal_data["type"], hal_data["data"]),
            ]
    return []


def matchify(
    hal_recording_paths: List[str],
    ioctl_recording_path: str,
    match_count_d: Dict[int, Dict[str, int | bool]],
):
    hal_data = []
    for hal_recording_path in hal_recording_paths:
        log.debug(hal_recording_path)
        with open(hal_recording_path, "rb") as f:
            deserialized = pickle.load(f)
            # log.debug(deserialized)
            if deserialized:
                hal_data.append(deserialized)

    log.debug("---- File: {}".format(ioctl_recording_path))
    with open(ioctl_recording_path, "rb") as f:
        ioctl_seq = f.read()

    matches: List[SeedTemplateElement] = []
    for param_node_idx, param_node in enumerate(hal_data):
        leaf_nodes = extract_leaf_nodes(param_node)
        for leaf_node_idx, leaf_node in enumerate(leaf_nodes):
            data = leaf_node[1]
            type = leaf_node[0]

            hal_node_id = (param_node_idx, leaf_node_idx)
            if hal_node_id not in match_count_d.keys():
                match_count_d[hal_node_id] = {
                    "cnt": 0,
                    "type": type,
                    "sz": len(data),
                    "zero": False,
                    "partial": False,
                }

            if ioctl_seq and data:
                # we do not match individual bytes
                if len(data) == 1:
                    continue

                # ignore zero sequences, we do not match
                # a sequence that is only zeroes
                unique = set(data)
                if len(unique) == 1 and unique.pop() == 0:
                    match_count_d[hal_node_id]["zero"] = True
                    continue

                # TODO: we are only looking for the first match here
                #       keep it this way?

                # ignore partial matches, we only apply the type if
                # it is entirely present within the sequence
                off = ioctl_seq.find(data)
                if off == -1:
                    if match_count_d[hal_node_id]["cnt"] == 0:
                        match_count_d[hal_node_id]["partial"] = True
                    continue

                size = len(data)
                match_count_d[hal_node_id]["cnt"] += 1
                if match_count_d[hal_node_id]["partial"]:
                    match_count_d[hal_node_id]["partial"] = False
                matches.append(SeedTemplateElement(off, off + size, type))

    # sort our matches so that the biggest matches are applied first
    matches = sorted(matches, key=lambda match: match.size, reverse=True)

    if matches:
        with open(f"{ioctl_recording_path}.types", "rb") as f:
            seed_tmpl: SeedTemplate = pickle.load(f)

        for new_elem in matches:
            try:
                seed_tmpl.add_elem(new_elem)
            except ValueError as e:
                log.warning(f"Could not add type {new_elem}: {e}")

        # serialize matches
        with open(f"{ioctl_recording_path}.types", "wb") as f:
            pickle.dump(seed_tmpl, f)

    return


def handle_recordings(
    hal_recording_dir: str,
    ioctl_recording_paths: List[str],
    match_count_d: Dict[int, Dict[str, int | bool]],
):
    hal_recording_paths = find_files(hal_recording_dir, ".*")
    if not hal_recording_paths:
        log.error("no typed hal dumps in '{}'.".format(hal_recording_dir))
        return None
    for ioctl_recording_path in ioctl_recording_paths:
        matchify(hal_recording_paths, ioctl_recording_path, match_count_d)
    return


def main(tee: str, recordings_base_dir: str) -> None:
    hal_recording_onenter_dirs: List[str] = []
    hal_recording_onleave_dirs: List[str] = []

    # find all the recordings of high-level functions
    # by convention, all high-level functions start with the 'hal_' prefix
    # seperate the onenter from the onleave recordings
    for d in glob.glob(os.path.join(recordings_base_dir, "*/*/onenter/hal_*")):
        hal_recording_onenter_dirs.append(d)
    for d in glob.glob(os.path.join(recordings_base_dir, "*/*/onleave/hal_*")):
        hal_recording_onleave_dirs.append(d)

    hal_recording_onenter_dirs.sort()
    hal_recording_onleave_dirs.sort()

    seedCls = get_seed_cls(tee)

    # go through the onenter recordings
    for hal_recording_dir in hal_recording_onenter_dirs:
        seed = seedCls.deserialize_raw_from_path(os.path.dirname(hal_recording_dir))
        match_count_d = {}
        for idx, param in enumerate(seed.params):
            if not param.is_input():
                continue
            if not param.data or not param.data_paths:
                continue
            handle_recordings(hal_recording_dir, param.data_paths, match_count_d)
        stats_path = os.path.join(hal_recording_dir, "match.stats")
        with open(stats_path, "wb") as f:
            pickle.dump(match_count_d, f)

    # go through the onleave recordings
    for hal_recording_dir in hal_recording_onleave_dirs:
        seed = seedCls.deserialize_raw_from_path(os.path.dirname(hal_recording_dir))
        match_count_d = {}
        for param in seed.params:
            if not param.is_output():
                continue
            if not param.data or not param.data_paths:
                continue
            handle_recordings(hal_recording_dir, param.data_paths, match_count_d)
        stats_path = os.path.join(hal_recording_dir, "match.stats")
        with open(stats_path, "wb") as f:
            pickle.dump(match_count_d, f)


def usage():
    print("Usage:\n\t{} <tc|qsee> <dump_dir>".format(sys.argv[0]))


if __name__ == "__main__":
    if len(sys.argv) >= 3 and os.path.isdir(sys.argv[2]):
        tee = sys.argv[1]
        recordings_base_dir = sys.argv[2]
        main(tee, recordings_base_dir)
    else:
        usage()
