import argparse
import logging
from fuzz.runner.valdeprunner import ValDepRunner


FORMAT = (
    "%(asctime)s,%(msecs)d %(levelname)-8s " "[%(filename)s:%(lineno)d] %(message)s"
)
log = logging.getLogger(__name__)


def init_runner(args):
    runner = ValDepRunner(
        args.target_tee,
        args.port,
        args.config,
        args._in,
        args._out,
        args.device_id,
        args.reboot,
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

    # add flags
    parent_parser.add_argument(
        "-R",
        "--reboot",
        action="store_true",
        help="Reboot device after every sequence.",
    )

    # required arguments
    parent_parser.add_argument(
        "--in", required=True, dest="_in", help="Directory containing the seeds."
    )
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
    adb_target_parser.add_argument(
        "device_id",
        help="Android device id (adb devices).",
        default=None,
    )
    adb_target_parser.set_defaults(func=init_runner)

    # tcp target
    # tcp_target_parser = sp.add_parser('tcp', parents=[parent_parser])
    # tcp_target_parser.add_argument("--port",
    #                                type=int,
    #                                required=True,
    #                                help="Executor is listening on this port.")
    # tcp_target_parser.set_defaults(func=probe_value_dependencies)

    return parser


def main():
    logging.basicConfig(format=FORMAT, datefmt="%Y-%m-%d:%H:%M:%S", level=logging.DEBUG)

    arg_parser = setup_args()
    args = arg_parser.parse_args()

    runner = args.func(args)
    runner.run()


if __name__ == "__main__":
    main()
