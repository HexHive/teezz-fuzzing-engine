#!/usr/bin/env python
from __future__ import print_function

import sys
import os
import json
import logging

log = logging.getLogger(__file__)

TARGET = 'optee'

UUID_FILENAME = "ta.uuid"
UUID_LEN = 32

def get_dirs(basedir):
    return [os.path.join(basedir, dir_) \
            for dir_ in os.listdir(basedir) \
            if os.path.isdir(os.path.join(basedir, dir_))]

def create_config(cmd_id_dir, uuid, process):
    param_type_dirs = get_dirs(cmd_id_dir)
    configs = []
    for param_type_dir in param_type_dirs:
        config = dict()
        config['target'] = TARGET
        config['params'] = dict()
        config['params']['uuid'] = uuid
        config['params']['seeds_dir'] = param_type_dir
        config['params']['process'] = process
        configs.append(config)
    return configs


def handle_process_dir(pdir):
    uuid_path = os.path.join(pdir, UUID_FILENAME)
    if not os.path.exists(uuid_path):
        log.error("uuid doesn't exist: {}".format(uuid_path))
        return
    with open(uuid_path) as f:
        uuid = f.read().strip('\n')

    # check proper size of uuid
    if not len(uuid) == UUID_LEN:
        log.error("we're expecting a uuid of size {}, ".format(UUID_LEN) +\
                  "this one is of size {}: {}".format(len(uuid), uuid_path))
        return

    # check if we can dehex uuid
    try:
        uuid.decode('hex')
    except:
        log.error("error hex-decoding uuid: {}".format(uuid))
        return

    cmd_id_dirs = get_dirs(pdir)
    configs = []
    for cmd_id_dir in cmd_id_dirs:
        configs.extend(create_config(cmd_id_dir, uuid, os.path.basename(pdir)))
    return configs

def store_config(dst_dir, config):
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    tokens = config['params']['seeds_dir'].split('/')
    param_types = tokens[-1]
    cmd_id = tokens[-2]
    process = tokens[-3]
    target  = tokens[-4]
    config_name = "{}_{}_{}_{}.json".format(target, process, cmd_id, param_types)
    with open(os.path.join(dst_dir, config_name), "w+") as f:
        json.dump(config, f, indent=2)

def main(config_dst_dir, seed_dir):
    seed_dir = os.path.abspath(seed_dir)
    # get all process directories
    process_dirs = get_dirs(seed_dir)
    #log.debug(process_dirs)
    configs = []
    for pdir in process_dirs:
        configs.extend(handle_process_dir(pdir))
    for config in configs:
        store_config(config_dst_dir, config)

def usage():
    print("Usage:\n\t{} <config_dst_dir> <seed_dir>".format(sys.argv[0]))

if __name__=="__main__":
    if len(sys.argv) < 3 or not os.path.isdir(sys.argv[1]) or \
            not os.path.isdir(sys.argv[2]):
        usage()
        sys.exit(0)
    main(sys.argv[1], sys.argv[2])
