#!/usr/bin/env python3
import os
from io import BytesIO
import logging
import struct
import pickle
import ctypes
import hexdump
import random

from fuzz.utils import p32, u32, u64, p64

from . import tc
from .tc import (
    TEEC_ParamType,
    TEEC_ParamType_dict,
    TEEC_ReturnCode,
    TEEC_ReturnCode_dict,
    TEEC_ReturnCodeOrigin,
    TEEC_ReturnCodeOrigin_dict,
)

log = logging.getLogger(__file__)


class TcSerializationException(Exception):
    pass


class cTcNsMemrefParam(ctypes.Structure):
    _fields_ = [
        ("buffer", ctypes.c_uint64),
        ("offset", ctypes.c_uint64),
        ("size_addr", ctypes.c_uint64),
    ]


class cTcNsValueParam(ctypes.Structure):
    _fields_ = [("a_value", ctypes.c_uint64), ("b_value", ctypes.c_uint64)]


class cTcNsClientParam(ctypes.Union):
    _fields_ = [("memref", cTcNsMemrefParam), ("value", cTcNsValueParam)]


class cTcNsClientReturn(ctypes.Structure):
    _fields_ = [("code", ctypes.c_uint32), ("origin", ctypes.c_uint32)]


class cTcNsClientLogin(ctypes.Structure):
    _fields_ = [("method", ctypes.c_uint32), ("mdata", ctypes.c_uint32)]


class cTcNsClientContext(ctypes.Structure):
    _fields_ = [
        ("uuid", ctypes.c_uint8 * 16),
        ("session_id", ctypes.c_uint32),
        ("cmd_id", ctypes.c_uint32),
        ("returns", cTcNsClientReturn),
        ("login", cTcNsClientLogin),
        ("params", cTcNsClientParam * 4),
        ("paramTypes", ctypes.c_uint32),
        ("started", ctypes.c_uint8),
    ]


class cTcNsClientContextAuth(ctypes.Structure):
    _fields_ = [
        ("uuid", ctypes.c_uint8 * 16),
        ("session_id", ctypes.c_uint32),
        ("cmd_id", ctypes.c_uint32),
        ("returns", cTcNsClientReturn),
        ("login", cTcNsClientLogin),
        ("params", cTcNsClientParam * 4),
        ("paramTypes", ctypes.c_uint32),
        ("started", ctypes.c_uint8),
        ("teec_token", ctypes.c_uint64),
    ]


class ParamException(Exception):
    pass


class TC_NS_ClientParam:
    """class representing a TC_NS_ClientParam

    struct found in Huawei Kernels looks like this:
        typedef union {
            struct {
                __u64 buffer;
                __u64 offset;
                __u64 size_addr;
            } memref;
            struct {
                __u64 *a_addr;
                __u64 *b_addr;
            } value;
        } TC_NS_ClientParam;
    """

    TYPES = [
        TEEC_ParamType.TEEC_MEMREF_TEMP_INPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_OUTPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_INOUT,
        TEEC_ParamType.TEEC_MEMREF_WHOLE,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_OUTPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INOUT,
        TEEC_ParamType.TEEC_VALUE_INOUT, TEEC_ParamType.TEEC_VALUE_INPUT,
        TEEC_ParamType.TEEC_VALUE_OUTPUT
    ]
    MEMREF_TYPES = [
        TEEC_ParamType.TEEC_MEMREF_TEMP_INPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_OUTPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_INOUT,
        TEEC_ParamType.TEEC_MEMREF_WHOLE,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_OUTPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INOUT,
    ]

    MEMREF_INPUT_TYPES = [
        TEEC_ParamType.TEEC_MEMREF_TEMP_INPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_INOUT,
        TEEC_ParamType.TEEC_MEMREF_WHOLE,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INOUT,
    ]

    MEMREF_OUTPUT_TYPES = [
        TEEC_ParamType.TEEC_MEMREF_TEMP_INOUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_OUTPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INOUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_OUTPUT,
    ]

    VALUE_TYPES = [
        TEEC_ParamType.TEEC_VALUE_INOUT,
        TEEC_ParamType.TEEC_VALUE_INPUT,
        TEEC_ParamType.TEEC_VALUE_OUTPUT,
    ]

    VALUE_INPUT_TYPES = [
        TEEC_ParamType.TEEC_VALUE_INOUT,
        TEEC_ParamType.TEEC_VALUE_INPUT,
    ]

    VALUE_OUTPUT_TYPES = [
        TEEC_ParamType.TEEC_VALUE_INOUT,
        TEEC_ParamType.TEEC_VALUE_OUTPUT,
    ]

    INPUT_TYPES = [
        TEEC_ParamType.TEEC_VALUE_INOUT,
        TEEC_ParamType.TEEC_VALUE_INPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_INPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_INOUT,
        TEEC_ParamType.TEEC_MEMREF_WHOLE,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INOUT,
    ]

    OUTPUT_TYPES = [
        TEEC_ParamType.TEEC_VALUE_INOUT,
        TEEC_ParamType.TEEC_VALUE_OUTPUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_INOUT,
        TEEC_ParamType.TEEC_MEMREF_TEMP_OUTPUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_INOUT,
        TEEC_ParamType.TEEC_MEMREF_PARTIAL_OUTPUT,
    ]

    def __init__(self, param_type, param_a, param_b, param_c):
        self._param_type = param_type
        self._param_a = param_a
        self._param_a_types = None
        self._param_b = param_b
        self._param_c = param_c
        self.data_paths = None

    @property
    def data(self):
        out = b""
        if self._param_a:
            out += p32(len(self._param_a)) + self._param_a
        if self._param_b:
            out += p32(len(self._param_b)) + self._param_b
        if self._param_c:
            out += p32(len(self._param_c)) + self._param_c
        return out

    def is_input(self):
        if self._param_type in TC_NS_ClientParam.INPUT_TYPES:
            return True
        return False

    def is_output(self):
        if self._param_type in TC_NS_ClientParam.OUTPUT_TYPES:
            return True
        return False

    def mutate(self, mutate_func):
        if self._param_a:
            self._param_a = mutate_func(self._param_a, self._param_a_types)
        # if self._param_b:
        #     self._param_b = mutate_func(self._param_b)
        # if self._param_c:
        #     self._param_c = mutate_func(self._param_c)
        return

    def resolve(self, dst_param, src_id, src_off, dst_id, dst_off, sz):
        if src_id.endswith("a"):
            src = self._param_a
        elif src_id.endswith("b"):
            src = self._param_b
        elif src_id.endswith("c"):
            src = self._param_c

        if not src:
            return

        data = src[src_off : src_off + sz]

        if dst_id.endswith("a"):
            dst_data = dst_param._param_a
            dst_param._param_a = dst_data[:dst_off] + data + dst_data[dst_off + sz :]
        elif dst_id.endswith("b"):
            dst_data = dst_param._param_b
            dst_param._param_b = dst_data[:dst_off] + data + dst_data[dst_off + sz :]
        elif dst_id.endswith("c"):
            dst_data = dst_param._param_c
            dst_param._param_c = dst_data[:dst_off] + data + dst_data[dst_off + sz :]
        return

    def unmutate(self, seed, idx, skip_indices=[]):
        """Compares the contents of `self` and `seed` byte-by-byte and sets
        the first differing byte to the byte found in `seed`.
        The contents of `self` are seen as a sequence of bytes.
        If a byte is changed, the squence index of this byte is returned as
        well as a `TC_NS_ClientParam` object where this byte is reverted.
        Otherwise, the last sequence idx and `None` is returned.
        `skip_indices` can be used to exclude an index from being changed.
        """
        mutant_data = bytearray(self.serialize().encode())
        seed_data = bytearray(seed.serialize().encode())

        for data_idx in range(len(mutant_data)):
            if mutant_data[data_idx] != seed_data[data_idx] and idx not in skip_indices:
                mutant_data[data_idx] = seed_data[data_idx]
                param = TC_NS_ClientParam.deserialize(mutant_data.decode())
                return idx, param
            idx += 1

        return idx, None


class TC_NS_ClientContext:
    """class representing TC_NS_ClientContext

    struct found in Huawei Kernels looks like this:
        typedef struct {
            unsigned char uuid[16];
            __u32 session_id;
            __u32 cmd_id;
            TC_NS_ClientReturn returns;
            TC_NS_ClientLogin login;
            TC_NS_ClientParam params[4];
            __u32 paramTypes;
            __u8 started;
        } TC_NS_ClientContext;
    """

    TC_NS_CLIENT_CONTEXT = "TC_NS_ClientContext"

    TYPES_EXT = ".types"

    PARAM_0_A = "param_0_a"
    PARAM_0_B = "param_0_b"
    PARAM_0_C = "param_0_c"

    PARAM_1_A = "param_1_a"
    PARAM_1_B = "param_1_b"
    PARAM_1_C = "param_1_c"

    PARAM_2_A = "param_2_a"
    PARAM_2_B = "param_2_b"
    PARAM_2_C = "param_2_c"

    PARAM_3_A = "param_3_a"
    PARAM_3_B = "param_3_b"
    PARAM_3_C = "param_3_c"

    PARAMS = [
        (PARAM_0_A, PARAM_0_B, PARAM_0_C),
        (PARAM_1_A, PARAM_1_B, PARAM_1_C),
        (PARAM_2_A, PARAM_2_B, PARAM_2_C),
        (PARAM_3_A, PARAM_3_B, PARAM_3_C),
    ]

    NUM_PARAMS = 4

    def __init__(self):
        self.c_struct = None
        self.params = None

    @property
    def uuid(self):
        return bytes(self.c_struct.uuid)

    @property
    def session_id(self):
        return self.c_struct.session_id

    @property
    def cmd_id(self):
        return self.c_struct.cmd_id

    @property
    def code(self):
        return self.c_struct.returns.code

    @property
    def origin(self):
        return self.c_struct.returns.origin

    @property
    def method(self):
        return self.c_struct.login.method

    @property
    def mdata(self):
        return self.c_struct.login.mdata

    @property
    def param_types(self):
        return self.c_struct.paramTypes

    @property
    def started(self):
        return self.c_struct.started

    @property
    def teec_token(self):
        return self.c_struct.teec_token

    def is_crash(self):
        if self.code in [tc.TEEC_ReturnCode.TEE_ERROR_TAGET_DEAD]:
            return True
        return False

    def is_success(self):
        if self.code in [tc.TEEC_ReturnCode.TEEC_SUCCESS]:
            return True
        return False

    @property
    def coverage(self):
        """Return a short textual representation to describe this arg."""
        out = f"{self.cmd_id:08x}"
        out += f":{self.param_types:04x}"
        out += f":{self.code:08x}"
        out += f":{self.origin:08x}"
        return out

    def satisfy_dependency(self, dep, mutant_from):
        """Adjusts mutant concerning the dependency dep with data from mutant_from.

        Copies data from parameters in mutant_from to parameters in mutant.
        The ValueDependency dep describes which data is copied.

        Args:
            dep: ValueDependency describing the relationship between mutant and mutant_from
            mutant_from: TC_NS_ClientContext describing the previous call

        Returns:
            True if no error occured, False if an error ocurred.
        """

        # get the relevant numbers
        src_param_id = int(dep.src_param_identifier.split("_")[1])
        src_param_specifier = dep.src_param_identifier.split("_")[2]
        src_off = dep.src_off
        src_sz = dep.src_sz

        dst_param_id = int(dep.dst_param_identifier.split("_")[1])
        dst_param_specifier = dep.dst_param_identifier.split("_")[2]
        dst_off = dep.dst_off
        dst_sz = dep.dst_sz

        # get source buffer
        src_buf = mutant_from.get_data_from_param(src_param_id, src_param_specifier)
        if not src_buf:
            log.error("get_data_from_param failed")
            return False

        # make sure our source buffer is large enough
        if not (len(src_buf) >= src_off + src_sz):
            log.warn("Source buffer is shorter than the dependency expects")

        # cut the source buffer to match our required data
        src_buf = src_buf[src_off : src_off + src_sz]

        # get destination buffer
        dst_buf = self.get_data_from_param(dst_param_id, dst_param_specifier)
        if not dst_buf:
            return True
            log.error("get_data_from_param failed")
            return False

        # manipulate the buffer
        dst_buf = dst_buf[:dst_off] + src_buf + dst_buf[dst_off + dst_sz :]

        # write data back to dst_params array
        dst_params = self.get_params()
        dst_param = dst_params[dst_param_id]
        if dst_param.is_memref_type():
            dst_params[dst_param_id].set_buf(dst_buf)
        elif dst_param.is_value_type():
            if dst_param_specifier == "a":
                dst_param.set_value_a_raw(dst_buf[0:8])
            elif dst_param_specifier == "b":
                dst_param.set_value_b_raw(dst_buf[0:8])
            elif dst_param_specifier == "c":
                dst_param.set_value_c_raw(dst_buf[0:8])
            else:
                log.error("Invalid param specifier.")
                return False
        else:
            # This should never happen
            log.error("Dependency cannot be resolved (Incompatible type)")
            import ipdb

            ipdb.set_trace()
            return False

        # write parameter back
        self.set_params(dst_params)

        return True

    def unmutate(self, seed, skip_indices=[]):
        """Compares the contents of `self` and `seed` byte-by-byte and sets
        the first differing byte to the byte found in `seed`.
        The contents of `self` are seen as a sequence of bytes.
        If a byte is changed, the squence index of this byte is returned.
        Otherwise, `None` is returned.
        `skip_indices` can be used to exclude an index from being changed.
        """

        # we view all the contents of the `TC_NS_ClientContext` object as
        # a sequence of bytes. This `idx` keeps track of the current idx
        # into this sequence.
        idx = 0

        # check that the corresponding buffers of `self` and `seed` have the
        # same sizes
        mutant_params = self.get_params()
        seed_params = seed.get_params()
        assert len(mutant_params) == len(seed_params), "Number of params mismatch"

        # compare cmd_id
        mutant_cmd_id_raw = struct.pack("<I", self.cmd_id)
        seed_cmd_id_raw = struct.pack("<I", seed.cmd_id)
        for cmd_id_raw_idx in range(len(mutant_cmd_id_raw)):
            if (
                mutant_cmd_id_raw[cmd_id_raw_idx] != seed_cmd_id_raw[cmd_id_raw_idx]
                and idx not in skip_indices
            ):
                mutant_cmd_id_raw[cmd_id_raw_idx] = seed_cmd_id_raw[cmd_id_raw_idx]
                self.cmd_id = struct.unpack("<I", mutant_cmd_id_raw)
                return idx
            idx += 1

        # compare params
        for param_idx in range(len(mutant_params)):
            idx, unmutated = mutant_params[param_idx].unmutate(
                seed_params[param_idx], idx, skip_indices
            )
            if unmutated:
                self._params[param_idx] = unmutated
                return idx

        return None

    @classmethod
    def _serialize_raw(cls, ctx):
        """Creates a chunk of raw memory from `ctx` (`TC_NS_ClientContext`)"""
        buf = bytes(ctx.c_struct)

        if len(buf) == ctypes.sizeof(cTcNsClientContext):
            pass
        elif len(buf) == ctypes.sizeof(cTcNsClientContextAuth):
            pass
        else:
            raise TcSerializationException(
                "Cannot serialize buffer of len {}".format(len(buf))
            )

        return buf

    def serialize(self):
        return self.serialize_obj(self)

    @classmethod
    def serialize_obj(cls, ctx):
        """Converts a `TC_NS_ClientContext` Python object to its raw
           representation.

        This functions opens and parses a `TC_NS_ClientContext` Python object
        from `ctx` and converts it into its raw representation.

        Args:
            `ctx`: `TC_NS_ClientContext` Python object

        Returns:
            A Python `bytes` object containing `ctx` and its params.
        """

        out = TC_NS_ClientContext._serialize_raw(ctx)

        for i, param in enumerate(ctx.params):
            param_type = tc.get_param_type(i, ctx.c_struct.paramTypes)
            if param_type is TEEC_ParamType.TEEC_NONE:
                continue
            elif param_type in TC_NS_ClientParam.VALUE_TYPES:
                # just a short sanity check
                if param.data and len(param.data) != 2 * 4 + 2 * 8:
                    raise TcSerializationException("value param len")
                out += param.data
            elif param_type in TC_NS_ClientParam.MEMREF_TYPES:
                out += param.data
            else:
                raise TcSerializationException("unknown param type")

        return out

    def serialize_to_path(self, ctx_dir):
        self.serialize_obj_to_path(self, ctx_dir)

    @classmethod
    def serialize_obj_to_path(cls, ctx, ctx_dir):
        ctx_buf = cls._serialize_raw(ctx)
        ctx_path = os.path.join(ctx_dir, cls.TC_NS_CLIENT_CONTEXT)
        with open(ctx_path, "wb") as f:
            f.write(ctx_buf)

        if ctx.params is None:
            # this should only be the case for non-success `ctx`s
            if ctx.code == TEEC_ReturnCode.TEEC_SUCCESS:
                raise TcSerializationException("Successful ctx should have params")
            return

        for i, param in enumerate(ctx.params):
            param_type = tc.get_param_type(i, ctx.c_struct.paramTypes)
            if param_type == TEEC_ParamType.TEEC_NONE or not param.data:
                # if NONE param type or no data present, skip
                continue
            if param_type in TC_NS_ClientParam.MEMREF_TYPES:
                # store buffer
                filename = cls.PARAMS[i][0]
                param_path = os.path.join(ctx_dir, filename)
                with open(param_path, "wb") as f:
                    f.write(param._param_a)

                # store buffer types
                param_types_path = param_path + TC_NS_ClientContext.TYPES_EXT
                if param._param_a_types:
                    with open(param_types_path, "wb") as f:
                        pickle.dump(param._param_a_types, f)

                # store size
                filename = cls.PARAMS[i][2]
                param_path = os.path.join(ctx_dir, filename)
                with open(param_path, "wb") as f:
                    f.write(param._param_c)
            elif param_type in TC_NS_ClientParam.VALUE_TYPES:
                # store a value
                filename = cls.PARAMS[i][0]
                param_path = os.path.join(ctx_dir, filename)
                with open(param_path, "wb") as f:
                    f.write(param._param_a)
                # store b value
                filename = cls.PARAMS[i][1]
                param_path = os.path.join(ctx_dir, filename)
                with open(param_path, "wb") as f:
                    f.write(param._param_b)
            else:
                raise TcSerializationException("Unknown param type")

    def deserialize(self):
        return self.deserialize_obj(self)

    @staticmethod
    def read_lv_len(f):
        sz_raw = f.read(4)
        sz = u32(sz_raw)
        return sz, sz_raw

    @staticmethod
    def read_lv_val(f):
        data = b""
        sz, _ = TC_NS_ClientContext.read_lv_len(f)
        data += f.read(sz)
        return data

    @staticmethod
    def read_lv(f):
        data = b""
        sz, sz_raw = TC_NS_ClientContext.read_lv_len(f)
        data += sz_raw
        data += f.read(sz)
        return data

    @classmethod
    def deserialize_obj(cls, buf):
        f = BytesIO(buf)
        sz = u32(f.read(4))

        if sz != ctypes.sizeof(cTcNsClientContext) and sz != ctypes.sizeof(
            cTcNsClientContextAuth
        ):
            raise TcSerializationException("Error: wrong size.")

        ctx = cls._deserialize_raw(f.read(sz))
        if ctx.code != TEEC_ReturnCode.TEEC_SUCCESS:
            return ctx

        ctx.params = []

        # update output params
        for i in range(cls.NUM_PARAMS):
            param_type = tc.get_param_type(i, ctx.c_struct.paramTypes)
            if param_type in TC_NS_ClientParam.MEMREF_OUTPUT_TYPES:
                # buffer
                param_a = cls.read_lv_val(f)
                # size
                param_c = p32(len(param_a))
                ctx.params.append(TC_NS_ClientParam(param_type, param_a, None, param_c))
            elif param_type in TC_NS_ClientParam.VALUE_OUTPUT_TYPES:
                # a value
                param_a = cls.read_lv_val(f)
                # b value
                param_b = cls.read_lv_val(f)
                ctx.params.append(TC_NS_ClientParam(param_type, param_a, param_b, None))
            else:
                # NONE and INPUT param types should have size of 0
                sz, _ = TC_NS_ClientContext.read_lv_len(f)
                if sz != 0:
                    raise TcSerializationException(
                        "We do not expect to deserialize input params."
                    )
                ctx.params.append(TC_NS_ClientParam(param_type, None, None, None))
        return ctx

    @classmethod
    def _deserialize_raw(self, buf):
        """Creates a `TC_NS_ClientContext` from `buf`"""

        if len(buf) == ctypes.sizeof(cTcNsClientContext):
            c_struct = cTcNsClientContext.from_buffer_copy(buf)
        elif len(buf) == ctypes.sizeof(cTcNsClientContextAuth):
            c_struct = cTcNsClientContextAuth.from_buffer_copy(buf)
        else:
            raise TcSerializationException(
                "Cannot deserialize buffer of len {}".format(len(buf))
            )

        ctx = self()
        ctx.c_struct = c_struct
        return ctx

    @classmethod
    def deserialize_raw_from_path(cls, ctx_dir):
        """Loads a raw context and its raw params from `ctx_path`.

        This functions opens and parses the raw memory dump of a
        `TC_NS_ClientContext` struct and turns it into a Python
        `TC_NS_ClientContext` object.
        It also trys to find raw memory dumps of parameters by searching for
        files following the naming convention in `PARAMS`.
        These parameters are turned into `TC_NS_ClientParam` objects and added
        to the context.

        Args:
            `ctx_path`: filename pointing to the raw memory dump of a
                      `TC_NS_ClientContext`

        Returns:
            The deserialized context.
        """
        ctx_path = os.path.join(ctx_dir, TC_NS_ClientContext.TC_NS_CLIENT_CONTEXT)
        with open(ctx_path, "rb") as f:
            ctx = TC_NS_ClientContext._deserialize_raw(f.read())

        if ctx.code == TEEC_ReturnCode.TEEC_SUCCESS:
            ctx.params = ctx._load_params_from_folder(ctx_dir)
        else:
            ctx.params = []
            for i in range(TC_NS_ClientContext.NUM_PARAMS):
                ctx.params.append(
                    TC_NS_ClientParam(TEEC_ParamType.TEEC_NONE, None, None, None)
                )

        if len(ctx.params) != TC_NS_ClientContext.NUM_PARAMS:
            raise TcSerializationException("Wrong number of params")
        return ctx

    @classmethod
    def serialize_raw_from_path(self, ctx_path):
        with open(ctx_path, "rb") as f:
            ctx = pickle.load(f)
        return TC_NS_ClientContext.serialize_raw_with_params(ctx)

    def _load_params_from_folder(self, _dir):
        """Loads parameters from a folder and returns them.

        This functions loads parameter values from the files in folder_path.
        It searches for the parameter expected by the context `self`.

        Args:
            folder_path: path to folder containing raw params

        Returns:
            List of `TC_NS_ClientParam` objects.
        """
        params = []
        for i, param in enumerate(self.PARAMS):
            param_type = tc.get_param_type(i, self.c_struct.paramTypes)
            param_a_path = os.path.join(_dir, param[0])
            param_a_types_path = param_a_path + self.TYPES_EXT
            param_a_types = None
            param_b_path = os.path.join(_dir, param[1])
            param_c_path = os.path.join(_dir, param[2])

            if param_type is TEEC_ParamType.TEEC_NONE:
                params.append(TC_NS_ClientParam(param_type, None, None, None))
            elif param_type in TC_NS_ClientParam.MEMREF_TYPES:
                if os.path.exists(param_a_path):
                    param_path = param_a_path
                    with open(param_a_path, "rb") as f:
                        param_a = f.read()
                    with open(param_c_path, "rb") as f:
                        param_c = f.read()
                    if os.path.exists(param_a_types_path):
                        with open(param_a_types_path, "rb") as f:
                            param_a_types = pickle.load(f)
                else:
                    param_path = None
                    param_a = None
                    param_c = None

                client_param = TC_NS_ClientParam(param_type, param_a, None, param_c)
                client_param._param_a_types = param_a_types
                client_param.data_paths = [param_path] if param_path else None
                params.append(client_param)
            elif param_type in TC_NS_ClientParam.VALUE_TYPES:
                if os.path.exists(param_a_path):
                    with open(param_a_path, "rb") as f:
                        param_a = f.read()
                    with open(param_b_path, "rb") as f:
                        param_b = f.read()
                else:
                    param_a = None
                    param_b = None

                client_param.data_paths = [param_a_path] if param_a_path else None
                client_param = TC_NS_ClientParam(param_type, param_a, param_b, None)

                params.append(client_param)
            else:
                raise TcSerializationException("Unknown param type")
        return params

    def resolve(self, dst_ctx, valdep):
        _, src_param_idx, _ = valdep.src_id.split("_")
        src_param_idx = int(src_param_idx)

        _, dst_param_idx, _ = valdep.dst_id.split("_")
        dst_param_idx = int(dst_param_idx)

        src_param = self.params[src_param_idx]
        dst_param = dst_ctx.params[dst_param_idx]
        src_param.resolve(
            dst_param,
            valdep.src_id,
            valdep.src_off,
            valdep.dst_id,
            valdep.dst_off,
            valdep.src_sz,
        )

    def mutate(self, mutate_func):
        self.c_struct.cmd_id = u32(mutate_func(p32(self.c_struct.cmd_id), "uint32_t"))
        return

    def get_num_output_value_params(self):
        """Returns the number of output value type parameters."""
        return len([1 for p in self._params if p and p.is_output_value_type()])

    def get_num_output_memref_params(self):
        """Returns the number of output memref type parameters."""
        return len([1 for p in self._params if p and p.is_output_memref_type()])

    def get_num_output_params(self):
        """Returns the number of output type parameters."""
        return len([1 for p in self._params if p and p.is_output_type()])

    def get_data_from_param(self, param_id, param_specifier):
        """Returns required data from the parameter.

        Args:
            param_id: The number of the parameter
            param_specifier: The specifier of the parameter ('a', 'b' or 'c')

        Returns:
            The extracted data, None if an error ocurred.
        """
        # get the params which shall be modified
        try:
            params = self.get_params()
        except AssertionError:
            log.error("Dependency cannot be resolved (mutant has no params)")
            return None

        # This is where we copy the data to
        param = params[param_id]

        if param.is_memref_type():
            return param.get_buf()
        elif param.is_value_type():
            if param_specifier == "a":
                return param.get_value_a_raw()
            elif param_specifier == "b":
                return param.get_value_b_raw()
            elif param_specifier == "c":
                return param.get_value_c_raw()
            else:
                log.error("Invalid param specifier.")
                import ipdb

                ipdb.set_trace()
                return None
        else:
            # This should never happen
            log.error("Dependency cannot be resolved (Incompatible type)")
            import ipdb

            ipdb.set_trace()
            return None

    def __str__(self):
        uuid = "uuid"
        session_id = "session_id"
        cmd_id = "cmd_id"
        code = "code"
        origin = "origin"
        method = "method"
        mdata = "mdata"
        paramTypes = "paramTypes"
        started = "started"
        out = (
            f"{uuid:<20}: {self.uuid}\n"
            f"{session_id:<20}: {self.session_id:#x}\n"
            f"{cmd_id:<20}: {self.cmd_id:#x}\n"
            f"{code:<20}: {self.code:#x}\n"
            f"{origin:<20}: {self.origin:#x}\n"
            f"{method:<20}: {self.method:#x}\n"
            f"{mdata:<20}: {self.mdata:#x}\n"
            f"{paramTypes:<20}: {self.param_types:#x}\n"
            f"{started:<20}: {self.started:#x}\n"
        )

        if self.params:
            for idx, param in enumerate(self.params):
                p = f"param[{idx}]"
                out += f"{p:<20}: "
                if param.data:
                    out += hexdump.dump(param.data)[:64]
                    out += f" (sz={len(param.data)})"
                else:
                    out += "NONE"
                out += "\n"

        return out

        out += "{:<20} {}\n".format("uuid:", self.uuid)
        out += "{:<20} {}\n".format("session_id:", hex(self.session_id))
        """
        if self.uuid == tc.KEYMASTER_UUID.encode().hex(
        ) and self.cmd_id in tc.SVC_KEYMASTER_CMD_ID_dict:
            out += "{:<20} {} ({})\n".format(
                "cmd_id:", tc.SVC_KEYMASTER_CMD_ID_dict[self.cmd_id],
                hex(self.cmd_id))
        """
        out += "{:<20} {}\n".format("cmd_id:", hex(self.cmd_id))

        if self.returns.code in TEEC_ReturnCode_dict:
            out += "{:<20} {} ({})\n".format(
                "returns.code:",
                TEEC_ReturnCode_dict[self.returns.code],
                hex(self.returns.code),
            )
        else:
            out += "{:<20} {} ({})\n".format(
                "returns.code:", "unknown ret code", hex(self.returns.code)
            )
        if self.returns.origin in TEEC_ReturnCodeOrigin_dict:
            out += "{:<20} {} ({})\n".format(
                "returns.origin:",
                TEEC_ReturnCodeOrigin_dict[self.returns.origin],
                hex(self.returns.origin),
            )
        else:
            out += "{:<20} {} ({})\n".format(
                "returns.origin:", "unknown origin", hex(self.returns.origin)
            )
        out += "{:<20} {}\n".format("login.method:", hex(self.login.method))
        out += "{:<20} {}\n".format("login.mdata:", hex(self.login.mdata))
        out += "{:<20} {}\n".format(
            "originalParamTypes:", hex(self.original_paramTypes)
        )
        if self._params and (
            self.returns.code in TEEC_ReturnCode_dict
            and self.returns.code
            in [TEEC_ReturnCode.TEE_CODE_NOT_SET, TEEC_ReturnCode.TEEC_SUCCESS]
        ):
            out += "{:<20} {}\n".format("paramTypes:", hex(self.get_paramTypes()))

            out += "\n"
            out += "    {:<10} {} ({})\n".format(
                "p0:",
                TEEC_ParamType_dict[tc.get_param_type(0, self.get_paramTypes())],
                hex(tc.get_param_type(0, self.get_paramTypes())),
            )

            if self._params and self._params[0]:
                out += "\n"
                out += str(self._params[0]) + "\n"
                out += "\n"
            out += "    {:<10} {} ({})\n".format(
                "p1:",
                TEEC_ParamType_dict[tc.get_param_type(1, self.get_paramTypes())],
                hex(tc.get_param_type(1, self.get_paramTypes())),
            )

            if self._params and self._params[1]:
                out += "\n"
                out += str(self._params[1]) + "\n"
                out += "\n"
            out += "    {:<10} {} ({})\n".format(
                "p2:",
                TEEC_ParamType_dict[tc.get_param_type(2, self.get_paramTypes())],
                hex(tc.get_param_type(2, self.get_paramTypes())),
            )

            if self._params and self._params[2]:
                out += "\n"
                out += str(self._params[2]) + "\n"
                out += "\n"
            out += "    {:<10} {} ({})\n".format(
                "p3:",
                TEEC_ParamType_dict[tc.get_param_type(3, self.get_paramTypes())],
                hex(tc.get_param_type(3, self.get_paramTypes())),
            )

            if self._params and self._params[3]:
                out += "\n"
                out += str(self._params[3]) + "\n"
                out += "\n"
        else:
            out += "{:<20}\n".format(
                "Not printing params. No params set. Bad return code?"
            )

        out += "{:<20} {}".format("started:", hex(self.started))
        return out
