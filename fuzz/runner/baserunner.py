import subprocess
import os
import logging
import time
import json

from fuzz.const import TEEID
from fuzz.runner.runner import Runner
from fuzz.runner.seqrunner import SequenceRunner
from fuzz.orchestrator.adborchestrator import AdbOrchestrator
from fuzz.runner.sessionmeta import build_session_meta
from fuzz.utils import mkdir_p
from adb import adb
from fuzz.config import HOST_EXECUTOR_PATH, TARGET_EXECUTOR_PATH
from fuzz.stats import STATS

log = logging.getLogger(__file__)


class FuzzEvent(object):
    START_RUN = "START_RUN"
    END_RUN = "END_RUN"
    REBOOT = "REBOOT"
    UNRECOVERABLE = "UNRECOVERABLE"


class DeviceResetException(Exception):
    pass


class BaseRunnerException(Exception):
    pass


class BaseRunner(object):
    def __init__(
        self, target_tee, port, config, out_dir, device_id=None, reboot=False
    ):
        self._device_id = device_id
        self._target_tee = target_tee
        self._port = port
        self._config = json.load(config)
        # we use tee- and device-specific subfolders
        self._out_dir = os.path.join(
            out_dir,
            self._target_tee,
            self._device_id if self._device_id else "tcp",
        )
        self._queue_dir = os.path.join(self._out_dir, "queue")
        self._crashes_dir = os.path.join(self._out_dir, "crashes")
        self._timeouts_dir = os.path.join(self._out_dir, "timeouts")
        self._cov_dir = os.path.join(self._out_dir, "cov")

        self._queue_id = (
            0
            if not os.path.isdir(self._queue_dir)
            else len(os.listdir(self._queue_dir))
        )

        self._crash_id = (
            0
            if not os.path.isdir(self._crashes_dir)
            else len(os.listdir(self._crashes_dir))
        )

        self._hang_id = (
            0
            if not os.path.isdir(self._timeouts_dir)
            else len(os.listdir(self._timeouts_dir))
        )

        self._cov_id = (
            0
            if not os.path.isdir(self._cov_dir)
            else len(os.listdir(self._cov_dir))
        )

        self.is_prev_factory_reset = False
        self.reboot = reboot

        self._session_meta = build_session_meta(self._target_tee, self._config)

        if self._device_id:
            self.check_device()
            # we use the device id to detect if we are targeting a device via
            # adb and spin up the executor on the device here
            self._executor = AdbOrchestrator(
                self._target_tee, self._port, self._device_id, self._out_dir
            )
        self._seqrunner = SequenceRunner("127.0.0.1", self._port)
        self._runner = Runner("127.0.0.1", self._port + 1, self._session_meta)

        mkdir_p(self._out_dir)

    def _get_seed_class(self, target_tee: str):
        if target_tee == TEEID.OPTEE or target_tee == TEEID.BEANPOD:
            from fuzz.optee.opteedata import TeeIoctlInvokeArg as cls
        elif target_tee == TEEID.TC:
            from fuzz.huawei.tc.tcdata import TC_NS_ClientContext as cls
        elif target_tee == TEEID.QSEE:
            from fuzz.qc.qsee.qseedata import QseecomSendCmdReq as cls
        else:
            raise BaseRunnerException(f"Unknown TEE {target_tee}")
        return cls

    def reset_device(self):
        """reset the device"""

        assert self._executor is not None, ""
        # trigger clean up of sequence runner
        del self._seqrunner
        # trigger clean up of executor
        del self._executor

        hard_reset_ctr = 0
        while True:
            try:
                # reboot the device
                adb.reboot(self._device_id)

                self.check_device()

                # sync time between device and host
                adb.set_date(self._device_id)
                break
            except Exception as e:
                log.error(e)
                if hard_reset_ctr >= 3:
                    raise
                log.info("Device is inresponsive. Performing hard reset.")
                STATS["#hardresets"] += 1
                cmd = [
                    "ssh",
                    "resetpi-epfl",
                    "/home/pi/teezzhardreset/longpress.sh",
                ]
                if subprocess.call(cmd):
                    log.error(
                        "Hard reset failed for {}.".format(self._device_id)
                    )
                hard_reset_ctr += 1
        return

    @staticmethod
    def check_device_root_working(device_id):
        p = adb.subprocess_privileged("whoami", device_id)
        if not p:
            return False
        stdout, stderr = p.communicate()
        return b"root" in stdout

    @staticmethod
    def is_data_tmpfs(device_id):
        """True if data/ mounted as tmpfs, False otherwise"""
        out, _ = adb.execute_command("mount", device_id)
        ret = False
        for line in out.split(b"\n"):
            if b"on /data " in line and b"type tmpfs" in line:
                ret = True
                break
        return ret

    def check_device(self):
        """We check all the requirements to run TEEzz successfully here."""

        ret = True
        adb.is_device_ready(self._device_id)

        # make sure we did not boot to recovery
        if adb.is_recovery(self._device_id) or self.is_data_tmpfs(
            self._device_id
        ):
            # The phone booted to recovery mode or the data partition is mounted
            # as a tmpfs. This usually means that the regular system is corrupt.
            # We try to wipe the data partition here to repair the system
            self.factory_reset()
            # are we still in recovery mode?
            if adb.is_recovery(self._device_id):
                # still recovery mode, we are screwed
                raise DeviceResetException("Cannot repair device.")
            # fix root access
            self.root_phone()
            # deploy TEEzz
            log.debug(
                adb.push(
                    HOST_EXECUTOR_PATH, TARGET_EXECUTOR_PATH, self._device_id
                )
            )

        ctr = 0
        while not BaseRunner.check_device_root_working(self._device_id):
            log.warning("Cannot connect as root.")
            ctr += 1
            time.sleep(5)
            if ctr > 10:
                ret = False
                break

        return ret

    def root_phone(self):
        """deploy magisk via recovery."""

        adb.reboot_recovery(self._device_id)
        adb.is_device_ready(self._device_id)

        ROOT_ARCHIVE = "root_archive"
        MAGISK_DB = "magisk_db"

        if not ROOT_ARCHIVE in self._config:
            raise BaseRunnerException(f"{ROOT_ARCHIVE} not found in config.")
        if not MAGISK_DB in self._config:
            raise BaseRunnerException(f"{MAGISK_DB} not found in config.")

        root_archive_path = self._config[ROOT_ARCHIVE]

        log.debug(f"Applying {root_archive_path}")
        # FIXME: this is just a hotfix for the Nexus5X where it needs some time
        # when it boots to recovery before the following commands succeed.
        # Maybe there is a getprop property that indicates when the phone is
        # ready?
        time.sleep(10)
        log.debug(adb.push(root_archive_path, "/tmp/", self._device_id))
        out, _ = adb.execute_command(
            f"twrp install /tmp/{os.path.basename(root_archive_path)}",
            self._device_id,
            timeout=120,
        )
        log.debug(out)

        # We need to change the policy for the shell user, too.
        # The default one does not grant us root access.
        magisk_db_path = self._config[MAGISK_DB]
        log.debug(f"Applying magisk.db from '{magisk_db_path}'")
        log.debug(
            adb.push(magisk_db_path, "/data/adb/magisk.db", self._device_id)
        )

        log.debug("Rebooting to system")
        adb.reboot(self._device_id)

        adb.is_device_ready(self._device_id)

        if adb.is_recovery(self._device_id):
            # we are still in recovery mode, let's try to reboot one more time
            log.debug("Second attempt rebooting to system")
            adb.reboot(self._device_id)
            adb.is_device_ready(self._device_id)
            if adb.is_recovery(self._device_id):
                raise adb.DeviceUnresponsiveException(
                    "Device should have booted into system, not recovery."
                )

        if not BaseRunner.check_device_root_working(self._device_id):
            raise adb.DeviceUnresponsiveException("Cannot root device.")

        log.debug("Success! The phone is rooted!")
        return

    def factory_reset(self):
        """factory reset the device"""

        STATS["#factoryresets"] += 1
        if not adb.is_recovery(self._device_id):
            adb.reboot_recovery(self._device_id)

        adb.is_device_ready(self._device_id)

        log.info("factory reset")
        adb.execute_command("twrp wipe factoryreset", self._device_id)
        time.sleep(5)

        log.info("rebooting")
        adb.reboot(self._device_id)

        # some exta time for the system to come up out of a factory reset
        time.sleep(30)

        adb.is_device_ready(self._device_id)

        return

    def format_userdata(self):
        """reformat the userdata partition."""
        out, _ = adb.execute_command(
            "twrp unmount data", self._device_id, timeout=10
        )
        out, _ = adb.execute_command(
            "readlink -f /dev/block/by-name/userdata",
            self._device_id,
            timeout=10,
        )
        partition_path = out.strip().decode()
        out, _ = adb.execute_command(
            "blockdev --getsize64 {}".format(partition_path),
            self._device_id,
            timeout=10,
        )
        nbytes = int(out.strip().decode())
        out, _ = adb.execute_command(
            "blockdev --getbsz {}".format(partition_path),
            self._device_id,
            timeout=10,
        )
        blocksz = int(out.strip().decode())
        nblocks = nbytes // blocksz

        out, _ = adb.execute_command(
            'echo "y" | mke2fs -t ext4 -b {} {} {}'.format(
                blocksz, partition_path, nblocks
            ),
            self._device_id,
            timeout=10,
        )

        out, _ = adb.execute_command(
            "ee2fsdroid -e -S /file_contexts -a /data {}".format(
                partition_path
            ),
            self._device_id,
            timeout=10,
        )
