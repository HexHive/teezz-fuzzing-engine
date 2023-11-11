import unittest
import os
import tempfile


from fuzz.const import TEEID
from fuzz.adbproc.executor import Executor
from fuzz import config
from adb import adb


class ExecutorTest(unittest.TestCase):

    def setUp(self):
        pass

    def test_executor_spawned(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            device_id = adb.get_device_ids()[0]
            self.executor = Executor(TEEID.TC, 4243, device_id, tmpdir)
            out = adb.pgrep(config.HOST_EXECUTOR_NAME, device_id=device_id)
            assert out, "Executor process not found."
            assert os.path.exists(self.executor.log_path)


if __name__ == '__main__':
    unittest.main()
