#!/usr/bin/env python

import sys
import os
import logging
import re
from datetime import timedelta

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__file__)

MAX_DELTA = timedelta(minutes=30)


def check_line_format(line):
    """ check if line has proper format and return its timedelta, return None otherwise. """

    # we skip lines with malformed input
    if '0:0:0:0;0x0;0x0;0x0;0x0;0x0' in line:
        return None
    if not re.match(r'\d{1,2}:\d{1,2}:\d{1,2}:', line):
        return None

    split_line = line.split(';')
    if len(split_line) != 6:
        log.error("malformed line: {}".format(line))
        return None
    try:
        time_components = split_line[0].split(':')
        if len(time_components) != 4:
            log.error("malformed line: {}".format(line))
            return None
    except ValueError:
        log.error("malformed line: {}".format(line))
        return None

    hh, mm, ss = [int(i) for i in time_components[:3]]
    delta = timedelta(hours=hh, minutes=mm, seconds=ss)
    return delta


def main(tzlog, timespan, out_dir):

    # we collect log lines until ellapsed_time reaches required_total_time
    required_total_time = timedelta(hours=timespan)
    ellapsed_time = timedelta()

    if not os.path.exists(out_dir):
        os.mkdir(out_dir)

    delta = None

    with open(tzlog) as log_file, open(os.path.join(out_dir, "{}.{}h".format(os.path.basename(tzlog), timespan)), 'w') as dest:

        for cnt, line in enumerate(log_file):
            prev_delta = delta
            delta = check_line_format(line)

            if not delta:
                # skip this line because it is malformed
                continue

            if prev_delta and delta:
                # we have a previous delta, do some sanity checks
                if abs(prev_delta.seconds - delta.seconds) > (15 * 60):
                    # if the gap is greater than 15min, we assume the fuzzing stopped unexpectedly
                    # and was reset manually. The gap resulting from the manual reset is not considered.
                    # Therefore, we skip it here.
                    continue
                elif prev_delta > delta:
                    # either the target reset the time and is off by a few seconds
                    # or we entered the next day
                    if prev_delta.seconds - delta.seconds > (23 * 60 * 60):
                        # we entered the next day: timestamps are >23h apart
                        ellapsed_time += ((timedelta(hours=24)+delta) - prev_delta)
                    elif prev_delta.seconds - delta.seconds > 2:
                        import ipdb; ipdb.set_trace()
                        # we tolerate inaccuracies of up to 2 secons here
                        assert False, "This is bad. The timestamps need to be linear, otherwise we drop all the gaps where" \
                                      "for some reason the time was reset (probably a reboot) and therefore render the" \
                                      "measured logs unusable. Make the fuzzer synchronize the time with the host to have" \
                                      "proper timestamps!"
                else:
                    # update elapsed time
                    ellapsed_time += (delta - prev_delta)

            # as long as we have not reached the required time, we copy each line to the filtered log
            dest.write(line)

            if ellapsed_time >= required_total_time:
                break

        log.info('Total time: ' + str(ellapsed_time))


def usage():
    print("{} <tzlog> <timespan_in_hours> <out/>".format(sys.argv[0]))
    return


if __name__ == "__main__":
    if len(sys.argv) < 4 or not os.path.exists(sys.argv[1]):
        usage()
        sys.exit(0)

    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
