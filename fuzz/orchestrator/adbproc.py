import logging
import os
import signal
import shutil
import glob
from subprocess import TimeoutExpired
from threading import Thread

from fuzz.utils import mkdir_p
from adb import adb

log = logging.getLogger(__name__)


class AdbProcExcpetion(Exception):
    """ Exceptions related to the `AdbProc` class. """
    pass


class AdbProc(object):
    def __init__(self, name, executable_path, args, device_id, log_dir):

        self.name = name
        self.executable_path = executable_path
        self.executable_name = os.path.basename(executable_path)
        self.args = args
        self.device_id = device_id
        self.log_path = os.path.join(log_dir, f"{self.name}.log")
        self.pid_path = os.path.join(log_dir, f"{self.name}.pid")

        # check if the executor executable is present
        if not adb.path_exists(f"{self.executable_path}", self.device_id):
            # log.debug("AdbProc not found on target device. Pushing it...")
            # log.debug(adb.push(os.path.join(HOST_EXECUTOR_DIR,
            #                                 HOST_EXECUTOR_NAME),
            #                   self.TARGET_EXECUTOR_PATH, self.device_id))
            raise AdbProcExcpetion("AdbProc not found "
                                   f"({self.executable_path})")

        # does our log directory exist?
        if not os.path.exists(log_dir):
            mkdir_p(log_dir)

        # kill the old process if still running
        self._kill()

        # start the adb process
        self._adb_proc = adb.subprocess_privileged(f"{executable_path} {args}",
                                                   self.device_id)

        # does this log file already exists? if so, rotate log
        if os.path.exists(self.log_path):
            # log file exists, we need to rotate
            existing_logs = glob.glob(
                os.path.join(log_dir, f"{os.path.basename(self.log_path)}.*"))
            # the suffix of these logs should be a number
            log_ids = [int(log.split(".")[-1]) for log in existing_logs]
            if log_ids:
                log_ids.sort()
                new_id = log_ids[-1] + 1
            else:
                new_id = 1
            shutil.move(self.log_path, f"{self.log_path}.{new_id}")

        # logging thread
        self.logf = open(self.log_path, "ab")
        self.logging_thread = Thread(target=self.log_to_file,
                                     args=(self._adb_proc.stdout, self.logf))
        self.logging_thread.daemon = True  # thread dies with the program
        self.logging_thread.start()

    def __del__(self):
        self.logf.close()
        self._adb_proc.kill()
        self._adb_proc.stdout.close()
        self._adb_proc.stderr.close()
        self._adb_proc.stdin.close()
        self._adb_proc.wait()

    def _kill(self):
        """ Kill the process on the device using its path and pidof. """
        pids_str = adb.pidof(self.executable_path, self.device_id)
        pids = [int(pid_str) for pid_str in pids_str.split(b" ") if pid_str]
        for pid in pids:
            out, _ = adb.cat_file(f"/proc/{pid}/cmdline", self.device_id)
            if self.executable_path in out.decode():
                adb.kill(pid, self.device_id)

    def log_recv_until(self, s, timeout=5):
        signal.signal(signal.SIGALRM, AdbProc.sig_unexpected_behavior)
        signal.alarm(timeout)
        with open(self.log_path, "rb") as logf:
            out = b""
            while s not in out.decode():
                out += logf.readline()
        signal.alarm(0)

    @staticmethod
    def sig_unexpected_behavior(signum, frame):
        raise TimeoutExpired("executor", 5)

    @staticmethod
    def log_to_file(out, logfile):
        try:
            for line in iter(out.readline, ''):
                logfile.write(line)
                logfile.flush()
        except ValueError:
            # We expect the logfile to be closed from another thread
            pass
