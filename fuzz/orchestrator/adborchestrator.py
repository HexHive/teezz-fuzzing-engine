import os
import logging

from adb import adb
from fuzz import config
from .adbproc import AdbProc

log = logging.getLogger(__name__)


class AdbOrchestrator(AdbProc):

    def __init__(self, target_tee, port, device_id, log_dir):
        args = f"{target_tee} {port}"
        executable_path = os.path.join(config.TARGET_EXECUTOR_DIR,
                                       config.TARGET_EXECUTOR_NAME)
        super(AdbOrchestrator, self).__init__("executor", executable_path,
                                              args, device_id, log_dir)

        self.port = port

        # setup adb socket forwarding
        adb.forward(self.port, self.port, self.device_id)
        adb.forward(self.port+1, self.port+1, self.device_id)

        # check if executor is behaving correctly, will timeout otherwise
        self.log_recv_until("bind done")
