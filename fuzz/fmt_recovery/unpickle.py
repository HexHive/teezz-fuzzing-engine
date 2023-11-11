import sys
import os
from hexdump import hexdump
import pickle
from pprint import pprint


if len(sys.argv) < 2:
    print("Usage:\n\n{} <file.pickle>".format(sys.argv[0]))
    sys.exit(0)

with open(sys.argv[1], "rb") as f:
    # import ipdb; ipdb.set_trace()
    data = pickle.load(f)
    print(data)

import ipdb

ipdb.set_trace()
