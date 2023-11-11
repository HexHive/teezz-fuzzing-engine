#!/usr/bin/env python3
import struct
import sys
import binascii

def usage():
    print("{} <name> <path> [sha256hexdigest]\n\tExample: {} secure_storage /system/bin/secure_storage".format(sys.argv[0], sys.argv[0]))

if len(sys.argv) < 3:
    usage()
    sys.exit(0)

name = sys.argv[1]
path = sys.argv[2]

out = b""
out += struct.pack("<I", len(path))
out += path.encode()
out += struct.pack("<I", 0)

if len(sys.argv) > 3:
    sha256digest = binascii.unhexlify(sys.argv[3].replace(" ", ""))
    out += sha256digest


with open("login.blob.{}".format(name), "wb") as f:
    f.write(out)

sys.exit(0)
