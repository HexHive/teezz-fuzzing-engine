import unittest
import os
import logging
import tempfile
import shutil
import glob
import pickle

from fuzz.fmt_recovery import typify
from fuzz.fmt_recovery import sort
from fuzz.fmt_recovery import match
from fuzz.fmt_recovery import common_sequence
from fuzz.fmt_recovery import find_value_deps
from fuzz.fmt_recovery import gen_deps

DIR = os.path.dirname(os.path.abspath(__file__))

# test-global log configuration
logging.basicConfig(format='%(asctime)s,%(msecs)d %(levelname)-8s '
                    '[%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S')

# module-local log setup
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class OpteeSeedsTest(unittest.TestCase):

    DATADIR = os.path.join(DIR, "data", "optee")
    SINGLEDEP_DATA_DIR = "single_dep"
    KM_GEN_BEGIN_ABORT_DEL_DATA_DIR = "km_gen_begin_abort_del"
    KM_GENKEY_WITH_HAL_DIR = "km_genkey_with_hal"

    DEP_CHAINS_FILENAME = "dep_chains.pickle"
    DEPENDENCY_FILE = "dependencies.pickle"

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

    def setupData(self, _dir):
        self.datadir = os.path.join(self.tmpdir.name)
        log.debug(f"datadir: {self.datadir}")
        shutil.copytree(os.path.join(self.DATADIR, _dir),
                        os.path.join(self.datadir, _dir))
        return os.path.join(self.datadir, _dir)

    def tearDown(self):
        # rm -rf the tmpdir
        self.tmpdir.cleanup()

    @staticmethod
    def _typify(dir_):
        typify.typify("optee", dir_)

    @staticmethod
    def _common_sequence(dir_):
        common_sequence.common_sequence("optee", dir_)

    @staticmethod
    def _find_value_deps(dir_):
        find_value_deps.find_value_deps("optee", dir_)

    @staticmethod
    def _gen_deps(dir_):
        gen_deps.gen_deps(dir_)

    @staticmethod
    def _run_all(dir_):
        OpteeSeedsTest._typify(dir_)
        OpteeSeedsTest._common_sequence(dir_)
        OpteeSeedsTest._find_value_deps(dir_)
        OpteeSeedsTest._gen_deps(dir_)

    def test_typify(self):
        """ Test typify. """
        dir_ = os.path.join(self.setupData(self.SINGLEDEP_DATA_DIR), "0")
        data_files = glob.glob(f"{dir_}/*/*/*/param_*_data")
        self._typify(dir_)
        for data_file in data_files:
            if not os.path.isfile(f"{data_file}.types"):
                assert os.path.isfile(f"{data_file}.types"), \
                    f"{data_file}.types missing"

    def test_sorthal(self):
        # TODO: add hal sorting
        pass

    def test_match(self):
        # TODO: add hal matching
        pass

    def test_sz_off(self):
        # TODO: add tests to find size and offset fields
        pass

    def test_common_sequence(self):
        """ in this test we have a recording of the km ta where a response
        contains a keyblob that is used in the following request. """
        dir_ = os.path.join(self.setupData(self.SINGLEDEP_DATA_DIR), "0")
        self._typify(dir_)
        self._common_sequence(dir_)

        resp = os.path.join(dir_, "0", "0", "onleave", "param_1_data")
        req = os.path.join(dir_, "0", "1", "onenter", "param_0_data")

        resp_type_path = f"{resp}.types"
        with open(resp_type_path, "rb") as f:
            resp_type = pickle.load(f)

        req_type_path = f"{req}.types"
        with open(req_type_path, "rb") as f:
            req_type = pickle.load(f)

        req_off_sz, req_type_name = req_type.getAsList()[0]
        req_off, req_sz = req_off_sz

        resp_off_sz, resp_type_name = resp_type.getAsList()[0]
        resp_off, resp_sz = resp_off_sz

        assert req_off == 0, "req off wrong"
        assert req_sz == 4492, "req sz wrong"
        assert resp_off == 4, "resp off wrong"
        assert resp_sz == 4492, "resp sz wrong"

    def test_find_value_deps(self):
        dir_ = os.path.join(self.setupData(self.SINGLEDEP_DATA_DIR), "0")
        self._typify(dir_)
        self._common_sequence(dir_)
        self._find_value_deps(f"{dir_}")
        with open(os.path.join(dir_, self.DEP_CHAINS_FILENAME),
                  "rb") as f:
            dep_chain = pickle.load(f)
        assert len(dep_chain) == 1, "We expect one dependency here."

    def test_gen_deps(self):
        dir_ = os.path.join(self.setupData(self.SINGLEDEP_DATA_DIR), "0")
        self._typify(dir_)
        self._common_sequence(dir_)
        self._find_value_deps(dir_)
        self._gen_deps(dir_)
        with open(os.path.join(dir_, self.DEPENDENCY_FILE), "rb") as f:
            dep_chain = pickle.load(f)
        assert len(dep_chain) == 2, "We expect two requests here."
        assert len(dep_chain[1].value_dependencies
                   ) == 1, "We expect one dependency here"

    def test_km_gen_begin_abort_del(self):
        dir_ = os.path.join(self.setupData(self.KM_GEN_BEGIN_ABORT_DEL_DATA_DIR), "0")
        self._run_all(dir_)
        with open(os.path.join(dir_, self.DEPENDENCY_FILE), "rb") as f:
            dep_chain = pickle.load(f)
        import ipdb; ipdb.set_trace()
        dep_chain[1] # begin

    def test_km_genkey_with_hal(self):
        dir_ = self.setupData(self.KM_GENKEY_WITH_HAL_DIR)
        ioctl_dir = os.path.join(dir_, "ioctl")
        hal_dir = os.path.join(dir_, "hal")
        self._typify(ioctl_dir)

        sort.main('optee', ioctl_dir, hal_dir)
        for dirent in glob.glob(os.path.join(ioctl_dir, '*/*/on*/hal_*')):
            match.main('optee', dirent)

        key_params = os.path.join(ioctl_dir, "0", "0", "onenter", "param_0_data.types")

        with open(key_params, "rb") as f:
            key_params_types = pickle.load(f)

        key_blob = os.path.join(ioctl_dir, "0", "0", "onleave", "param_1_data.types")
        with open(key_blob, "rb") as f:
            key_blob_types = pickle.load(f)
        import ipdb; ipdb.set_trace()

        # TODO: add asserts for expected results
        # note that we currently look for onleave -> onenter deps
        # this breaks when a HAL functions uses a callback to for its return values
        # import ipdb; ipdb.set_trace()



if __name__ == '__main__':
    unittest.main()
