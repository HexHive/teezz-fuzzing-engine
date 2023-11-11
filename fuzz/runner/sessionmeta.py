import codecs
import logging

from fuzz.utils import p8, p32
from fuzz.const import TEEID

log = logging.getLogger(__file__)


class SessionMetaException(Exception):
    pass


def build_session_meta(target_tee, config):
    """Helper function to create a session meta object.

    We expect config to be a dictionary containing the params needed to
    initialize the target-specific session meta object.

    This function returns a session meta object.
    """

    if config["target"] != target_tee:
        raise SessionMetaException("Target TEE mismatch.")

    if target_tee == TEEID.OPTEE or target_tee == TEEID.BEANPOD:
        session_meta = OPTEESessionMetaData(config["uuid"])
    elif target_tee == TEEID.TC:
        session_meta = TCSessionMetaData(
            config["uuid"],
            config["login_blob"],
            config["process_name"],
            int(config["uid"]),
        )
    elif target_tee == TEEID.QSEE:
        session_meta = QSEESessionMetaData(
            config["path"], config["fname"], int(config["sb_size"], 16)
        )
    else:
        raise SessionMetaException(f"Unknown TEE {target_tee}")
    return session_meta


class SessionMetaBuilder(object):
    def __init__(self, config):
        self._target_tee = config["target"]


class SessionMetaData:
    def serialize(self):
        out = b""
        for k, v in self.__dict__.items():
            # log.debug(f"key: {k}")
            k_enc = k.encode()[1:]
            v_enc = v if isinstance(v, bytes) else v.encode()
            out += p8(len(k_enc)) + k_enc
            out += p32(len(v_enc)) + v_enc
        return out


class OPTEESessionMetaData(SessionMetaData):
    def __init__(self, uuid):
        """
        Args:
            uuid:       b64-encoded uuid
        """
        super(OPTEESessionMetaData, self).__init__()
        if not isinstance(uuid, bytes):
            uuid = uuid.encode()
        self._uuid = codecs.decode(uuid, "hex")


class TCSessionMetaData(SessionMetaData):
    def __init__(self, uuid: bytes, login_blob: bytes, process_name: str, uid: int):
        super(TCSessionMetaData, self).__init__()
        if not isinstance(uuid, bytes):
            uuid = uuid.encode()
        self._uuid = codecs.decode(uuid, "hex")
        with open(login_blob, "rb") as f:
            self._login_blob = f.read()
        self._process_name = process_name
        self._uid = p32(uid)


class QSEESessionMetaData(SessionMetaData):
    def __init__(self, path: str, fname: str, sb_size: int):
        super(QSEESessionMetaData, self).__init__()
        self._path = path.encode()
        self._fname = fname.encode()
        self._sb_size = p32(sb_size)
