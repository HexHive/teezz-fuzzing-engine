import struct
import os
import errno
import subprocess

from typing import List


def find_files(where: str, what: str) -> List[str]:
    cmd = ["find", where, "-regex", what, "-type", "f"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = p.stdout.read()
    p.wait()
    p.stdout.close()
    p.stderr.close()
    if not d:
        return []
    paths = [line for line in d.split(b"\n") if line]
    return paths


def find_dirs(where, what):
    cmd = ["find", where, "-iname", what, "-type", "d"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d = p.stdout.read()
    p.wait()
    p.stdout.close()
    p.stderr.close()
    if not d:
        return []
    paths = [line for line in d.split(b"\n") if line]
    return paths


def p8(v):
    return struct.pack("<B", v)


def p16(v):
    return struct.pack("<H", v)


def p32(v):
    return struct.pack("<I", v)


def p64(v):
    return struct.pack("<Q", v)


def u8(v):
    return struct.unpack("<B", v)[0]


def u16(v):
    return struct.unpack("<H", v)[0]


def u32(v):
    return struct.unpack("<I", v)[0]


def us32(v):
    """unpack signed 32"""
    return struct.unpack("<i", v)[0]


def u64(v):
    return struct.unpack("<Q", v)[0]


# thx https://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
