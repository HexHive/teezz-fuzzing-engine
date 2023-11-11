#ifndef _TC_H_
#define _TC_H_

#include <time.h>
#include <tc/teek_client_id.h>
#include <tc/teek_client_type.h>
#include <sys/types.h>
#include <tc/tc_ns_client.h>


#define PARAM_OFF 4
#define BUF_SIZE 0x3000
#define PRESET_RETURN_CODE 0xDEADBEEF
#define PRESET_RETURN_ORIGIN 0xDEADC0DE
#define AUTH_TOKEN_SIZE 0x45

// TODO: figure out max len from drivers/hisi/tzdriver/tc_client_driver.c
#define LOGIN_BLOB_MAX_SZ 2048
#define PROCESS_NAME_MAX_SIZE 256

#define FP_UUID                                                                \
    "\x00\x3d\x2b\xa3\x57\xcb\xe3\x11\x9c\x1a\x08\x00\x20\x0c\x9a\x66"
#define GK_UUID                                                                \
    "\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b\x0b"

#define LOGIN_BUF_FINGERPRINTD                                                 \
    "\x18\x00\x00\x00/system/bin/fingerprintd"                                 \
    "\x04\x00\x00\x00\xe8\x03\x00\x00"
#define LOGIN_BUF_GATEKEEPERD                                                  \
    "\x2e\x00\x00\x00/system/bin/gatekeeperd\x00"                              \
    "/data/misc/gatekee\x00\x00\x00\x00"                                       \
    "\x04\x00\x00\x00\xe8\x03\x00\x00"

typedef struct tc_state {
    int fd;
    TC_NS_ClientContext ctx;  // uuid
    char login_blob[LOGIN_BLOB_MAX_SZ];
    uid_t uid;
    char process_name[PROCESS_NAME_MAX_SIZE];
    struct timespec start;
} tc_state_t;

#endif // _TC_H_
