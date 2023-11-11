#ifndef _TC_NS_CLIENT_H_
#define _TC_NS_CLIENT_H_

#include <stdint.h>
#include <asm-generic/int-ll64.h>

#ifdef SECURITY_AUTH_ENHANCE
#define SCRAMBLING_KEY_LEN    4
#define TOKEN_BUFFER_LEN    42   /* token(32byte) + timestamp(8byte) + kernal_api(1byte) + sync(1byte)*/
#define TIMESTAMP_BUFFER_INDEX    32
#define KERNAL_API_INDEX    40
#define SYNC_INDEX    41
#define TIMESTAMP_LEN_DEFAULT \
	((KERNAL_API_INDEX) - (TIMESTAMP_BUFFER_INDEX))
#define KERNAL_API_LEN \
	((TOKEN_BUFFER_LEN) - (KERNAL_API_INDEX))
#define TIMESTAMP_SAVE_INDEX    16
#endif

#define TOKEN_SAVE_LEN    24
#define NPARAMS           4


//#define bool uint8_t

/****************************************************
 *      Return Codes
 ****************************************************/
enum TEEC_Result {
    TEEC_SUCCESS = 0x0,
    TEEC_ERROR_INVALID_CMD = 0x1,
    TEEC_ERROR_SERVICE_NOT_EXIST = 0x2,
    TEEC_ERROR_SESSION_NOT_EXIST = 0x3,
    TEEC_ERROR_GENERIC = 0xFFFF0000,
    TEEC_ERROR_ACCESS_DENIED = 0xFFFF0001,
    TEEC_ERROR_CANCEL = 0xFFFF0002,
    TEEC_ERROR_ACCESS_CONFLICT = 0xFFFF0003,
    TEEC_ERROR_EXCESS_DATA = 0xFFFF0004,
    TEEC_ERROR_BAD_FORMAT = 0xFFFF0005,
    TEEC_ERROR_BAD_PARAMETERS = 0xFFFF0006,
    TEEC_ERROR_BAD_STATE = 0xFFFF0007,
    TEEC_ERROR_ITEM_NOT_FOUND = 0xFFFF0008,
    TEEC_ERROR_NOT_IMPLEMENTED = 0xFFFF0009,
    TEEC_ERROR_NOT_SUPPORTED = 0xFFFF000A,
    TEEC_ERROR_NO_DATA = 0xFFFF000B,
    TEEC_ERROR_OUT_OF_MEMORY = 0xFFFF000C,
    TEEC_ERROR_BUSY = 0xFFFF000D,
    TEEC_ERROR_COMMUNICATION = 0xFFFF000E,
    TEEC_ERROR_SECURITY = 0xFFFF000F,
    TEEC_ERROR_SHORT_BUFFER = 0xFFFF0010,
    TEEC_PENDING = 0xFFFF2000,
    TEEC_PENDING2 = 0xFFFF2001,
    TEE_ERROR_TAGET_DEAD = 0xFFFF3024,
    TEE_ERROR_GT_DEAD = 0xFFFF3124,
    TEEC_ERROR_MAC_INVALID = 0xFFFF3071,
    TEEC_CLIENT_INTR = 0xFFFF4000,
};

/****************************************************
 *      Return Code Origins
 ****************************************************/
enum TEEC_ReturnCodeOrigin {
    TEEC_ORIGIN_API = 0x1,
    TEEC_ORIGIN_COMMS = 0x2,
    TEEC_ORIGIN_TEE = 0x3,
    TEEC_ORIGIN_TRUSTED_APP = 0x4,
};

/****************************************************
 *      Shared Memory Control
 ****************************************************/
enum TEEC_SharedMemCtl {
    TEEC_MEM_INPUT = 0x1,
    TEEC_MEM_OUTPUT = 0x2,
    TEEC_MEM_INOUT = 0x3,
};

/****************************************************
 *      API Parameter Types
 ****************************************************/
enum TEEC_ParamType {
    TEEC_NONE = 0x0,
    TEEC_VALUE_INPUT = 0x01,
    TEEC_VALUE_OUTPUT = 0x02,
    TEEC_VALUE_INOUT = 0x03,
    TEEC_MEMREF_TEMP_INPUT = 0x05,
    TEEC_MEMREF_TEMP_OUTPUT = 0x06,
    TEEC_MEMREF_TEMP_INOUT = 0x07,
    TEEC_MEMREF_WHOLE = 0xc,
    TEEC_MEMREF_PARTIAL_INPUT = 0xd,
    TEEC_MEMREF_PARTIAL_OUTPUT = 0xe,
    TEEC_MEMREF_PARTIAL_INOUT = 0xf
};
enum TEE_ParamType {
    TEE_PARAM_TYPE_NONE = 0x0,
    TEE_PARAM_TYPE_VALUE_INPUT = 0x1,
    TEE_PARAM_TYPE_VALUE_OUTPUT = 0x2,
    TEE_PARAM_TYPE_VALUE_INOUT = 0x3,
    TEE_PARAM_TYPE_MEMREF_INPUT = 0x5,
    TEE_PARAM_TYPE_MEMREF_OUTPUT = 0x6,
    TEE_PARAM_TYPE_MEMREF_INOUT = 0x7,
};

/****************************************************
 *      Session Login Methods
 ****************************************************/
enum TEEC_LoginMethod {
    TEEC_LOGIN_PUBLIC = 0x0,
    TEEC_LOGIN_USER,
    TEEC_LOGIN_GROUP,
    TEEC_LOGIN_APPLICATION = 0x4,
    TEEC_LOGIN_USER_APPLICATION = 0x5,
    TEEC_LOGIN_GROUP_APPLICATION = 0x6,
    TEEC_LOGIN_IDENTIFY = 0x7,
};

typedef struct {
    __u32 method;
    __u32 mdata;
} TC_NS_ClientLogin;

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

typedef struct {
    __u32 code;
    __u32 origin;
} TC_NS_ClientReturn;

typedef struct {
    unsigned char uuid[16];
    __u32 session_id;
    __u32 cmd_id;
    TC_NS_ClientReturn returns;
    TC_NS_ClientLogin login;
    TC_NS_ClientParam params[NPARAMS];
    __u32 paramTypes;
    __u8 started;
#ifdef SECURITY_AUTH_ENHANCE
	void* teec_token;
#endif
} TC_NS_ClientContext;

typedef struct {
    uint32_t seconds;
    uint32_t millis;
} TC_NS_Time;

#define TEEC_PARAM_TYPES( param0Type, param1Type, param2Type, param3Type) \
        ((param3Type) << 12 | (param2Type) << 8 | (param1Type) << 4 | (param0Type))

#define TEEC_PARAM_TYPE_GET( paramTypes, index) \
        (((paramTypes) >> (4*(index))) & 0x0F)

#define TC_NS_CLIENT_IOC_MAGIC  't'
#define TC_NS_CLIENT_DEV            "tc_ns_client"
#define TC_NS_CLIENT_DEV_NAME   "/dev/tc_ns_client"

#define	vmalloc_addr_valid(kaddr)	(((void *)(kaddr) >= (void *)VMALLOC_START) && \
					((void *)(kaddr) < (void *)VMALLOC_END))
#define IMG_LOAD_FIND_NO_DEV_ID  0xFFFF00A5
#define IMG_LOAD_FIND_NO_SHARE_MEM 0xFFFF00A6
#define IMG_LOAD_SECURE_RET_ERROR 0xFFFF00A7

#define TST_CMD_01 (1)
#define TST_CMD_02 (2)
#define TST_CMD_03 (3)
#define TST_CMD_04 (4)
#define TST_CMD_05 (5)

#define TC_NS_CLIENT_IOCTL_SES_OPEN_REQ \
    _IOW(TC_NS_CLIENT_IOC_MAGIC, 1, TC_NS_ClientContext)
#define TC_NS_CLIENT_IOCTL_SES_CLOSE_REQ \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 2, TC_NS_ClientContext)
#define TC_NS_CLIENT_IOCTL_SEND_CMD_REQ \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 3, TC_NS_ClientContext)
#define TC_NS_CLIENT_IOCTL_SHRD_MEM_RELEASE \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 4, unsigned int)
#define TC_NS_CLIENT_IOCTL_WAIT_EVENT \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 5, unsigned int)
#define TC_NS_CLIENT_IOCTL_SEND_EVENT_REPONSE \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 6, unsigned int)
#define TC_NS_CLIENT_IOCTL_REGISTER_AGENT \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 7, unsigned int)
#define TC_NS_CLIENT_IOCTL_UNREGISTER_AGENT \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 8, unsigned int)
#define TC_NS_CLIENT_IOCTL_LOAD_APP_REQ \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 9, TC_NS_ClientContext)
#define TC_NS_CLIENT_IOCTL_NEED_LOAD_APP \
    _IOWR(TC_NS_CLIENT_IOC_MAGIC, 10, TC_NS_ClientContext)
#define TC_NS_CLIENT_IOCTL_LOAD_APP_EXCEPT \
	_IOWR(TC_NS_CLIENT_IOC_MAGIC, 11, unsigned int)
#define TC_NS_CLIENT_IOCTL_ALLOC_EXCEPTING_MEM \
        _IOWR(TC_NS_CLIENT_IOC_MAGIC, 12, unsigned int)
#define TC_NS_CLIENT_IOCTL_CANCEL_CMD_REQ \
        _IOWR(TC_NS_CLIENT_IOC_MAGIC, 13, TC_NS_ClientContext)
#define TC_NS_CLIENT_IOCTL_LOGIN \
        _IOWR(TC_NS_CLIENT_IOC_MAGIC, 14, int)
#define TC_NS_CLIENT_IOCTL_TST_CMD_REQ \
        _IOWR(TC_NS_CLIENT_IOC_MAGIC, 15, int)
#define TC_NS_CLIENT_IOCTL_TUI_EVENT \
        _IOWR(TC_NS_CLIENT_IOC_MAGIC, 16, int)
#define TC_NS_CLIENT_IOCTL_SYC_SYS_TIME \
        _IOWR(TC_NS_CLIENT_IOC_MAGIC, 17, TC_NS_Time)
#endif
