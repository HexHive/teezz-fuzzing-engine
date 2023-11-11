#!/usr/bin/env python3
import argparse
import os
import re


def setup_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("infolder", help="Input folder of crash log files")
    parser.add_argument("outfolder", help="Output folder of unique crashes")

    return parser


def extract_stack_traces(crash_log_file):
    """ Extract stack traces from crashes logged to `/dev/hisi_teelog`..

    Crashes look like this:
    ```
    =========== The PC which result in abort is task_keymaster(get_key_param+0x00000048)=======
    ====backtraces:
            #[0] task_keymaster(km_import_key+0x00000034)
            #[1] task_keymaster(TA_InvokeCommandEntryPoint+0x00000180)
            #[2] task_keymaster(tee_task_entry+0x000001c8)
            #[3] Wrong Address
    ==============Task Crash======================================
    ```

    The regex used in this function matches this pattern.
    """

    with open(crash_log_file) as f:
        log_text = [line.strip() for line in f.readlines() if line.strip()]
        log_text = "\n".join(log_text)

        regex = r"The PC which.*?"
        regex += r"====backtraces:\n"
        regex += r"(.*?)\n"
        regex += r"==============Task Crash"

        stack_traces = re.findall(regex, log_text, re.DOTALL)

    return stack_traces


def main():
    arg_parser = setup_args()
    args = arg_parser.parse_args()

    stack_traces = []
    crash_log_files = []
    for r, _, files in os.walk(args.infolder):
        for f in files:
            log_path = os.path.join(r, f)
            crash_log_files.append(log_path)
            stack_traces.extend(extract_stack_traces(log_path))

    unique_stack_traces = list(set(stack_traces))
    out_path = os.path.join(args.outfolder, "crash_report.txt")

    if not os.path.isdir(args.outfolder):
        os.mkdir(args.outfolder)

    with open(out_path, "w+") as report:
        report.write(f"Total unique crashes: {len(unique_stack_traces)}\n")
        report.write(f"Total crash log files: {len(crash_log_files)}\n")
        report.write("-----------------------\n")
        for trace in unique_stack_traces:
            report.write("Log files of crashes:\n")
            report.write(trace)
            report.write("\n-----------------------\n")

    print(f"Total unique crashes: {len(unique_stack_traces)}")

if __name__ == '__main__':
    main()

