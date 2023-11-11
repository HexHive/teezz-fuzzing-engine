def get_param_type(param_num, val):
    assert param_num >= 0 and param_num < 4
    return (val >> (param_num * 4)) & 0xf


TC_MAGIC = 0x74
SIZE_TC_NS_ClientContext = 0x98  #  0x90 (older) vs 0x98 (newer)


class TC_CMDID:
    TC_NS_CLIENT_IOCTL_SES_OPEN_REQ = (0x40 << 24) | (
        SIZE_TC_NS_ClientContext << 16) | (TC_MAGIC << 8) | 1
    TC_NS_CLIENT_IOCTL_SES_CLOSE_REQ = (0xc0 << 24) | (
        SIZE_TC_NS_ClientContext << 16) | (TC_MAGIC << 8) | 2
    TC_NS_CLIENT_IOCTL_SEND_CMD_REQ = (0xc0 << 24) | (
        SIZE_TC_NS_ClientContext << 16) | (TC_MAGIC << 8) | 3
    TC_NS_CLIENT_IOCTL_SHRD_MEM_RELEASE = (TC_MAGIC << 8) | 4
    TC_NS_CLIENT_IOCTL_WAIT_EVENT = (0xc0 << 24) | (4 << 16) | (
        TC_MAGIC << 8) | 5
    TC_NS_CLIENT_IOCTL_SEND_EVENT_REPONSE = (0xc0 << 24) | (4 << 16) | (
        TC_MAGIC << 8) | 6
    TC_NS_CLIENT_IOCTL_REGISTER_AGENT = (0xc0 << 24) | (4 << 16) | (
        TC_MAGIC << 8) | 7
    TC_NS_CLIENT_IOCTL_UNREGISTER_AGENT = (0xc0 << 24) | (0x4 << 16) | (
        TC_MAGIC << 8) | 8
    TC_NS_CLIENT_IOCTL_LOAD_APP_REQ = (0xc0 << 24) | (
        SIZE_TC_NS_ClientContext << 16) | (TC_MAGIC << 8) | 9
    TC_NS_CLIENT_IOCTL_NEED_LOAD_APP = (0xc0 << 24) | (
        SIZE_TC_NS_ClientContext << 16) | (TC_MAGIC << 8) | 0x0a
    TC_NS_CLIENT_IOCTL_LOAD_APP_EXCEPT = (0xc0 << 24) | (4 << 16) | (
        TC_MAGIC << 8) | 0x0b
    TC_NS_CLIENT_IOCTL_ALLOC_EXCEPTING_MEM = (0xc0 << 24) | (4 << 16) | (
        TC_MAGIC << 8) | 0x0c
    TC_NS_CLIENT_IOCTL_CANCEL_CMD_REQ = (0xc0 << 24) | (
        SIZE_TC_NS_ClientContext << 16) | (TC_MAGIC << 8) | 0x0d
    TC_NS_CLIENT_IOCTL_LOGIN = (0xc0 << 24) | (0x04 << 16) | (
        TC_MAGIC << 8) | 0x0e
    TC_NS_CLIENT_IOCTL_TST_CMD_REQ = (0xc0 << 24) | (0x04 << 16) | (
        TC_MAGIC << 8) | 0x0f
    TC_NS_CLIENT_IOCTL_TUI_EVENT = (0xc0 << 24) | (0x04 << 16) | (
        TC_MAGIC << 8) | 0x10
    TC_NS_CLIENT_IOCTL_SYC_SYS_TIME = (0xc0 << 24) | (0x08 << 16) | (
        TC_MAGIC << 8) | 0x11


TC_CMDID_dict = \
    {v: k for k, v in TC_CMDID.__dict__.items() if isinstance(v, int)}


class TC_CMDID_P20Lite(TC_CMDID):
    TC_NS_CLIENT_IOCTL_LOAD_APP_REQ = (0xc0 << 24) | (0x20 << 16) | (
        TC_MAGIC << 8) | 0x9
    TC_NS_CLIENT_IOCTL_SET_NATIVE_IDENTITY = (0xc0 << 24) | (0x4 << 16) | (
        TC_MAGIC << 8) | 0x12
    TC_NS_CLIENT_IOCTL_LOAD_TTF_FILE = (0xc0 << 24) | (0x4 << 16) | (
        TC_MAGIC << 8) | 0x13


TC_CMDID_P20Lite_dict = dict(TC_CMDID_dict)
TC_CMDID_P20Lite_dict.update(
    {v: k
     for k, v in TC_CMDID_P20Lite.__dict__.items() if isinstance(v, int)})


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


TEEC_ParamType_dict = {
    v: k
    for k, v in TEEC_ParamType.__dict__.items()
    if 'TEE' in k and isinstance(v, int)
}


class TEEC_ReturnCode:
    TEEC_SUCCESS = 0x0
    TEEC_ERROR_INVALID_CMD = 0x1
    TEEC_ERROR_SERVICE_NOT_EXIST = 0x2
    TEEC_ERROR_SESSION_NOT_EXIST = 0x3
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
    TEEC_PENDING = 0xFFFF2000
    TEEC_PENDING2 = 0xFFFF2001
    TEE_ERROR_TAGET_DEAD = 0xFFFF3024
    TEE_ERROR_GT_DEAD = 0xFFFF3124
    TEEC_ERROR_MAC_INVALID = 0xFFFF3071
    TEEC_CLIENT_INTR = 0xFFFF4000
    TEEC_ERROR_FP_UNKNOWN = 0xFFFF5002  # Custom return code found in fp binary
    TEE_ERROR_CA_AUTH_FAIL = 0xFFFFCFE5
    TEE_ERROR_KM_UNKNOWN1 = 0xffffffbe  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN2 = 0xffffffc5  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN3 = 0xffffffc7  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN4 = 0xffffffd4  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN5 = 0xffffffd8  # Custom return code found in km binary
    TEE_ERROR_KM_UNSUPPORTED_TAG = 0xffffffd9
    TEE_ERROR_KM_UNKNOWN_D7 = 0xffffffd7
    TEE_ERROR_KM_UNKNOWN6 = 0xffffffe4  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN7 = 0xffffffe7  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN8 = 0xfffffff6  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN9 = 0xfffffff3  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN10 = 0xfffffff4  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN11 = 0xfffffff5  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN12 = 0xfffffff8  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN13 = 0xfffffffa  # Custom return code found in km binary
    TEE_ERROR_KM_UNKNOWN14 = 0xfffffffd  # Custom return code found in km binary
    TEE_CODE_NOT_SET = 0xDEADBEEF


TEEC_ReturnCode_dict = \
        {v: k for k, v in TEEC_ReturnCode.__dict__.items() \
        if 'TEE' in k and isinstance(v, int)}


class TEEC_ReturnCodeOrigin:
    TEEC_DUNNO_WHAT_THIS_IS = 0x0  # TODO: investigate this
    TEEC_ORIGIN_API = 0x1
    TEEC_ORIGIN_COMMS = 0x2
    TEEC_ORIGIN_TEE = 0x3
    TEEC_ORIGIN_TRUSTED_APP = 0x4
    TEEC_ORIGIN_NOT_SET = 0xDEADC0DE


TEEC_ReturnCodeOrigin_dict = \
        {v: k for k,v in TEEC_ReturnCodeOrigin.__dict__.items() \
        if 'TEE' in k and isinstance(v, int)}
"""
KEYMASTER
"""

KEYMASTER_UUID = '\x07' * 16


class SVC_KEYMASTER_CMD_ID:
    KM_CMD_ID_INVALID = 0x0
    KM_CMD_ID_GENERATE_KEYPAIR = 0x1
    KM_CMD_ID_GET_PUBLIC_KEY = 0x2
    KM_CMD_ID_IMPORT_KEYPAIR = 0x3
    KM_CMD_ID_SIGN_DATA = 0x4
    KM_CMD_ID_VERIFY_DATA = 0x5
    KM_INIT_ABILITY = 0x6
    KM_CMD_ID_GENERATE_KEY = 0x7
    KM_GET_KEY_CHARACTERISTICS = 0x8
    KM_IMPORT_KEY = 0x9
    KM_EXPORT_KEY = 0xA
    KM_BEGIN = 0xB
    KM_UPDATE = 0xC
    KM_FINISH = 0xD
    KM_ABORT = 0xE
    KM_GET_ROT = 0x20
    KM_GENERATE_ROT = 0x21

SVC_KEYMASTER_CMD_ID_dict = \
    {v: k for k, v in SVC_KEYMASTER_CMD_ID.__dict__.items() if isinstance(v, int)}
