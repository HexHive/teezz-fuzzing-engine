import logging
import os
import hexdump
from typing import Union, List, Callable
from io import BytesIO

from fuzz.utils import p32, u32, u64, p64, us32

log = logging.getLogger(__file__)


class QseecomParam():
    def __init__(self,
                 data: bytes,
                 is_input: bool,
                 path: Union[str, None] = None):
        self._data = data
        self._is_input = is_input
        self._path = path
        self._ioctl_ret = 0

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def data_paths(self) -> List[Union[str, None]]:
        paths = []
        if self._path:
            paths.append(self._path)
        return paths

    def mutate(self, mutate_func: Callable):
        if self._data:
            self._data = mutate_func(self._data)
        return

    def is_input(self) -> bool:
        return self._is_input

    def is_output(self) -> bool:
        return not self._is_input


class QseecomReq(object):
    """class representing a generic qseecom request struct

    /*
     * @cmd_req_len - command buffer length
     * @cmd_req_buf - command buffer
     * @resp_len - response buffer length
     * @resp_buf - response buffer
     */
    """

    MODFD_CMD_REQ = "qseecom_send_modfd_cmd_req"
    CMD_REQ = "qseecom_send_cmd_req"

    def __init__(self, req_buf: bytes, resp_buf: bytes):
        self._req = QseecomParam(req_buf, True)
        self._resp = QseecomParam(resp_buf, False)
        self._ioctl_ret = 0
        self.params = list()
        self.params.append(self._req)
        self.params.append(self._resp)

    def satisfy_dependency(self, dep, mutant_from):
        """Adjusts mutant concerning the dependency dep with data from mutant_from.

        Copies data from parameters in mutant_from to parameters in self.
        The ValueDependency dep describes which data is copied.

        Args:
            dep: ValueDependency describing the relationship between self and mutant_from
            mutant_from: QseecomReq describing the previous call

        Returns:
            True if no error occured, False if an error ocurred.
        """

        # get the relevant data
        src_param_specifier = dep.src_param_identifier
        src_off = dep.src_off
        src_sz = dep.src_sz

        dst_param_specifier = dep.dst_param_identifier
        dst_off = dep.dst_off
        dst_sz = dep.dst_sz

        # copy the dependent data
        if src_param_specifier == "shared":
            self._update_shared_helper(dst_sz, dst_off, src_sz, src_off,
                                       mutant_from)
        elif src_param_specifier == "req":
            if (dst_off + dst_sz) > self.resp_len:
                return False
            self.resp_buf = self.resp_buf[0:dst_off] \
                + mutant_from.cmd_req_buf[src_off:(src_off + src_sz)] \
                + self.resp_buf[(dst_off + dst_sz):self.resp_len]
        elif src_param_specifier == "resp":
            if (dst_off + dst_sz) > self.req_len:
                return False
            #import ipdb; ipdb.set_trace()
            self.req_buf = self.req_buf[0:dst_off] \
                + mutant_from.resp_buf[src_off:(src_off + src_sz)] \
                + self.req_buf[(dst_off + dst_sz):self.req_len]
        else:
            return False

        return True

    # TODO: we'll see later if we keep this in the subclasses or here
    #@classmethod
    #def get_cmdreq_from_path(cls, req_path):
    #    """Create a QseecomSendCmdRequest Object from a file.

    #    Args:
    #        path: Path to the cmd_req

    #    Returns: Object of subclass depending on type of request
    #    """
    #    with open(os.path.join(req_path, "req"), "rb") as f:
    #        req_data = f.read()
    #    with open(os.path.join(req_path, "resp"), "rb") as f:
    #        resp_data = f.read()

    #    if os.path.isfile(os.path.join(req_path, cls.CMD_REQ)):
    #        send_cmd_req = QseecomSendCmdReq(req_data, len(req_data),
    #                                         resp_data, len(resp_data))
    #    elif os.path.isfile(os.path.join(req_path, cls.MODFD_CMD_REQ)):
    #        if os.path.isfile(os.path.join(req_path, "shared")):
    #            with open(os.path.join(req_path, "shared"), "rb") as f:
    #                shared_data = f.read()
    #            send_cmd_req = QseecomSendModfdCmdReq(req_data,
    #                                                  len(req_data), resp_data,
    #                                                  len(resp_data),
    #                                                  shared_data,
    #                                                  len(shared_data))
    #        else:
    #            send_cmd_req = QseecomSendModfdCmdReq(req_data,
    #                                                  len(req_data), resp_data,
    #                                                  len(resp_data))
    #    else:
    #        log.error("unknown command in QSEE seeds!")
    #        return None
    #    return send_cmd_req


class QseecomSendModfdCmdReq(QseecomReq):
    """child class representing a struct qsee_send_modfd_cmd_req

    /*
     * struct qseecom_send_modfd_cmd_req - for send command ioctl request
     * @shared_len - shared buffer length
     * @shared_buf - shared buffer
     */
    struct qseecom_send_modfd_cmd_req {
        void *cmd_req_buf; /* in */
        unsigned int cmd_req_len; /* in */
        void *resp_buf; /* in/out */
        unsigned int resp_len; /* in/out */
        struct qseecom_ion_fd_info ifd_data[MAX_ION_FD]; /*fd for shared buffer*/
    };
    """
    def __init__(self, cmd_req_buf, resp_buf, shared_buf=0, shared_len=0):
        super(QseecomSendModfdCmdReq, self).__init__(cmd_req_buf, resp_buf)
        self.shared_buf = shared_buf
        self.shared_len = shared_len

    def _update_shared_helper(self, dst_sz, dst_off, src_sz, src_off,
                              mutant_from):
        """ Update the shared Buffer """
        if (dst_off + dst_sz) > self.shared_len:
            return False
        self.shared_buf = self.shared_buf[0:dst_off] \
            + mutant_from.shared_buf[src_off:(src_off + src_sz)] \
            + self.shared_buf[(dst_off + dst_sz):self.shared_len]


class QseecomSendCmdReq(QseecomReq):
    """child class representing a struct qsee_send_cmd_req

    /*
     * struct qseecom_send_cmd_req - for send command ioctl request
     */
    struct qseecom_send_cmd_req {
        void *cmd_req_buf; /* in */
        unsigned int cmd_req_len; /* in */
        void *resp_buf; /* in/out */
        unsigned int resp_len; /* in/out */
    };
    """
    QSEECOM_SEND_CMD_REQ = "qseecom_send_cmd_req"
    QSEECOM_SEND_CMD_REQ_BUF = "req"
    QSEECOM_SEND_CMD_RESP_BUF = "resp"

    def __init__(self, cmd_req_buf: bytes, resp_buf: bytes):
        super(QseecomSendCmdReq, self).__init__(cmd_req_buf, resp_buf)

    """
    +serialize_obj()
    +deserialize_obj()
    +serialize_obj_to_path()
    +deserialize_obj()
    +serialize()
    +serialize_to_path()
    +deserialize()
    +bool is_crash()
    +bool is_success()
    """

    def is_crash(self):
        return False if self._ioctl_ret == 0 else True

    def is_success(self):
        res = us32(self.params[1].data[:4])
        if res == 0:
            return True
        return False

    @property
    def status_code(self):
        """ Returns the status code from the TA. """
        return us32(self.params[1].data[:4])

    def mutate(self, mutate_func):
        return

    def resolve(self, dst_ctx, valdep):
        src_param = self.params[1]
        dst_param = dst_ctx.params[0]

        data = src_param.data[valdep.src_off:valdep.src_off + valdep.src_sz]
        dst_param._data = dst_param.data[:valdep.
                                         dst_off] + data + dst_param.data[
                                             valdep.dst_off + valdep.src_sz:]

    @property
    def coverage(self):
        """ Return a short textual representation to describe this arg. """
        # TODO: fix if it works
        out = f"{u32(self._req.data[:4]):08x}"
        out += f":{u32(self._resp.data[:4]):08x}"
        return out

    @classmethod
    def deserialize_raw_from_path(cls, req_dir: str):
        req_path = os.path.join(req_dir,
                                QseecomSendCmdReq.QSEECOM_SEND_CMD_REQ_BUF)
        resp_path = os.path.join(req_dir,
                                 QseecomSendCmdReq.QSEECOM_SEND_CMD_RESP_BUF)
        with open(req_path, "rb") as f:
            req_buf = f.read()
        with open(resp_path, "rb") as f:
            resp_buf = f.read()
        obj = cls(req_buf, resp_buf)
        obj._req._path = req_path
        obj._resp._path = resp_path
        return obj

    @classmethod
    def deserialize_obj(cls, buf: bytes):

        f = BytesIO(buf)
        ioctl_ret = u32(f.read(4))
        req_sz = u32(f.read(4))
        req_buf = f.read(req_sz)
        resp_sz = u32(f.read(4))
        resp_buf = f.read(resp_sz)

        res = us32(resp_buf[:4])
        # if res > 0:
        #     import ipdb
        #     ipdb.set_trace()

        obj = cls(req_buf, resp_buf)
        obj._ioctl_ret = ioctl_ret
        return obj

    def serialize(self):
        return self.serialize_obj(self)

    @classmethod
    def serialize_obj(cls, cmd_req):
        out = p32(len(cmd_req._req._data))
        out += cmd_req._req._data
        out += p32(4)
        out += p32(len(cmd_req._resp._data))
        return out

    def serialize_to_path(self, send_cmd_dir):
        self.serialize_obj_to_path(self, send_cmd_dir)

    @classmethod
    def serialize_obj_to_path(cls, send_cmd_obj, send_cmd_dir):

        ctx_path = os.path.join(send_cmd_dir, cls.QSEECOM_SEND_CMD_REQ_BUF)
        with open(ctx_path, "wb") as f:
            f.write(send_cmd_obj._req.data)

        ctx_path = os.path.join(send_cmd_dir, cls.QSEECOM_SEND_CMD_RESP_BUF)
        with open(ctx_path, "wb") as f:
            f.write(send_cmd_obj._resp.data)

    def __str__(self) -> str:
        out = "QseecomSendCmdReq\n"
        out += "req:  " + hexdump.dump(self._req._data)[:64]
        out += f" (sz={len(self._req._data)})\n"
        out += "resp: " + hexdump.dump(self._resp._data)[:64]
        out += f" (sz={len(self._resp._data)})\n"
        return out
