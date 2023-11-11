#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Call this script like this:
# ./crash_info.py <path_to_crash> | less -R
# Or in a loop:
# for i in $(ls *_hisi_teelog); do ../../crash_info.py $i | less -R ; done

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../tzzz_fuzzer/fuzz'))
from qsee_structs import QseecomSendCmdReq
from tc_structs import TC_NS_ClientContext

import re
import pickle
from hexdump import hexdump
from difflib import Differ
from colorama import init, Fore, Style


def param_type_str(param):
    s = ''
    if not param:
        return 'none'
    if param.param_type in param.value_types:
        s += 'value'
    elif param.param_type in param.memref_types:
        s += 'memref'
    else:
        s += 'none'
    if param.param_type in [0x03, 0x07, 0x0c, 0x0f]:
        s += Style.BRIGHT + ' inout' + Style.NORMAL
    elif param.param_type in [0x01, 0x05, 0x0d]:
        s += Style.BRIGHT + ' in' + Style.NORMAL
    elif param.param_type in [0x02, 0x06, 0x0e]:
        s += Style.BRIGHT + ' out' + Style.NORMAL
    return s

def pretty_print_TC_NS_ClientContext(ctx):
    s = ''
    s += Fore.LIGHTGREEN_EX + Style.BRIGHT + 'Started:     ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(ctx.started) + Fore.LIGHTBLUE_EX + ' (' + hex(ctx.started) + ')' + Fore.RESET + '\n'
    s += Fore.LIGHTGREEN_EX + Style.BRIGHT + 'Command ID:  ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(ctx.cmd_id) + Fore.LIGHTBLUE_EX + ' (' + hex(ctx.cmd_id) + ')' + Fore.RESET + '\n'
    s += Fore.LIGHTGREEN_EX + Style.BRIGHT + 'Session ID:  ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(ctx.session_id) + Fore.LIGHTBLUE_EX + ' (' + hex(ctx.session_id) + ')' + Fore.RESET + '\n'
    params_str = ', '.join([param_type_str(param) for param in ctx.params])
    s += Fore.LIGHTGREEN_EX + Style.BRIGHT + 'Param types: ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(ctx.paramTypes) + Fore.LIGHTBLUE_EX + ' (' + hex(ctx.paramTypes) + ')' + Fore.LIGHTMAGENTA_EX +' (' + params_str + ')' + Fore.RESET + '\n'
    s += Fore.LIGHTGREEN_EX + Style.BRIGHT + 'Params:      ' + Style.RESET_ALL + '[\n'
    for param in ctx.params:
        param_type = param.param_type if param else 0
        s += '    {\n'
        s += Fore.LIGHTGREEN_EX + Style.BRIGHT + '        Param type:    ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(param_type) + Fore.LIGHTBLUE_EX + ' (' + hex(param_type) + ') ' + Fore.LIGHTMAGENTA_EX + '(' + param_type_str(param) + ')' + Style.RESET_ALL + '\n'
        if param and param_type in param.value_types:
            s += Fore.LIGHTGREEN_EX + Style.BRIGHT + '        Value a:       ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(param.value_a) + Fore.LIGHTBLUE_EX + ' (' + hex(param.value_a) + ')' + Style.RESET_ALL + '\n'
            s += Fore.LIGHTGREEN_EX + Style.BRIGHT + '        Value b:       ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(param.value_b) + Fore.LIGHTBLUE_EX + ' (' + hex(param.value_b) + ')' + Style.RESET_ALL + '\n'
        if param and param_type in param.memref_types:
            s += Fore.LIGHTGREEN_EX + Style.BRIGHT + '        Buffer offset: ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(param.offset) + Fore.LIGHTBLUE_EX + ' (' + hex(param.offset) + ')\n'
            s += Fore.LIGHTGREEN_EX + Style.BRIGHT + '        Buffer size:   ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(param.size) + Fore.LIGHTBLUE_EX + ' (' + hex(param.size) + ')\n'
            s += Fore.LIGHTGREEN_EX + Style.BRIGHT + '        Buffer:' + Style.RESET_ALL + '\n'
            for line in hexdump(param.buffer, 'generator'):
                s += ' ' * 12 + line + '\n'
        s += '    },\n'
    s += ']\n'
    return s

def pretty_print_QseecomSendCmdReq(ctx):
    s = ''
    s += Fore.LIGHTGREEN_EX + Style.BRIGHT + 'Request buffer size: ' + Style.RESET_ALL + Fore.LIGHTYELLOW_EX + str(ctx.cmd_req_len) + Fore.LIGHTBLUE_EX + ' (' + hex(ctx.cmd_req_len) + ')' + Style.RESET_ALL + '\n'
    s += Fore.LIGHTGREEN_EX + Style.BRIGHT + 'Request buffer:' + Style.RESET_ALL + '\n'
    for line in hexdump(ctx.cmd_req_buf, 'generator'):
        s += ' ' * 4 + line + '\n'
    return s

def pretty_print_request(ctx):
    if isinstance(ctx, TC_NS_ClientContext):
        return pretty_print_TC_NS_ClientContext(ctx)
    elif isinstance(ctx, QseecomSendCmdReq):
        return pretty_print_QseecomSendCmdReq(ctx)


def main(crash_path):
    # First argument is the path to a crash
    if crash_path.endswith('hisi_teelog'):
        crash_path = crash_path[:-len('hisi_teelog')]
    elif crash_path.endswith('seed_ctx.pickle'):
        crash_path = crash_path[:-len('seed_ctx.pickle')]
    elif crash_path.endswith('seed.pickle'):
        crash_path = crash_path[:-len('seed.pickle')]
    elif crash_path.endswith('mutation_ctx.pickle'):
        crash_path = crash_path[:-len('mutation_ctx.pickle')]
    elif crash_path.endswith('mutation.pickle'):
        crash_path = crash_path[:-len('mutation.pickle')]
    teelog_path = crash_path + 'hisi_teelog'
    seed_path = crash_path + 'seed_ctx.pickle'
    if not os.path.exists(seed_path):
        seed_path = crash_path + 'seed.pickle'
    mutation_path = crash_path + 'mutation_ctx.pickle'
    if not os.path.exists(mutation_path):
        mutation_path = crash_path + 'mutation.pickle'

    crash_name = os.path.basename(crash_path)
    id_parts = crash_name.split('_')
    print(Fore.YELLOW + 'Filename: ' + Style.BRIGHT + (teelog_path if os.path.exists(teelog_path) else sys.argv[1]) + Style.RESET_ALL)
    print(Fore.YELLOW + 'Crash ID: ' + Style.BRIGHT + id_parts[-2] + Style.RESET_ALL)
    print(Fore.YELLOW + 'Crash timestamp: ' + Style.BRIGHT + id_parts[0] + ' ' + id_parts[1].replace('-', ':') + Style.RESET_ALL)
    print

    # Load backtrace
    if os.path.exists(teelog_path):
        with open(teelog_path) as f:
            content = f.read().replace('\x00', '')
        m = re.search(r'=+\s*The PC which result in abort is .*=+\s*Task Crash\s*=+', content, re.MULTILINE | re.DOTALL)
        if m:
            print(m.group(0))

    seed_str = None
    mutation_str = None

    # Load seed
    if os.path.exists(seed_path):
        with open(seed_path) as f:
            seed = pickle.load(f)
        seed_str = pretty_print_request(seed)


    # Load mutation
    if os.path.exists(mutation_path):
        with open(mutation_path) as f:
            mutation = pickle.load(f)
        mutation_str = pretty_print_request(mutation)

    if seed_str and mutation_str:
        d = Differ()
        print('\n')
        print('========== SEED - MUTATION diff ==========')
        for line in d.compare(seed_str.splitlines(True), mutation_str.splitlines(True)):
            if line.startswith('- '):
                sys.stdout.write(Fore.RED + line + Fore.RESET)
            elif line.startswith('+ '):
                sys.stdout.write(Fore.GREEN + line + Fore.RESET)
            elif line.startswith('? '):
                sys.stdout.write(Fore.CYAN + line + Fore.RESET)
            elif line.startswith(' ' * (12 if isinstance(seed, TC_NS_ClientContext) else 4)):
                sys.stdout.write(Style.DIM + line + Style.RESET_ALL)
            else:
                sys.stdout.write(line)
    elif seed_str:
        print('\n')
        print('========== SEED ==========')
        for line in seed_str.split('\n'):
            if line.startswith(' ' *  (12 if isinstance(seed, TC_NS_ClientContext) else 4)):
                print(Style.DIM + line + Style.RESET_ALL)
            else:
                print(line)
    elif mutation_str:
        print('\n')
        print('========== MUTATION ==========')
        for line in mutation_str.split('\n'):
            if line.startswith(' ' *  (12 if isinstance(mutation, TC_NS_ClientContext) else 4)):
                print(Style.DIM + line + Style.RESET_ALL)
            else:
                print(line)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: ' + sys.argv[0] + ' <crash_path...>')
        exit(1)

    for i in range(1, len(sys.argv)):
        if i > 1:
            print('\n\n')
        main(sys.argv[i])
