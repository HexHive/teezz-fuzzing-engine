import argparse
import logging
from fuzz.runner.fuzzrunner import FuzzRunner


FORMAT = (
    "%(asctime)s,%(msecs)d %(levelname)-8s "
    "[%(filename)s:%(lineno)d] %(message)s"
)
log = logging.getLogger(__name__)


def fuzz_adb_target(args):
    runner = FuzzRunner(
        args.target_tee,
        args.port,
        args.config,
        args._in,
        args._out,
        args.mutation_engine,
        args.modelaware,
        args.device_id,
        args.reboot,
    )
    return runner


def fuzz_tcp_target(args):
    runner = FuzzRunner(
        args.target_tee,
        args.port,
        args.config,
        args._in,
        args._out,
        args.mutation_engine,
        args.modelaware,
        reboot=args.reboot,
        cov_enabled=args.coverage,
    )
    return runner


def setup_args():
    """Returns an initialized argument parser."""
    parser = argparse.ArgumentParser()

    parent_parser = argparse.ArgumentParser(add_help=False)
    # add positional arguments
    parent_parser.add_argument(
        "target_tee", help="Target tee (optee, qsee or tc)."
    )
    parent_parser.add_argument(
        "config", type=argparse.FileType("r"), help="Target config file."
    )

    # add flags
    parent_parser.add_argument(
        "-M",
        "--modelaware",
        action="store_true",
        help="Set this flag for api modelaware " "fuzzing/triaging.",
    )
    parent_parser.add_argument(
        "-R",
        "--reboot",
        action="store_true",
        help="Reboot device after every sequence.",
    )
    parent_parser.add_argument(
        "-C",
        "--coverage",
        action="store_true",
        help="Target indicates new coverage for run.",
    )

    # required arguments
    parent_parser.add_argument(
        "-m",
        "--mutation_engine",
        required=True,
        help="Mutation engine (nop, dumb or format).",
    )
    parent_parser.add_argument(
        "--in",
        required=True,
        dest="_in",
        help="Directory containing the seeds.",
    )
    parent_parser.add_argument(
        "--out",
        required=True,
        dest="_out",
        help="Directory used to write output to.",
    )

    # optional arguments
    parent_parser.add_argument(
        "-d", "--duration", type=int, help="Duration of fuzzing in seconds."
    )
    parent_parser.add_argument(
        "-n", "--nruns", type=int, help="Number of requests."
    )

    sp = parser.add_subparsers()

    # adb target
    adb_target_parser = sp.add_parser("adb", parents=[parent_parser])
    adb_target_parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Port for adb forward for multiple fuzzer " "instances.",
    )
    adb_target_parser.add_argument(
        "device_id", help="Android device id (adb devices)."
    )
    adb_target_parser.set_defaults(func=fuzz_adb_target)

    # tcp target
    tcp_target_parser = sp.add_parser("tcp", parents=[parent_parser])
    tcp_target_parser.add_argument(
        "--port",
        type=int,
        required=True,
        help="Executor is listening on this port.",
    )
    tcp_target_parser.set_defaults(func=fuzz_tcp_target)

    return parser


def main():
    logging.basicConfig(
        format=FORMAT, datefmt="%Y-%m-%d:%H:%M:%S", level=logging.DEBUG
    )

    arg_parser = setup_args()
    args = arg_parser.parse_args()

    runner = args.func(args)

    if args.duration:
        runner.runt(args.duration)
    elif args.nruns:
        runner.runs(args.nruns)
    else:
        print("need either duration or nruns")


if __name__ == "__main__":
    main()
