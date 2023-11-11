#ifndef _EXECUTOR_H_
#define _EXECUTOR_H_

#define TARGET_QSEE "qsee"
#define TARGET_TC "tc"
#define TARGET_OPTEE "optee"

#define TEEZZ_CMD_START 0x01
#define TEEZZ_CMD_SEND 0x02
#define TEEZZ_CMD_END 0x03
#define TEEZZ_CMD_TERMINATE 0x04

enum EXECUTOR_STATUS {
    EXECUTOR_SUCCESS = 42,
    EXECUTOR_ERROR = 1
};

typedef struct teezz_ops {
    int (*init) (void);
    int (*pre_execute) (int status_stock);
    int (*execute) (int data_sock);
    int (*post_execute) (int status_sock);
    int (*deinit) (void);
} teezz_ops_t;

#endif // _EXECUTOR_H_

