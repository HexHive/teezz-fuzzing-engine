"""Module providing functions to diff seeds and their corresponding mutants."""
import sys
import argparse
import pickle
import struct
from difflib import Differ
from colorama import Fore
from hexdump import hexdump
from fuzz.const import TEEID, TEEID_dict
from fuzz import huawei
from fuzz.huawei.tc import TEEC_ParamType

def diff(seed_hex, mutant_hex):
    differ = Differ()
    print('========== SEED (-) / MUTANT (+) DIFF ==========')
    for line in differ.compare(seed_hex.splitlines(True), mutant_hex.splitlines(True)):
        if line.startswith('- '):
            sys.stdout.write(Fore.RED + line + Fore.RESET)
        elif line.startswith('+ '):
            sys.stdout.write(Fore.GREEN + line + Fore.RESET)
        elif line.startswith('? '):
            sys.stdout.write(Fore.CYAN + line + Fore.RESET)
        else:
            sys.stdout.write(line)
    print()
    print('========== DIFF END ============================')

def diff_tc(seed, mutant):
    """Pretty print the diff of seed and mutant."""
    
    # diff cmdid
    seed_cmd_hex = hexdump(struct.pack("<I", seed.cmd_id), result='return')
    mutant_cmd_hex = hexdump(struct.pack("<I", mutant.cmd_id), result='return')

    
    print('========== CMD ID ==========')
    diff(seed_cmd_hex, mutant_cmd_hex)

    # diff params
    
    for param_idx in range(len(seed.get_params())):
        print(f'========== PARAM IDX {param_idx}  =====')
        seed_param = seed.get_params()[param_idx]
        mutant_param = mutant.get_params()[param_idx]
        
        if seed_param.get_param_type() == TEEC_ParamType.TEEC_NONE:
            print(f'========== PARAM IS NONE ==========')
            continue
        
        seed_a_or_buf = hexdump(seed_param.a_or_buf, result='return')
        mutant_a_or_buf = hexdump(mutant_param.a_or_buf, result='return')
        diff(seed_a_or_buf, mutant_a_or_buf)

        seed_b_or_off = hexdump(seed_param.b_or_off, result='return')
        mutant_b_or_off = hexdump(mutant_param.b_or_off, result='return')
        diff(seed_b_or_off, mutant_b_or_off)

        seed_c_or_sz = hexdump(seed_param.c_or_sz, result='return')
        mutant_c_or_sz = hexdump(mutant_param.c_or_sz, result='return')
        diff(seed_c_or_sz, mutant_c_or_sz)


def diff_qsee(seed, mutant):
    """Pretty print the diff of seed and mutant."""

    # qsee seed and mutant handling
    seed_buf = seed.cmd_req_buf
    mutant_buf = mutant.cmd_req_buf

    seed_hex = hexdump(seed_buf, result='return')
    mutant_hex = hexdump(mutant_buf, result='return')

    diff(seed_hex, mutant_hex)


def setup_args():
    """Returns an initialized argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--tee", required=True, choices=TEEID_dict.keys(), help="The targeted TEE.")
    parser.add_argument("seed", help="The seed's path.")
    parser.add_argument("mutant", help="The mutants's path.")
    return parser


def main():
    arg_parser = setup_args()
    args = arg_parser.parse_args()

    # get the data
    with open(args.seed, "rb") as f:
        seed = pickle.load(f)
    with open(args.mutant, "rb") as f:
        mutant = pickle.load(f)

    if args.tee == TEEID.QSEE:
        diff_qsee(seed, mutant)
    elif args.tee == TEEID.TC:
        diff_tc(seed, mutant)


if __name__=="__main__":
    main()
