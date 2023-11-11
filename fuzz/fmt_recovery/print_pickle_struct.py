#!/usr/bin/env python3
import sys
import os
ROOT=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
TZZZ_ROOT=os.path.abspath(os.path.join(ROOT, ".."))
sys.path.append(TZZZ_ROOT)
import pickle

from StructDictClass import StructDict

def runTest(x):
    print('')
    sd_loaded = pickle.load(open(x, "rb"))
    print(sd_loaded.__str__())
    #ol = sd_loaded.getAsList()
    #for elem in ol:
    #    print(elem)

if __name__ == '__main__':
    if(len(sys.argv) != 2):
        print("{} <filename>".format(sys.argv[0]))
    runTest(sys.argv[1])
