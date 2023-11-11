import logging

from fuzz import config
from .adbproc import AdbProc


log = logging.getLogger(__name__)


class TzLog(AdbProc):

    def __init__(self, device_id, log_dir):
        args = f"{config.TARGET_TZLOG_PATH}"
        executable_path = "/system/bin/cat"
        super(TzLog, self).__init__("tzlog", executable_path, args,
                                    device_id, log_dir)
