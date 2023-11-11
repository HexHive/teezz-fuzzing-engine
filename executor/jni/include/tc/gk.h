#ifndef _GK_H_
#define _GK_H_

enum GK_CMD_ID {
    GK_CMD_ID_ENROLL = 0x1,
    GK_CMD_ID_VERIFY = 0x2,
};

//
struct ENROLL_PARAM_2_IN_BUF {
    char password[4];
};

struct ENROLL_PARAM_3_IN_BUF {
    uint64_t zero;
    uint8_t unknown[]; // zero when password is not set
};

struct ENROLL_PARAM_3_OUT_BUF {
    uint8_t weirdBlockFromHDD[1]; // /data/system/gatekeeper.password.key
};

struct VERIFY_PARAM_0_IN_VALUES {
    uint64_t value_a; // zero
    uint64_t value_b; // zero
};

struct VERIFY_PARAM_1_IN_BUF {
    uint8_t weirdBlockFromHDD[1000]; // /data/system/gatekeeper.password.key
};

struct VERIFY_PARAM_2_IN_BUF {
    char password[4];
};

struct VERIFY_PARAM_3_IN_BUF {
    uint64_t challenge;
    uint8_t zero[]; // /data/system/gatekeeper.password.key
};

#endif
