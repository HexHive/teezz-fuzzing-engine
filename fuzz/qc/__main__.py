import os
import sys
import argparse
import pickle

from pprint import pprint
from .qsee.qseedata import QseecomSendCmdReq


def setup_args():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(help="Help for subcommands.",
                                       dest="subparser")

    #serialize_parser = subparsers.add_parser("serialize",
    #                                         help="serialize help")
    deserialize_parser = subparsers.add_parser("deserialize",
                                               help="serialize help")

    deserialize_parser.add_argument("raw_req_dir")
    #serialize_parser.add_argument("pickled_ctx_path")

    return parser


def main():
    arg_parser = setup_args()
    args = arg_parser.parse_args()

    if "deserialize" == args.subparser:
        # handle deserialize
        if not os.path.isdir(args.raw_req_dir):
            print("Need a dir.")
            sys.exit()
        req = QseecomSendCmdReq.deserialize_raw_from_path(args.raw_req_dir)
        import ipdb
        ipdb.set_trace()
        print(req)
    else:
        arg_parser.print_help()


if __name__ == "__main__":
    main()
