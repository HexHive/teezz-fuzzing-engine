#ifndef _QSEE_H_
#define _QSEE_H_

#include <qsee/QSEEComAPI.h>

/*
 * @brief: Definition of a handle to manage the data needed to use the QSEECom
 * API.
 *         - qseecom: The pointer to QSEECom_handle struct which will hold
 *                    the shared buffer after initialization by
 * QSEECom_start_app- or QSEECom_register_listener_request. This does kind of
 * like identify the origin of a call to the API and therefor it is needed for
 * each following API call.
 *         - libhandle: Place for a reference to the API library
 *         - function pointers to hold a reference into the API shared object
 */

#define QSEECOM_SEND_CMD_REQ 0x1
#define QSEECOM_SEND_MODFD_CMD_REQ 0x2
#define QSEECOM_USE_OLD_SHARED 0xABCDABCD

#define FNAME_NAME_MAX_SIZE 256
#define PATH_MAX_SIZE 256

struct qcom_my_handle
{
    struct QSEECom_handle *qseecom;
    void *libhandle;
    int (*QSEECom_start_app)(struct QSEECom_handle **handle, char *path,
                             char *appname, uint32_t size);
    int (*QSEECom_shutdown_app)(struct QSEECom_handle **handle);
    int (*QSEECom_register_listener)(struct QSEECom_handle **handle,
                                     uint32_t lstnr_id, uint32_t sb_length,
                                     uint32_t flags);
    int (*QSEECom_unregister_listener)(struct QSEECom_handle *handle);
    int (*QSEECom_send_cmd)(struct QSEECom_handle *handle, void *cbuf,
                            uint32_t clen, void *rbuf, uint32_t rlen);
    int (*QSEECom_send_modified_cmd)(struct QSEECom_handle *handle, void *cbuf,
                                     uint32_t clen, void *rbuf, uint32_t rlen,
                                     struct QSEECom_ion_fd_info *ihandle);
    int (*QSEECom_receive_req)(struct QSEECom_handle *handle, void *buf,
                               uint32_t len);
    int (*QSEECom_send_resp)(struct QSEECom_handle *handle, void *send_buf,
                             uint32_t len);
    int (*QSEECom_set_bandwidth)(struct QSEECom_handle *handle, bool high);
    int (*QSEECom_app_load_query)(struct QSEECom_handle *handle,
                                  char *app_name);
};
typedef struct qcom_my_handle qcom_my_handle_t;

qcom_my_handle_t *init_qcom_my_handle();

typedef struct qsee_state
{
    qcom_my_handle_t *libteec;
    uint32_t sb_size;
    char path[PATH_MAX_SIZE];
    char fname[FNAME_NAME_MAX_SIZE];
    struct timespec start;
} qsee_state_t;

#endif // _QSEE_H_
