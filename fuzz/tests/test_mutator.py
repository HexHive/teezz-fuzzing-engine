#!/usr/bin/env python

import sys
import copy
import os
import pickle
import math
import random
from mutator import mutator

ITERATIONS = 1000

def start_proc(tee, engine, seeds_dir):
    process = 'keystore'
    config_path = None
    cur_mutator = mutator.get_mutator(tee, seeds_dir, engine, process, config_path)

    result = []
    for i in range(0, ITERATIONS):
        if tee == 'qsee':
            data = mutate_qsee(cur_mutator)
            #print(str(len(data[0].cmd_req_buf)) + data[0].cmd_req_buf)
            #print(str(len(data[1].cmd_req_buf)) + data[1].cmd_req_buf)

            changed = 0
            for a in range(0, data[0].cmd_req_len):
                if data[0].cmd_req_buf[a] != data[1].cmd_req_buf[a]:
                    changed += 1

            result.append((data[0].cmd_req_len, changed))

            percent = changed / (data[0].cmd_req_len / 100.0)
            print("     -> {} ({:.2f}%) Bytes from {} got mutated! ".format(changed, percent, data[0].cmd_req_len))

        elif tee == 'tc':
            data = mutate_tc(cur_mutator)
        else:
            print("TEE not supported!!!")
            sys.exit(1)

    # calculate mean percent
    total_bytes = 0
    total_changed = 0
    for data in result:
        total_bytes += data[0]
        total_changed += data[1]

    avg_percent = total_changed / (total_bytes / 100.0)

    # calculate standard derivation
    avg_stdder = 0.0
    min_percent = 100.0
    max_percent = 0.0
    for data in result:
        cur_percent = data[1] / (data[0] / 100.0)
        if cur_percent > max_percent:
            max_percent = cur_percent
        if cur_percent < min_percent:
            min_percent = cur_percent
        avg_stdder += math.pow((cur_percent - avg_percent), 2)

    std_der = math.sqrt(avg_stdder / float(ITERATIONS))

    print("")
    print("--------------------------------------")
    print("RESULTS for {} mutations ({}, {}):".format(ITERATIONS, tee, engine))
    print("{} from {} Bytes mutated!".format(total_changed, total_bytes))
    print("Average: {:.2f}%".format(avg_percent))
    print("Minimum: {:.2f}%".format(min_percent))
    print("Maximum: {:.2f}%".format(max_percent))
    print("Standard Derivation: {:.2f}".format(std_der))



def mutate_qsee(mutator):
    mutator.next_seed()
    mutant = copy.deepcopy(mutator.current_seed)
    orig = copy.deepcopy(mutator.current_seed)

    req_types_path = os.path.join(mutator.current_seed_dir, "{}.{}".format(mutator.REQ, mutator.TYPES_EXTENSION))

    if not os.path.exists(req_types_path):
        print("no format for parameter")
        msg_format = None
    else:
        with open(req_types_path) as f:
            msg_format = pickle.load(f)

    mutant.cmd_req_buf = mutator.engine.do_mutate(mutant.cmd_req_buf, **{"msg_format": msg_format})

    mutator.current_mutation = mutant
    return (orig, mutant)

def mutate_tc(mutator):
    mutator.next_seed()
    ctx = copy.deepcopy(mutator.current_seed)
    ctx_orig = copy.deepcopy(mutator.current_seed)

    for i, param in enumerate(ctx.params):
        chance = random.randint(1, 100)
        if param and param.param_type in huawei.tc_structs.TC_NS_ClientParam.memref_input_types:
            if chance <= 70: # 70 % chance this param gets mutated
                #log.info("Mutating buffer of param #{}".format(i))
                param_types_path = os.path.join(mutator.current_seed_dir, "param_{}_a.{}".format(i, mutator.TYPES_EXTENSION))

                if not os.path.exists(param_types_path):
                    print("no format for parameter")
                    msg_format = None
                else:
                    with open(param_types_path) as f:
                        msg_format = pickle.load(f)

                param.buffer = mutator.engine.do_mutate(param.buffer,
                                                     **{"msg_format": msg_format})
    mutator.current_mutation = ctx
    return (ctx_orig, ctx)


if __name__ == '__main__':
    if(len(sys.argv) != 4):
        print("Usage: {} <TEE> <Engine> <Seeds-Dir>".format(sys.argv[0]))
        sys.exit(1)
    start_proc(sys.argv[1], sys.argv[2], sys.argv[3])
