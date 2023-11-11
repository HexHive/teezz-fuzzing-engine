#!/usr/bin/env python
import sys
import os
import json
import subprocess
import logging
import shutil
import aggregate_kernel


logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

TMPDIR = os.path.join("/tmp", "teezz_tmp")
EVALDIR = os.path.join("/tmp", "teezz_eval")
FUZZCFG = "fuzz.cfg"
TZLOGGERLOG = "tzlogger.log"


def aggregate_crashes(basedir):
    crash_dirs = os.listdir(os.path.join(basedir, "crash"))
    if len(crash_dirs) != 1:
        log.error("len(crash_dirs) > 1: {}".format(crash_dirs))
    crash_count = len([d for d in os.listdir(os.path.join(basedir, "crash", crash_dirs[0])) if "run" not in d])
    return crash_count


def aggregate_kernel_log(basedir, cfg):
    tzlog = os.path.join(basedir, TZLOGGERLOG)
    stats = aggregate_kernel.main(cfg["tee"], tzlog)

    # TODO: duration not part of fuzz.cfg yet, fix this once it's there
    stats["duration"] = 28800  # duration (sec)
    # TODO: untrusted application not part of fuzz.cfg yet, fix this once it's there
    stats["ua"] = "<placeholder_for_ua>"


    # TODO: check reproducible crash count
    crash_count = aggregate_crashes(basedir)

    out = "{};{};{};{};{};{};{};{};{};{};{}\n".format(
        cfg["tee"],
        stats["ua"],
        stats["duration"],

        stats["ioctl_total"] / float(stats["duration"]),
        stats["ioctl_total"],
        stats["ioctl_success"],
        stats["ioctl_total"] - stats["ioctl_success"],

        stats["smc_total"],
        stats["smc_total"] / float(stats["ioctl_total"]),

        stats["smc_valid"],
        crash_count,
    )

    print(out)


def move_eval_data(basedir, cfg):
    tee = cfg["tee"]
    mutation = cfg["mutation"]
    modelaware = "modelaware" if cfg["modelaware"] else "modelunaware"
    # TODO: the untrusted applications is not part of fuzz.cfg yet, get it from there once it's included
    uas = os.listdir(os.path.join(basedir, "crash"))
    if len(uas) != 1:
        log.error("Multiple target TAs.")
        sys.exit(1)
    dst_dir = os.path.join(EVALDIR, tee, mutation, modelaware, uas[0])
    shutil.move(basedir, dst_dir)
    return dst_dir

"""
Provide a file with a json list, i.e.:

[
  "/home/tzzz/eval/dumb/tc/2020-01-09/km",
  "/home/tzzz/eval/dumb/tc/2020-01-09/gk",
  "/home/tzzz/eval/dumb/tc/2020-01-09/fp"
]

"""

def main(host, remote_paths_file):
    with open(remote_paths_file) as f:
        remote_paths = json.load(f)

    for remote_path in remote_paths:
        log.info("retrieving {} from {}".format(remote_path, host))
        cmd = "tar cfz /tmp/eval.tar.gz --directory={} .".format(remote_path)
        if subprocess.call(["ssh", host, cmd]):
            log.error("ssh error")
            sys.exit(1)
        if subprocess.call(["scp", "{}:/tmp/eval.tar.gz".format(host), "/tmp/"]):
            log.error("scp error")
            sys.exit(1)
        if not os.path.isdir(TMPDIR):
            os.mkdir(TMPDIR)
        if subprocess.call(["tar", "xfz", "/tmp/eval.tar.gz", "--directory={}".format(TMPDIR)]):
            log.error("tar error")
            sys.exit(1)

        cfg_path = os.path.join(TMPDIR, FUZZCFG)
        tmpbasedir = os.path.dirname(cfg_path)
        with open(cfg_path) as f:
            cfg = json.load(f)
        basedir = move_eval_data(tmpbasedir, cfg)
        aggregate_kernel_log(basedir, cfg)


def usage():
    print("{} <ssh_host> <eval_json>".format(sys.argv[0]))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        usage()
        exit(1)

    main(sys.argv[1], sys.argv[2])
