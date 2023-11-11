import unittest
import logging
import os
import tempfile

from tc.tcdata import TC_NS_ClientContext

TC_TEST_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TC_TEST_DATA_DIR = os.path.join(TC_TEST_BASE_DIR, "data")
TC_TEST_SEED_DIR = os.path.join(
    TC_TEST_DATA_DIR, "km_onenter")

# test-global log configuration
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s '
                    '[%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S')

# module-local log setup
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class TcDataTest(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        log.debug(f"tmpdir: {self.tmpdir.name}")

    def test_serialization(self):
        ctx = TC_NS_ClientContext.deserialize_raw_from_path(TC_TEST_SEED_DIR)
        # buf = TC_NS_ClientContext.serialize(ctx)
        TC_NS_ClientContext.serialize_obj_to_path(ctx, self.tmpdir.name)
        newctx = TC_NS_ClientContext.deserialize_raw_from_path(self.tmpdir.name)
        assert ctx.uuid == newctx.uuid
        assert ctx.session_id == newctx.session_id
        assert ctx.cmd_id == newctx.cmd_id
        assert ctx.code == newctx.code
        assert ctx.origin == newctx.origin
        assert ctx.method == newctx.method
        assert ctx.mdata == newctx.mdata
        assert ctx.param_types == newctx.param_types
        assert ctx.started == newctx.started

    def tearDown(self):
        self.tmpdir.cleanup()


if __name__ == '__main__':
    unittest.main()
