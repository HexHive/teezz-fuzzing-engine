#!/usr/bin/env python
import sys
import os

"""
Format:

IN:<param_i>{8}\n
OUT:<ret_val>{4}\n
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


def main(log):

    stats = { "crashes" : [] }
    print(log)
    with open(log) as f:
        data = f.read()

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
                #print("broken line: {}".format(line))
                if '0x8ab61cbaeff34349;0x8c63ba1f89bded27' in line:
                    import ipdb; ipdb.set_trace()
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
            int(ret[0], 16)
        except:
            #print("cannot decode hex: {}".format(ret[0]))
            continue

        if ret[0] not in stats:
            stats[ret[0]] = 0
        stats[ret[0]] += 1

        if ret[0] != '0xffffffff' or ret[0] != '0xffffffffffffffff':
            pass
            #print(ret[0])
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
