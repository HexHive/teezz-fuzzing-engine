from __future__ import annotations
import os
from io import BytesIO
import logging
import functools
import ctypes
import pickle
import random

from . import optee
from fuzz.utils import p32, u32, u64, p64
from fuzz.seed.seedtemplate import SeedTemplate

from typing import List, Tuple, Any, Callable


log = logging.getLogger(__file__)


class TeeIoctlInvokeArgSerializationException(Exception):
    pass


class TeeIoctlParamException(Exception):
    pass


class ParamException(Exception):
    pass


class cTeeIoctlParam(ctypes.Structure):
    _fields_ = [
        ("attr", ctypes.c_uint64),
        ("a", ctypes.c_uint64),
        ("b", ctypes.c_uint64),
        ("c", ctypes.c_uint64),
    ]


class cTeeIoctlInvokeArg(ctypes.Structure):
    _fields_ = [
        ("func", ctypes.c_uint32),
        ("session", ctypes.c_uint32),
        ("cancel_id", ctypes.c_uint32),
        ("ret", ctypes.c_uint32),
        ("ret_origin", ctypes.c_uint32),
        ("num_params", ctypes.c_uint32),
        ("params", cTeeIoctlParam * 4),
    ]


class TeeIoctlParam(object):
    """class representing a tee_ioctl_param struct

    struct tee_ioctl_param {
        __u64 attr;
        __u64 a;
        __u64 b;
        __u64 c;
    };
    """

    SIZE = 4 * 8

    TEE_IOCTL_PARAM_ATTR_TYPE_NONE = 0
    TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT = 1
    TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_OUTPUT = 2
    TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INOUT = 3
    TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT = 5
    TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT = 6
    TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT = 7

    TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_NONE,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INOUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT,
    ]

    INPUT_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INOUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT,
    ]

    OUTPUT_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INOUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT,
    ]

    MEMREF_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT,
    ]

    MEMREF_INPUT_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT,
    ]

    MEMREF_OUTPUT_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INOUT,
    ]

    VALUE_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INOUT,
    ]

    VALUE_INPUT_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INOUT,
    ]

    VALUE_OUTPUT_TYPES = [
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_OUTPUT,
        TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INOUT,
    ]

    def __init__(self):
        self.c_struct = None
        # used to hold content of memref types
        self.data = None
        self.data_paths = None
        self.types = None

    @property
    def attr(self):
        return self.c_struct.attr

    @property
    def a(self):
        return self.c_struct.a

    @property
    def b(self):
        return self.c_struct.b

    @property
    def c(self):
        return self.c_struct.c

    def is_input(self):
        if self.attr in TeeIoctlParam.INPUT_TYPES:
            return True
        return False

    def is_output(self):
        if self.attr in TeeIoctlParam.OUTPUT_TYPES:
            return True
        return False

    @classmethod
    def deserialize_raw(cls, buf):
        """buf is supposed to contain the raw tee_ioctl_param struct"""
        param = cls()
        param.c_struct = cTeeIoctlParam.from_buffer_copy(buf)
        param.data = None
        return param

    def mutate(self, mutate_func: Callable[[Any], Any]):
        r = random.random()

        # TODO: think of a smart way to mutate the parameter type
        # self.c_struct.attr

        if self.c_struct.attr in TeeIoctlParam.VALUE_INPUT_TYPES and r < 0.15:
            # 15% chance to mutate vals

            self.c_struct.a = u32(
                mutate_func(p32(self.c_struct.a & 0xFFFFFFFF), "uint32_t")
            )

            self.c_struct.b = u32(
                mutate_func(p32(self.c_struct.b & 0xFFFFFFFF), "uint32_t")
            )

        if (
            self.c_struct.attr in TeeIoctlParam.MEMREF_INPUT_TYPES
            and not self.data
        ):
            # make sure we have data for memref inputs
            self.data = b"\x00" * 128
            self.c_struct.b = 128

        # TODO: implement mutations for memref sizes
        # NOTE: the harness is currently using tmp memrefs. Thus, naively
        # mutating a memref size might corrupt the harness because libteec.so
        # copies the buffer to an internal tee-shared region. If the indicated
        # size is much larger than the actual size of the buffer, this will lead
        # to reads from unmapped memory.

        if self.data and self.types:
            self.data = mutate_func(self.data, self.types)
        elif self.data:
            self.data = mutate_func(self.data)
        return

    def __str__(self):
        out = ""
        out += "struct tee_ioctl_param\n"
        attr = optee.TEEC_ParamType_dict[self.c_struct.attr]
        out += "{:<20} {}\n".format("attr:", attr)
        out += "{:<20} {}\n".format("a:", hex(self.c_struct.a))
        out += "{:<20} {}\n".format("b:", hex(self.c_struct.b))
        out += "{:<20} {}\n".format("c:", hex(self.c_struct.c))
        return out


class TeeIoctlInvokeArg(ctypes.Structure):
    """class representing a tee_ioctl_invoke_arg struct

    struct tee_ioctl_invoke_arg {
        __u32 func;
        __u32 session;
        __u32 cancel_id;
        __u32 ret;
        __u32 ret_origin;
        __u32 num_params;
        /* num_params tells the actual number of element in params */
        struct tee_ioctl_param params[];
    };
    """

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

    PARAM_0_DATA = "param_0_data"
    PARAM_1_DATA = "param_1_data"
    PARAM_2_DATA = "param_2_data"
    PARAM_3_DATA = "param_3_data"

    PARAMS = [
        (PARAM_0_A, PARAM_0_B, PARAM_0_C, PARAM_0_DATA),
        (PARAM_1_A, PARAM_1_B, PARAM_1_C, PARAM_1_DATA),
        (PARAM_2_A, PARAM_2_B, PARAM_2_C, PARAM_2_DATA),
        (PARAM_3_A, PARAM_3_B, PARAM_3_C, PARAM_3_DATA),
    ]

    NUM_PARAMS = 4

    INVOKE_ARG_PREFIX = "tee_ioctl_invoke_arg"
    TYPES_EXT = ".types"

    _TEEC_CONFIG_PAYLOAD_REF_COUNT = 4
    _TEE_IOCTL_PARAM_SIZE = 4 * 8
    SIZE = 6 * 4 + _TEEC_CONFIG_PAYLOAD_REF_COUNT * _TEE_IOCTL_PARAM_SIZE

    def __init__(self):
        self.c_struct = None
        self.params: List[TeeIoctlParam] = []

    @property
    def func(self):
        return self.c_struct.func

    @property
    def session(self):
        return self.c_struct.session

    @property
    def cancel_id(self):
        return self.c_struct.cancel_id

    @property
    def ret(self):
        return self.c_struct.ret

    @property
    def status_code(self):
        return self.ret

    @property
    def ret_origin(self):
        return self.c_struct.ret_origin

    @property
    def num_params(self):
        return self.c_struct.num_params

    def is_crash(self) -> bool:
        if self.ret in [optee.OPTEEReturnStatus.TEEC_ERROR_TARGET_DEAD]:
            return True
        return False

    def is_success(self) -> bool:
        if self.ret in [optee.OPTEEReturnStatus.TEEC_SUCCESS]:
            return True
        return False

    def get_param_types(self) -> int:
        return functools.reduce(
            (lambda x, y: (x << 4) | y), [p.attr for p in self.params[::-1]]
        )

    def add_out_params(self, params_data):
        """`params_data` needs to be a list containing data for the
        output parameters of this `TeeIoctlInvokeArg`."""
        for param in self.params:
            if param.attr in TeeIoctlParam.MEMREF_OUTPUT_TYPES:
                param.b = u64(params_data[0])
                param.data = params_data[1]
                params_data = params_data[2:]
            elif param.attr in TeeIoctlParam.VALUE_OUTPUT_TYPES:
                param.a = u32(params_data[0])
                param.b = u32(params_data[1])
                params_data = params_data[2:]
        return

    @property
    def coverage(self) -> Tuple[Any]:
        """Returns a tuple describing the coverage generated by this
        `TeeIoctlInvokeArg`."""
        return (self.func, self.get_param_types(), self.ret, self.ret_origin)

    def mutate(self, mutate_func):
        # TODO: we do not mutate the cmd id in favor of leveraging known cmd ids
        # in combination with paramTypes, return status, and return origin as
        # a proxy for coverage

        # mutate cmd id
        # self.c_struct.func = u32(mutate_func(p32(self.c_struct.func), "uint32_t"))
        return

    def resolve(self, dst_arg: TeeIoctlInvokeArg, valdep):
        _, src_param_idx, _ = valdep.src_id.split("_")
        src_param_idx = int(src_param_idx)

        _, dst_param_idx, _ = valdep.dst_id.split("_")
        dst_param_idx = int(dst_param_idx)

        if not self.params:
            # arg does not have params, skip
            return

        src_param = self.params[src_param_idx]
        dst_param = dst_arg.params[dst_param_idx]

        if not dst_param.data:
            # no data, probably output param, sikp
            return

        if not src_param.data:
            # no data, probably input param, skip
            return

        src_prior_sz = len(src_param.data)
        dst_prior_sz = len(dst_param.data)

        src_data = src_param.data
        dst_data = dst_param.data

        dep_data = src_data[valdep.src_off : valdep.src_off + valdep.src_sz]

        dst_data = (
            dst_data[: valdep.dst_off]
            + dep_data
            + dst_data[valdep.dst_off + valdep.dst_sz :]
        )

        if not dst_data:
            import ipdb

            ipdb.set_trace()

        dst_param.data = dst_data

        if src_prior_sz != len(src_param.data):
            import ipdb

            ipdb.set_trace()

        if dst_prior_sz != len(dst_param.data):
            import ipdb

            ipdb.set_trace()

    @classmethod
    def deserialize_raw_from_path(
        cls, invoke_arg_dir: str
    ) -> TeeIoctlInvokeArg:
        """Loads a raw invoke arg and its raw params from `invoke_arg_dir`.

        This functions opens and parses the raw memory dump of a
        `tee_ioctl_invoke_arg` struct and turns it into a Python
        `TeeIoctlInvokeArg` object.
        It also trys to find raw memory dumps of parameters by searching for
        files following the naming convention in `PARAMS`.
        These parameters are turned into `TeeIoctlParam` objects and added
        to the invoke arg.

        Args:
            `invoke_arg_dir`: filename pointing to the raw memory dump of a
                               `tee_ioctl_invoke_arg`

        Returns:
            The deserialized invoke arg.
        """
        invoke_arg_path = os.path.join(invoke_arg_dir, cls.INVOKE_ARG_PREFIX)
        with open(invoke_arg_path, "rb") as f:
            invoke_arg = TeeIoctlInvokeArg._deserialize_raw(f.read())
            for param in invoke_arg.c_struct.params:
                p = TeeIoctlParam.deserialize_raw(bytes(param))
                invoke_arg.params.append(p)

        invoke_arg._load_params_from_folder(invoke_arg_dir)
        invoke_arg.sanity_check()

        return invoke_arg

    def _load_params_from_folder(self, folder_path: str):
        """Loads parameter contents and types from a folder.

        This functions loads parameter values from the files in folder_path.
        It searches for the parameter expected by the invoke arg `self`.

        Args:
            folder_path: path to folder containing raw params
        """
        for i, param in enumerate(self.params):
            if param.attr == optee.TEEC_ParamType.TEEC_NONE:
                continue

            # get data
            param_data_path = os.path.join(
                folder_path, TeeIoctlInvokeArg.PARAMS[i][3]
            )
            if os.path.exists(param_data_path):
                with open(param_data_path, "rb") as f:
                    param.data = f.read()
                param.data_paths = [param_data_path]
            else:
                param.data = None
                param.data_paths = []

            # get types for data
            tmp_filename = "{}{}".format(
                TeeIoctlInvokeArg.PARAMS[i][3], TeeIoctlInvokeArg.TYPES_EXT
            )
            param_data_types_path = os.path.join(folder_path, tmp_filename)
            if os.path.exists(param_data_types_path):
                with open(param_data_types_path, "rb") as f:
                    param.types: SeedTemplate = pickle.load(f)
            else:
                param.types = None

            if param.types and (param.types.size != len(param.data)):
                # sanity check, investigate during debug
                import ipdb

                ipdb.set_trace()
                # TODO: substitute with assertion

        return

    def deserialize(self):
        return self.deserialize_obj(self)

    @classmethod
    def deserialize_obj(cls, buf):
        f = BytesIO(buf)
        sz = u32(f.read(4))

        if sz != TeeIoctlInvokeArg.SIZE:
            raise TeeIoctlInvokeArgSerializationException("Error: wrong size.")

        invoke_arg = cls._deserialize_raw(f.read(TeeIoctlInvokeArg.SIZE))

        # update params
        for param in invoke_arg.c_struct.params:
            invoke_arg.params.append(
                TeeIoctlParam.deserialize_raw(bytes(param))
            )

        if invoke_arg.ret != optee.OPTEEReturnStatus.TEEC_SUCCESS:
            # do not try to parse if return status is not successful
            return invoke_arg

        # update output params
        for idx, param in enumerate(invoke_arg.params):
            if param.attr in TeeIoctlParam.VALUE_OUTPUT_TYPES:
                sz = u32(f.read(4))
                if sz != 4:
                    raise TeeIoctlInvokeArgSerializationException(
                        "We expect 8 bytes for a value param here."
                    )
                param.a = f.read(4)
                param.b = f.read(4)
            elif param.attr in TeeIoctlParam.MEMREF_OUTPUT_TYPES:
                sz = u32(f.read(4))
                param.data = f.read(sz)
            else:
                # NONE and INPUT param types should have size of 0
                sz = u32(f.read(4))
                if sz != 0:
                    raise TeeIoctlInvokeArgSerializationException(
                        "We do not expect to deserialize input params."
                    )
        return invoke_arg

    @classmethod
    def _deserialize_raw(cls, buf):
        """buf is supposed to contain the raw tee_ioctl_invoke_arg struct"""

        assert (
            len(buf) == TeeIoctlInvokeArg.SIZE
        ), "sizeof(struct tee_ioctl_invoke_arg) is {}, but len(buf)={}".format(
            TeeIoctlInvokeArg.SIZE, len(buf)
        )

        invoke_arg = cls()
        invoke_arg.c_struct = cTeeIoctlInvokeArg.from_buffer_copy(buf)
        return invoke_arg

    def serialize_to_path(self, invoke_arg_dir):
        self.serialize_obj_to_path(self, invoke_arg_dir)

    @classmethod
    def serialize_obj_to_path(cls, invoke_arg, invoke_arg_dir):
        arg_buf = cls._serialize_raw(invoke_arg)
        with open(
            os.path.join(invoke_arg_dir, TeeIoctlInvokeArg.INVOKE_ARG_PREFIX),
            "wb",
        ) as f:
            f.write(arg_buf)

        for i, param in enumerate(invoke_arg.params):
            if param.attr == optee.TEEC_ParamType.TEEC_NONE:
                continue

            param_data_path = os.path.join(
                invoke_arg_dir, TeeIoctlInvokeArg.PARAMS[i][3]
            )

            # store data
            if param.data:
                with open(param_data_path, "wb") as f:
                    f.write(param.data)

            # store types
            if param.types:
                with open(f"{param_data_path}.types", "wb") as f:
                    pickle.dump(param.types, f)

            if param.types and (param.types.size != len(param.data)):
                # sanity check, investigate during debug
                import ipdb

                ipdb.set_trace()
                # TODO: substitute with assertion

    def sanity_check(self):
        for i, param in enumerate(self.params):
            if param.types and (param.types.size != len(param.data)):
                # sanity check, investigate during debug
                import ipdb

                ipdb.set_trace()
                # TODO: substitute with assertion

    @classmethod
    def _serialize_raw(cls, invoke_arg):
        """Creates a chunk of raw memory from `invoke_arg`
        (`TeeIoctlInvokeArg`)"""

        buf = bytes(invoke_arg.c_struct)

        assert (
            len(buf) == TeeIoctlInvokeArg.SIZE
        ), "sizeof(struct tee_ioctl_invoke_arg ) is {}, but len(buf)={}".format(
            TeeIoctlInvokeArg.SIZE, len(buf)
        )

        return buf

    def serialize(self):
        return self.serialize_obj(self)

    @classmethod
    def serialize_obj(cls, invoke_arg):
        """Converts a `TeeIoctlInvokeArg` Python object to its raw
           representation.

        This functions opens and parses a `TeeIoctlInvokeArg` Python object
        from `invoke_arg` and converts it to its raw representation.

        Args:
            `invoke_arg`: filename pointing a `TeeIoctlInvokeArg` Python object

        Returns:
            A Python `bytes` object containing `invoke_arg` and its params.
            The format is the following:

            cTeeIoctlInvokeArg
            {% for param in cTeeIoctlInvokeArg.params: %}
                    uint64_t param.sz
                    uint8_t param.data
        """

        out = invoke_arg._serialize_raw(invoke_arg)
        out += p32(invoke_arg.get_param_types())

        for idx, param in enumerate(invoke_arg.params):
            if param.attr in TeeIoctlParam.VALUE_TYPES:
                out += p32(param.a)
                out += p32(param.b)
            elif param.attr in TeeIoctlParam.MEMREF_TYPES:
                if param.attr in TeeIoctlParam.MEMREF_INPUT_TYPES:
                    # TODO: support offset
                    if not param.data:
                        log.error(
                            f"Param {idx} is a memref_input_type, "
                            "we should have a buf here!"
                        )
                        return

                    # send actual size of buffer
                    out += p32(len(param.data))
                    # send content of buffer
                    out += param.data
                    # send signaled size of buffer
                    out += p32(param.b)
                else:
                    # send actual size of buffer
                    if param.data:
                        out += p32(len(param.data))
                    else:
                        out += p32(0x100)
                    # send size of buffer
                    out += p32(param.b)

            elif param.attr == TeeIoctlParam.TEE_IOCTL_PARAM_ATTR_TYPE_NONE:
                pass
            else:
                import ipdb

                ipdb.set_trace()
                raise NotImplementedError("This type is not known.")
        return out

    def __str__(self):
        out = "struct tee_ioctl_invoke_arg:\n"
        out += "{:<20} {}\n".format("func:", hex(self.func))
        out += "{:<20} {}\n".format("session:", hex(self.session))
        out += "{:<20} {}\n".format("cancel_id:", hex(self.cancel_id))
        out += "{:<20} {}\n".format("ret:", hex(self.ret))
        out += "{:<20} {}\n".format("ret_origin:", hex(self.ret_origin))
        out += "{:<20} {}\n".format("num_param:", hex(self.num_params))
        for idx, param in enumerate(self.params):
            out += "\n"
            out += f"## param {idx} ##\n"
            out += str(param)
        return out
