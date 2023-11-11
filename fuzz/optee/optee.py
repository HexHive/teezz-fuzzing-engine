def get_param_type(param_num, invoke):
    assert param_num >= 0
    if param_num < invoke.num_params:
        return invoke.params[param_num].attr


TEE_IOC_MAGIC = 0xa4


class OPTEE_CMDID:
    TEE_IOC_VERSION = 0x800ca400
    TEE_IOC_SHM_ALLOC = 0xc010a401
    TEE_IOC_SHM_REGISTER_FD = 0xc018a408
    TEE_IOC_SHM_REGISTER = 0xc018a409
    TEE_IOC_OPEN_SESSION = 0x8010a402
    TEE_IOC_INVOKE = 0x8010a403
    TEE_IOC_CANCEL = 0x8008a404
    TEE_IOC_CLOSE_SESSION = 0x8004a405
    TEE_IOC_SUPPL_RECV = 0x8010a406
    TEE_IOC_SUPPL_SEND = 0x8010a407


OPTEE_CMDID_dict = \
    {v: k for k, v in OPTEE_CMDID.__dict__.items() if isinstance(v, int)}


class OPTEEReturnStatus(object):
    TEEC_SUCCESS = 0x00000000
    TEEC_ERROR_GENERIC = 0xFFFF0000
    TEEC_ERROR_ACCESS_DENIED = 0xFFFF0001
    TEEC_ERROR_CANCEL = 0xFFFF0002
    TEEC_ERROR_ACCESS_CONFLICT = 0xFFFF0003
    TEEC_ERROR_EXCESS_DATA = 0xFFFF0004
    TEEC_ERROR_BAD_FORMAT = 0xFFFF0005
    TEEC_ERROR_BAD_PARAMETERS = 0xFFFF0006
    TEEC_ERROR_BAD_STATE = 0xFFFF0007
    TEEC_ERROR_ITEM_NOT_FOUND = 0xFFFF0008
    TEEC_ERROR_NOT_IMPLEMENTED = 0xFFFF0009
    TEEC_ERROR_NOT_SUPPORTED = 0xFFFF000A
    TEEC_ERROR_NO_DATA = 0xFFFF000B
    TEEC_ERROR_OUT_OF_MEMORY = 0xFFFF000C
    TEEC_ERROR_BUSY = 0xFFFF000D
    TEEC_ERROR_COMMUNICATION = 0xFFFF000E
    TEEC_ERROR_SECURITY = 0xFFFF000F
    TEEC_ERROR_SHORT_BUFFER = 0xFFFF0010
    TEEC_ERROR_EXTERNAL_CANCEL = 0xFFFF0011
    TEEC_ERROR_TARGET_DEAD = 0xFFFF3024

    _CODE2LABEL = None

    @classmethod
    def code2label(cls, code):
        """ Try to return the string representation of the numerical return
            code `code`. If the code is unknown, we return the hex string. """
        if code in cls._CODE2LABEL.keys():
            return cls._CODE2LABEL[code]
        else:
            return hex(code)


OPTEEReturnStatus._CODE2LABEL = \
    {v: k for k, v in OPTEEReturnStatus.__dict__.items() if isinstance(v, int)}


class OPTEEReturnOrigin(object):
    TEEC_ORIGIN_API = 0x00000001
    TEEC_ORIGIN_COMMS = 0x00000002
    TEEC_ORIGIN_TEE = 0x00000003
    TEEC_ORIGIN_TRUSTED_APP = 0x00000004


OPTEEReturnOrigin_dict = \
    {v: k for k, v in OPTEEReturnOrigin.__dict__.items() if isinstance(v, int)}


class TEEC_ParamType:
    TEEC_NONE = 0x0
    TEEC_VALUE_INPUT = 0x01
    TEEC_VALUE_OUTPUT = 0x02
    TEEC_VALUE_INOUT = 0x03
    TEEC_MEMREF_TEMP_INPUT = 0x05
    TEEC_MEMREF_TEMP_OUTPUT = 0x06
    TEEC_MEMREF_TEMP_INOUT = 0x07
    TEEC_ION_INPUT = 0x08
    TEEC_MEMREF_WHOLE = 0xc
    TEEC_MEMREF_PARTIAL_INPUT = 0xd
    TEEC_MEMREF_PARTIAL_OUTPUT = 0xe
    TEEC_MEMREF_PARTIAL_INOUT = 0xf


TEEC_ParamType_dict = \
        {v: k for k, v in TEEC_ParamType.__dict__.items()
            if 'TEE' in k and isinstance(v, int)}
