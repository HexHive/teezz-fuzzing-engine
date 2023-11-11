import argparse
import logging
from fuzz.runner.triagerunner import TriageRunner


FORMAT = (
    "%(asctime)s,%(msecs)d %(levelname)-8s " "[%(filename)s:%(lineno)d] %(message)s"
)
log = logging.getLogger(__name__)


def fuzz_adb_target(args):
    runner = TriageRunner(
        args.target_tee,
        args.port,
        args.config,
        args._out,
        args.device_id,
        reboot=args.reboot,
    )
    return runner


def fuzz_tcp_target(args):
    runner = TriageRunner(
        args.target_tee, args.port, args.config, args._out, reboot=args.reboot
    )

    return runner


def setup_args():
    """Returns an initialized argument parser."""
    parser = argparse.ArgumentParser()

    parent_parser = argparse.ArgumentParser(add_help=False)
    # add positional arguments
    parent_parser.add_argument("target_tee", help="Target tee (optee, qsee or tc).")
    parent_parser.add_argument(
        "config", type=argparse.FileType("r"), help="Target config file."
    )
    parent_parser.add_argument("crash_seq_dir", help="Crashing seq dir.")

    # add flags
    parent_parser.add_argument(
        "-R",
        "--reboot",
        action="store_true",
        help="Reboot device after every sequence.",
    )

    # required arguments
    parent_parser.add_argument(
        "--out", required=True, dest="_out", help="Directory used to write output to."
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
    adb_target_parser.add_argument("device_id", help="Android device id (adb devices).")
    adb_target_parser.set_defaults(func=fuzz_adb_target)

    # tcp target
    tcp_target_parser = sp.add_parser("tcp", parents=[parent_parser])
    tcp_target_parser.add_argument(
        "--port", type=int, required=True, help="Executor is listening on this port."
    )
    tcp_target_parser.set_defaults(func=fuzz_tcp_target)

    return parser


def main():
    logging.basicConfig(format=FORMAT, datefmt="%Y-%m-%d:%H:%M:%S", level=logging.DEBUG)

    arg_parser = setup_args()
    args = arg_parser.parse_args()

    runner = args.func(args)
    runner.triage(args.crash_seq_dir)


if __name__ == "__main__":
    main()
