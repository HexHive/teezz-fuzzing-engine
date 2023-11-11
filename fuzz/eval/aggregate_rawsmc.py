#!/usr/bin/env python3
import sys
import os

SMC_RET_COL_IDX = 1 # TC
SMC_RET_COL_IDX = 4 # QSEE
"""
TC format:

IN:<param_i>{3}\n
OUT:<ret_val>{2}\n

QSEE format:

IN:<param_i>{3}\n
OUT:<ret_val>{5}\n
"""

def process_logline(logline):
    try:
        tmp = logline.split(':')[1]
        r = tmp.split(';')
    except IndexError as e:
        # probably this log entry is corrupt
        print(e)
        print("caused by line:")
        print(logline)
        #import ipdb; ipdb.set_trace()
        return None, None
    return r


def analyze_log(data, stats):
    parsed_data = []

    idx = 0
    prev_idx = -1
    next_begin = "IN"
    
    req_ctr = 0
    curr_in = None
    curr_out = None
    while idx != -1:
        idx = data.find('\n', prev_idx+1)
        
        line = data[prev_idx+1:idx]
        if (line.startswith("IN") or line.startswith("OUT")) and "##" not in line:
            if next_begin == "IN" and line.startswith("IN"):
                curr_in = line
                next_begin = "OUT"
            elif next_begin == "OUT" and line.startswith("OUT") and curr_in:
                curr_out = line
                parsed_data.append((curr_in, curr_out))
                curr_in = None
                curr_out = None
                req_ctr += 1
                next_begin = "IN"
            else:
                curr_in = None
                curr_out = None
                next_begin = "IN"
        else:
                #print("broken line: {}".format(line))
                if "##" in line and curr_in:
                    req_ctr += 1
                    params = process_logline(curr_in)
                    stats["crashes"].append(params)
                curr_in = None
                curr_out = None
                next_begin = "IN"

        prev_idx = idx

    params = None
    for in_,out_ in parsed_data:
        params = process_logline(in_)
        ret = process_logline(out_)
        try:
            int(ret[1], 16)
        except:
            #print("cannot decode hex: {}".format(ret[0]))
            continue

        if ret[1] not in stats:
            stats[ret[1]] = 0
        stats[ret[1]] += 1

        if ret[1] != '0xffffffff' or ret[1] != '0xffffffffffffffff':
            pass
    return req_ctr


def main(log_dir):

    stats = { "crashes" : [] }
    req_ctr = 0

    log_files = [os.path.join(log_dir, f) for f in os.listdir(log_dir)]

    for log in log_files:
        print(log)
        with open(log) as f:
            data = f.read()

        req_ctr += analyze_log(data, stats)

    print("#reqs: {}".format(req_ctr))
    for k in stats.keys():
        if k != "crashes":
            print("{} : {}".format(k, stats[k]))
    print("len(crashes): {}".format(len(stats["crashes"])))


def usage():
    print("Usage:\n\t{} <raw_smc_log_optee>".format(sys.argv[0]))


if __name__=="__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit()
    main(sys.argv[1])

