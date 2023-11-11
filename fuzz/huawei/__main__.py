import os
import argparse
import pickle

from pprint import pprint
from .tc.tcdata import TC_NS_ClientContext


def store_dict(d, dir):
    """ Stores values of dict `d` in directory `dir` named after their keys.

        This function assumes all keys to be `str`s and values to be `bytes`.
    """

    for k, v in d.items():
        filename = os.path.join(dir, k)
        with open(filename, "wb") as f:
            f.write(v)


def setup_args():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(help="Help for subcommands.",
                                       dest="subparser")

    serialize_parser = subparsers.add_parser("serialize",
                                             help="serialize help")
    deserialize_parser = subparsers.add_parser("deserialize",
                                               help="serialize help")

    deserialize_parser.add_argument("raw_ctx_path")
    serialize_parser.add_argument("pickled_ctx_path")

    parser.add_argument("-o", "--out", dest="_out", help="Output directory.")
    return parser


def main():
    arg_parser = setup_args()
    args = arg_parser.parse_args()

    if "serialize" == args.subparser:
        # handle serialize
        raw_data_dict = TC_NS_ClientContext \
                        .serialize_raw_from_path(args.pickled_ctx_path)
        if args._out:
            # save to dir if `_out` is set, print to stdout otherwise
            if os.path.isdir(args._out):
                store_dict(raw_data_dict, args._out)
            else:
                print(f"Directory \"{args._out}\" does not exist.")
        else:
            pprint(raw_data_dict)
    elif "deserialize" == args.subparser:
        # handle deserialize
        ctx = TC_NS_ClientContext.deserialize_raw_from_path(args.raw_ctx_path)
        if args._out:
            # save to dir if `_out` is set, print to stdout otherwise
            if os.path.isdir(args._out):
                filepath = os.path.join(args._out, "TC_NS_ClientContext.pickle")
                with open(filepath, "wb") as f:
                    pickle.dump(ctx, f)
            else:
                print(f"Directory \"{args._out}\" does not exist.")
        else:
            print(ctx)
    else:
        arg_parser.print_help()


if __name__ == "__main__":
    main()

