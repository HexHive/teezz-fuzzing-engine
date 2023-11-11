#!/usr/bin/env python
import sys
import os
import pickle

def main(dep_chain):

    with open(dep_chain, "r") as f:
        dependency_seq = pickle.load(f)
    out_deps = []
    for dependency in dependency_seq:
        resp = dependency[0]
        req = dependency[1]

        resp_hal_name = resp[0]
        resp_dump_id = resp[1]
        resp_deps = resp[2]
        resp_tmp_list = []
        for resp_dep in resp_deps:
            off, sz = resp_dep
            resp_tmp_list.append((off, sz, "resp"))


        req_hal_name = req[0]
        req_dump_id = req[1]
        req_deps = req[2]
        req_tmp_list = []
        for req_dep in req_deps:
            off, sz = req_dep
            req_tmp_list.append((off, sz, "req"))


        out_deps.append(((resp_hal_name, resp_dump_id, resp_tmp_list), 
            (req_hal_name, req_dump_id, req_tmp_list)))

    with open("/tmp/update_seq_fixed.pickle", "wb") as f:
        pickle.dump(out_deps, f)

    """
    with open(dep_chains, "r") as f:
        all_dependency_seqs = pickle.load(f)

    for dependency_seq in all_dependency_seqs:
        for dependency in dependency_seq:
            resp = dependency[0]
            req = dependency[1]
            resp_id = resp[1]
            req_id = req[1]
            if req_id == 93 or resp_id == 93:
                import ipdb; ipdb.set_trace()
                with open("/tmp/update_seq.pickle", "wb") as f:
                    pickle.dump(dependency_seq, f)
                sys.exit()
    """


def usage():
    print("{} <dep_chains>".format(sys.argv[0]))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit()
    main(sys.argv[1])
