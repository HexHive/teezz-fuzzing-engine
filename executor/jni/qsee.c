#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <include/qsee_shmem.h>
#include <logging.h>
#include <qsee/QSEEComAPI.h> // libQSEEComAPI.so
#include <qsee/qsee.h>       // own stuff
#include <qsee/qseecom.h>    // kernel source
#include <executor.h>
#include <utils.h>

#include <ion/ion.h>

qsee_state_t QSEE_STATE = {0};

// global shared buffer
struct ion_info *iinfo_shm = NULL;

/**
 * @brief Open a handle to the  QSEECom device.
 *
 * @param[in/out] handle The device handle
 * @param[in] path Path of .mdt on RichOS disk (without .mdt suffix)
 * @param[in] fname The directory and filename to load. TODO: just file basename
 * or whole path?
 * @param[in] sb_size Size of the shared buffer memory  for sending requests.
 * @return Zero on success, negative on failure. errno will be set on
 *  error.
 */
int qsee_init_ta(qcom_my_handle_t **my_handle_ptr, char *path, char *fname,
                 uint32_t sb_size)
{
    qcom_my_handle_t *my_handle = NULL;
    int ret = 0;
    // Initialize the handle for QSEEComAPI use
    *my_handle_ptr = init_qcom_my_handle();
    my_handle = *my_handle_ptr;
    if (my_handle == NULL)
    {
        LOGE("Error at init_qcom_my_handle!\n");
        return -1;
    }

    ret =
        my_handle->QSEECom_start_app(&my_handle->qseecom, path, fname, sb_size);
    if (ret)
    {
        LOGE("QSEECom_start_app failed.\n");
        goto cleanup;
    }
    // check if TA already loaded
    ret = my_handle->QSEECom_app_load_query(my_handle->qseecom, fname);
    if (ret != QSEECOM_APP_ALREADY_LOADED)
    {
        if (ret == QSEECOM_APP_QUERY_FAILED)
        {
            LOGE("QSEECOM_APP_QUERY_FAILED\n");
        }
        else if (ret == QSEECOM_APP_NOT_LOADED)
        {
            LOGE("Implement me!\n");
            // TODO: get path, fname, sb_size from remote
            // ret = (*my_handle->QSEECom_start_app)((struct QSEECom_handle **)
            // &my_handle->qseecom,
            //             path, fname, sb_size);
            // if (ret)
            //{
            //    printf("    Loading \"%s\" failed!\n", fname);
            //    goto cleanup;
            //}
            // printf("    Loading \"%s\" succeeded!\n", fname);
        }
        else
        {
            LOGE("QSEECom_app_load_query return status unknown 0x%x\n", ret);
        }
    }
    else
    {
        // ta already loaded
        ret = 0;
    }

cleanup:
    if (ret < 0)
        free(my_handle);
    return ret;
}

int qsee_get_req(int client_sock, char *req_buf, ssize_t *req_size)
{
    ssize_t nread = 0;
    int ret = 0;
    char *req_buf_tmp = NULL;
    if ((nread = read_data_log("req buffer", client_sock, &req_buf_tmp)) ==
        -1)
    {
        ret = -1;
    }
    *req_size = nread;
    memcpy(req_buf, req_buf_tmp, *req_size);
    free(req_buf_tmp);
    return ret;
}

int qsee_get_shared(int client_sock, char *shared_buf, ssize_t *shared_size)
{
    ssize_t nread = 0;
    int ret = 0;
    char *shared_buf_tmp = NULL;
    if ((nread = read_data_log("shared buffer", client_sock, &shared_buf_tmp)) ==
        -1)
    {
        ret = -1;
    }
    // for shared buffer -> if special value is received use existing buffer
    if (nread == sizeof(uint32_t) && *((uint32_t *)shared_buf_tmp) ==
                                         QSEECOM_USE_OLD_SHARED)
        return 0;

    *shared_size = nread;
    memcpy(shared_buf, shared_buf_tmp, *shared_size);
    free(shared_buf_tmp);
    return ret;
}

int qsee_get_resp_buf_size(int client_sock, ssize_t *resp_size)
{
    int ret = 0;
    ssize_t nread = 0;
    char *resp_size_buf = 0;
    if ((nread = read_data_log("resp buffer", client_sock, &resp_size_buf)) ==
        -1)
    {
        ret = -1;
        goto exit;
    }

    if (nread != sizeof(uint32_t))
    {
        LOGE("nread should be %zd but is %zd\n", sizeof(uint32_t), nread);
        ret = -1;
        goto exit;
    }

    *resp_size = *((uint32_t *)resp_size_buf);
exit:
    return ret;
}

/*
QSEECom_send_modified_cmd(struct QSEECom_handle *handle, void *send_buf,
                        uint32_t sbuf_len, void *resp_buf, uint32_t rbuf_len,
                        struct QSEECom_ion_fd_info  *ifd_data)

struct QSEECom_ion_fd_data {
        int32_t fd;
        uint32_t cmd_buf_offset;
};
struct QSEECom_ion_fd_info {
        struct QSEECom_ion_fd_data data[4];
};
*/
uint64_t fpc_get_challenge(qcom_my_handle_t *my_handle)
{
    int ret = 0;

    struct QSEECom_handle *handle = my_handle->qseecom;
    struct QSEECom_ion_fd_info ifd_data = {0};

    ssize_t req_size = 64;
    ssize_t resp_size = 64;

    // TODO: dealloc finger memory
    struct ion_info *ion_info = finger_alloc_shared();

    ifd_data.data[0].fd = ion_info->fd;
    ifd_data.data[0].cmd_buf_offset = 4;

    unsigned char *req_buf = handle->ion_sbuffer;
    memset(req_buf, '\x00', req_size);
    unsigned char *resp_buf = &handle->ion_sbuffer[req_size];
    memset(resp_buf, '\x00', req_size);

    uint32_t *req_buf32 = (uint32_t *)ion_info->addr;
    req_buf[1] = 0x10; // ion_info->length;
    //*((uint32_t*) &req_buf[4]) = (uint32_t) ion_info->addr & 0xffffffff;
    // req_buf32[1] = (uint32_t) &req_buf32[0x20];

    req_buf32[0] = 0x08;
    req_buf32[1] = 0x02;

    req_buf32 = (uint32_t *)ion_info->addr;
    req_buf[1] = 0x10; // ion_info->length;
    //*((uint32_t*) &req_buf[4]) = (uint32_t) ion_info->addr & 0xffffffff;
    req_buf32[0] = 0x03;
    req_buf32[1] = 0x02;
    ret = my_handle->QSEECom_send_modified_cmd(handle, req_buf, req_size,
                                               resp_buf, resp_size, &ifd_data);

    if (ret)
    {
        LOGE("QSEECom_send_modified_cmd failed. ret=0x%x. (unsigned "
             "int)resp_buf=0x%x\n",
             ret, (unsigned int)resp_buf);
        return -1;
    }
    LOGI("retval %i\n", ret);
    // hexdump("req_buf", req_buf, req_size);
    // hexdump("req_buf32", req_buf32, 0x80);

    if (*((uint64_t *)&req_buf32[2]) != 0)
    {
        return *((uint64_t *)&req_buf32[2]);
    }
    return 0;
}

int func(uint64_t challenge, char *auth_token)
{
    // cmd_id // static
    // padding // static
    // challenge // from pre_enroll()
    // password_handle_offset; // static
    // signature_offset; // static
    // password_offset; // static
    // password_length; // static
    // enrolled_password_handle[58]; // read from file gatekeeper.pattern.key
    // password[38]; // static
    return 0;
}

int qsee_init(int client_sock, qcom_my_handle_t **my_handle)
{
    int ret = 0;
    ssize_t nread = 0;

    // get path
    char *path = NULL;

    if ((nread = read_data_log("path", client_sock, &path)) == -1)
    {
        ret = -1;
        goto error_1;
    }

    if (path[nread] != '\x00')
    {
        LOGE("Error receiving path. Tell client to end it's char*s with "
             "\\x00\n");
        goto error_1;
    }
    // get fname
    char *fname = NULL;

    if ((nread = read_data_log("fname", client_sock, &fname)) == -1)
    {
        ret = -1;
        goto error_2;
    }

    if (fname[nread] != '\x00')
    {
        LOGE("Error receiving fname. Tell client to end it's char*s with "
             "\\x00\n");
        goto error_2;
    }
    // get sb_size
    char *sb_size_buf = NULL;
    ssize_t sb_size = 0;

    if ((nread = read_data_log("sb_size_buf", client_sock, &sb_size_buf)) ==
        -1)
    {
        ret = -1;
        goto error_3;
    }

    sb_size = *((uint32_t *)sb_size_buf);
    LOGD("sb_size: %zd\n", sb_size);

    // get qsee handle and initialize TA
    ret = qsee_init_ta(my_handle, path, fname, sb_size);
    if (ret < 0)
    {
        LOGE("TA initialization failed (%s).\n", fname);
        ret = -1;
        goto error_4;
    }

    if (!((*my_handle)->qseecom))
    {
        LOGE("qseecom handle not initialized.\n");
        ret = -1;
        goto error_4;
    }

    if (!strcmp(fname, "fpctzappfingerprint"))
    {
        // LOGI("It's fpctzappfingerprint!\n");
        // uint64_t challenge = fpc_get_challenge(*my_handle);
        // LOGI("Challenge is %llx\n", challenge);
    }

    free(sb_size_buf);
    free(fname);
    free(path);
    return ret;

error_4:
    free(*my_handle);
error_3:
    free(sb_size_buf);
error_2:
    free(fname);
error_1:
    free(path);
    return ret;
}

int qsee_interact(int client_sock)
{
    static qcom_my_handle_t *my_handle = NULL;
    struct qseecom_send_cmd_req send_cmd_req = {0};
    struct QSEECom_handle *handle = NULL;
    int ret = 0;

    unsigned char tzzz_cmd = 0;
    ssize_t nread = 0;
    int is_end = 0;

    while (!is_end)
    {
        LOGD(" ### Waiting for TZZZ_CMD ###\n");
        if ((nread = read(client_sock, &tzzz_cmd, 1)) != 1)
        {
            LOGE("Error reading TZZZ_CMD\n");
            return -1;
        }

        switch (tzzz_cmd)
        {
        case TEEZZ_CMD_START:
            LOGD(" ### TZZZ_INIT_TA ###\n");
            ret = qsee_init(client_sock, &my_handle);
            handle = my_handle->qseecom;
            if (ret < 0)
            {
                LOGE("qsee_init failed.\n");
                exit(EXIT_FAILURE);
            }

            // Set bandwidth to high
            ret = my_handle->QSEECom_set_bandwidth(handle, true);
            if (ret < 0)
            {
                LOGE("Unable to enable clks: ret =%d\n", ret);
                exit(EXIT_FAILURE);
            }

            break;
        case TEEZZ_CMD_SEND:
            LOGD(" ### TZZZ_SEND_CMD ###\n");

            // get command type
            LOGD(" ### get cmd type ###\n");
            unsigned char send_cmd;
            if ((nread = read(client_sock, &send_cmd, 1)) != 1)
            {
                LOGE("Error reading SEND_CMD type\n");
                return -1;
            }

            LOGD(" ### req buffer ###\n");
            ssize_t req_size = 0;
            unsigned char *req_buf = handle->ion_sbuffer;
            ret = qsee_get_req(client_sock, (char *)req_buf, &req_size);
            if (ret < 0)
            {
                LOGE("Get request buffer failed.\n");
                break;
            }
            LOGD(" ### req_size %zd ###\n", req_size);

            LOGD(" ### resp_buf size buffer ###\n");
            unsigned char *resp_buf =
                &handle->ion_sbuffer[QSEECOM_ALIGN(req_size)];
            ssize_t resp_size = 0;
            qsee_get_resp_buf_size(client_sock, &resp_size);

            LOGD(" ### resp_size %zd ###\n", resp_size);

            resp_buf[0] = 0xde;
            resp_buf[1] = 0xad;
            resp_buf[2] = 0xbe;
            resp_buf[3] = 0xef;

            if (send_cmd == QSEECOM_SEND_CMD_REQ)
            {
                LOGD(" ### sending qseecom_send_cmd_req ###\n");
                // hexdump("[IN] req_buf", req_buf, req_size);
                // hexdump("[IN] resp_buf", resp_buf, resp_size);
                ret = my_handle->QSEECom_send_cmd(handle, req_buf, req_size,
                                                  resp_buf, resp_size);
            }
            else if (send_cmd == QSEECOM_SEND_MODFD_CMD_REQ)
            {
                // allocate only once -> global buffer
                if (iinfo_shm == NULL)
                    iinfo_shm = finger_alloc_shared();

                // set the lower 4 Bytes of the shared buffer address in the req-buffer
                LOGD("Shared buffer address: %p\n", iinfo_shm->addr);
                ((uint32_t *)req_buf)[1] = (uint32_t)iinfo_shm->addr;
                // hexdump("req_buf", req_buf, req_size);

                // get shared buffer from fuzzer
                ssize_t shared_size = 0;
                ret = qsee_get_shared(client_sock, (char *)iinfo_shm->addr, &shared_size);
                if (ret == -1)
                {
                    LOGE("Get shared buffer failed.\n");
                    break;
                }

                // set ion fd for shared buffer
                LOGD(" ### shared_size %zd ###\n", shared_size);
                struct QSEECom_ion_fd_info ion_info = {0};
                ion_info.data[0].fd = iinfo_shm->fd;
                ion_info.data[0].cmd_buf_offset = 4;

                // hexdump("Shared from fuzzer:", iinfo_shm->addr, 128);

                // hexdump("Resp before cmd req:", resp_buf, 128);

                LOGD(" ### sending qseecom_modfd_send_cmd_req ###\n");

                /*
                struct qseecom_send_modfd_cmd_req cmd = {0};
                cmd.cmd_req_buf = req_buf;
                cmd.cmd_req_len = 64;
                cmd.resp_buf = resp_buf;
                cmd.resp_len = 64;
                cmd.ifd_data[0].fd = iinfo_shm->fd;
                cmd.ifd_data[0].cmd_buf_offset = 4;

                ret = ioctl(((int*)handle)[4], QSEECOM_IOCTL_SEND_MODFD_CMD_REQ, &cmd);
                */
                ret = my_handle->QSEECom_send_modified_cmd(handle, req_buf, req_size,
                                                           resp_buf, resp_size, &ion_info);
                LOGD(" ### qseecom_modfd_send_cmd_req return value: %#x ###\n", ret);
                // hexdump("Shared after:", iinfo_shm->addr, 128);

                // always send the whole buffer
                LOGD(" ### writing shared buffer back to host ###\n");
                if (write_data(client_sock, (char *)iinfo_shm->addr, iinfo_shm->length) <= 0)
                {
                    LOGE("Error writing data back to host.\n");
                }
            }
            else
            {
                LOGE("Unknown SEND_CMD type\n");
                return -1;
            }

            if (ret)
            {
                LOGE("QSEECom_send_cmd failed. ret=0x%x. (unsigned "
                     "int)resp_buf=0x%x\n",
                     ret, (unsigned int)resp_buf);
                resp_buf[0] = 0xde;
                resp_buf[1] = 0xad;
                resp_buf[2] = 0xde;
                resp_buf[3] = 0xad;
            }
            // hexdump("[OUT] req_buf[:64]", req_buf, req_size);
            // hexdump("[OUT] resp_buf[:64]", resp_buf, resp_size);

            LOGD(" ### writing data back to host ###\n");

            if (resp_size > 0)
            {
                if (write_data(client_sock, (char *)resp_buf, resp_size) <= 0)
                {
                    LOGE("Error writing data back to host.\n");
                }
            }
            else
            {
                if (write_data(client_sock, (char *)resp_buf, 8) <= 0)
                {
                    LOGE("Error writing data back to host.\n");
                }
            }
            break;
        case TEEZZ_CMD_END:
            LOGD(" ### TZZZ_END ###\n");

            // Set bandwidth to low
            ret = my_handle->QSEECom_set_bandwidth(handle, false);
            if (ret < 0)
            {
                LOGE("Unable to disable clks: ret =%d\n", ret);
            }

            is_end = 1;
            free(my_handle);
            // TODO: close fd to /dev/qseecom
            break;
        default:
            LOGD(" ### WTF? ###\n");
        }
    }
    return ret;
}

/*
 * @brief: initialize the QSEEComAPI library related pointers of qcom_my_handle
 *         from libQSEECom.so shared object/library
 *
 */
static int qcom_my_get_lib_sym(qcom_my_handle_t *my_handle)
{
    my_handle->libhandle = dlopen("libQSEEComAPI.so", RTLD_NOW);
    if (my_handle->libhandle)
    {
        *(void **)(&my_handle->QSEECom_start_app) =
            dlsym(my_handle->libhandle, "QSEECom_start_app");
        if (my_handle->QSEECom_start_app == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_start_app\n");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&my_handle->QSEECom_shutdown_app) =
            dlsym(my_handle->libhandle, "QSEECom_shutdown_app");
        if (my_handle->QSEECom_shutdown_app == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_shutdown_app\n");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&my_handle->QSEECom_register_listener) =
            dlsym(my_handle->libhandle, "QSEECom_register_listener");
        if (my_handle->QSEECom_register_listener == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_register_listener");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }

        *(void **)(&my_handle->QSEECom_unregister_listener) =
            dlsym(my_handle->libhandle, "QSEECom_unregister_listener");
        if (my_handle->QSEECom_unregister_listener == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_unregister_listener");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&my_handle->QSEECom_send_cmd) =
            dlsym(my_handle->libhandle, "QSEECom_send_cmd");
        if (my_handle->QSEECom_send_cmd == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_send_cmd\n");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }

        *(void **)(&my_handle->QSEECom_send_modified_cmd) =
            dlsym(my_handle->libhandle, "QSEECom_send_modified_cmd");
        if (my_handle->QSEECom_send_modified_cmd == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_send_modified_cmd\n");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }

        *(void **)(&my_handle->QSEECom_set_bandwidth) =
            dlsym(my_handle->libhandle, "QSEECom_set_bandwidth");
        if (my_handle->QSEECom_set_bandwidth == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_set_bandwidth\n");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }

        *(void **)(&my_handle->QSEECom_receive_req) =
            dlsym(my_handle->libhandle, "QSEECom_receive_req");
        if (my_handle->QSEECom_receive_req == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_receive_req");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }

        *(void **)(&my_handle->QSEECom_send_resp) =
            dlsym(my_handle->libhandle, "QSEECom_send_resp");
        if (my_handle->QSEECom_send_resp == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_send_resp");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }

        *(void **)(&my_handle->QSEECom_app_load_query) =
            dlsym(my_handle->libhandle, "QSEECom_app_load_query");
        if (my_handle->QSEECom_app_load_query == NULL)
        {
            LOGE("dlsym: Error Loading QSEECom_app_load_query\n");
            dlclose(my_handle->libhandle);
            my_handle->libhandle = NULL;
            return -1;
        }
    }
    else
    {
        LOGE("failed to load qseecom library\n");
        return -1;
    }
    return 0;
}

/*
 * @brief: get the QSEECom API ready for usage
 */
qcom_my_handle_t *init_qcom_my_handle()
{
    // allocate memory for the handle
    qcom_my_handle_t *my_handle =
        (qcom_my_handle_t *)malloc(sizeof(qcom_my_handle_t));
    if (my_handle == NULL)
    {
        LOGE("Memalloc for qcom_my_handle failed!\n");
        return NULL;
    }

    my_handle->qseecom = NULL;
    my_handle->libhandle = NULL;
    // map the api symbols from the library to the local representation
    int ret = qcom_my_get_lib_sym(my_handle);
    if (ret < 0)
    {
        LOGE("get_lib_syms failed\n");
        free(my_handle);
        return NULL;
    }
    return my_handle;
}

static int qsee_cmd_start(data_stream_t *in_ds, qsee_state_t *state)
{
    ssize_t nread = 0;

    LOGD("%s", __FUNCTION__);

    // open ioctl device
    // state->fd = open(TC_NS_CLIENT_DEV_NAME, O_RDWR);
    // if (-1 == (state->fd))
    // {
    //     perror("open");
    //     LOGE("failed to get an fd to %s", TC_NS_CLIENT_DEV_NAME);
    //     goto err;
    // }

    // get path
    if (recv_item_by_name(in_ds, "path", state->path, MEMBER_SIZE(qsee_state_t, path)) < 0)
    {
        LOGE("Failed receiving path");
        goto err;
    }
    LOGI("path: %s", state->path);

    // get fname
    if (recv_item_by_name(in_ds, "fname", state->fname, MEMBER_SIZE(qsee_state_t, fname)) < 0)
    {
        LOGE("Failed receiving fname");
        goto err;
    }
    LOGI("fname: %s", state->fname);

    // get sb_size
    if (recv_item_by_name(in_ds, "sb_size", (char *)&state->sb_size, sizeof(uint32_t)) < 0)
    {
        LOGE("Failed receiving sb_size");
        goto err;
    }
    LOGI("sb_size: %i", state->sb_size);

    qcom_my_handle_t *qsee_handle = NULL;
    qsee_handle = init_qcom_my_handle();
    if (!qsee_handle)
    {
        LOGE("Failed initializing qcom handle");
        goto err;
    }
    state->libteec = qsee_handle;

    int ret = 0;
    ret =
        state->libteec->QSEECom_start_app(&state->libteec->qseecom, state->path, state->fname, state->sb_size);

    if (ret)
    {
        LOGE("QSEECom_start_app failed.\n");
        goto err;
    }

    // Set bandwidth to low
    ret = state->libteec->QSEECom_set_bandwidth(state->libteec->qseecom, false);
    if (ret < 0)
    {
        LOGE("Unable to disable clks: ret =%d\n", ret);
    }

    // check if TA already loaded
    // ret = my_handle->QSEECom_app_load_query(my_handle->qseecom, fname);
    // if (ret != QSEECOM_APP_ALREADY_LOADED)
    // {
    //     if (ret == QSEECOM_APP_QUERY_FAILED)
    //     {
    //         LOGE("QSEECOM_APP_QUERY_FAILED\n");
    //     }
    //     else if (ret == QSEECOM_APP_NOT_LOADED)
    //     {
    //         LOGE("Implement me!\n");
    //         // TODO: get path, fname, sb_size from remote
    //         // ret = (*my_handle->QSEECom_start_app)((struct QSEECom_handle **)
    //         // &my_handle->qseecom,
    //         //             path, fname, sb_size);
    //         // if (ret)
    //         //{
    //         //    printf("    Loading \"%s\" failed!\n", fname);
    //         //    goto cleanup;
    //         //}
    //         // printf("    Loading \"%s\" succeeded!\n", fname);
    //     }
    //     else
    //     {
    //         LOGE("QSEECom_app_load_query return status unknown 0x%x\n", ret);
    //     }
    // }
    // else
    // {
    //     // ta already loaded
    //     ret = 0;
    // }

    return 0;
err:
    return -1;
}

static int qsee_cmd_send(data_stream_t *in_ds, data_stream_t *out_ds, qsee_state_t *state)
{

    char *data = NULL;
    int invoke_ret = 0, ret = EXECUTOR_SUCCESS;

    char *req_buf = NULL, *resp_buf = NULL;
    uint32_t req_size = 0, resp_size = 0;

    LOGD("%s", __FUNCTION__);

    char *buf = NULL;
    ssize_t nread = 0;

    // get qseecom req buf
    if ((nread = parse_lv(in_ds, &buf)) < 0)
    {
        LOGD("error getting qseecom req buf");
        goto err;
    }
    LOGD("received qseecom req buf of sz %zd", nread);
    req_buf = buf;
    req_size = nread;

    // get qseecom resp buf size
    if ((nread = parse_lv(in_ds, &buf)) < 0)
    {
        LOGD("error getting size of memref param");
        goto err;
    }
    LOGD("received qseecom resp buf size of %zd", *(uint32_t *)buf);
    resp_size = *(uint32_t *)buf;
    // FIXME: allocate this once and check if space is enough
    resp_buf = calloc(1, resp_size);

    LOGD("Calling QSEECom_send_cmd with req sz %d and resp sz %d", req_size, resp_size);
    // invoke the requested command
    invoke_ret = state->libteec->QSEECom_send_cmd(state->libteec->qseecom, req_buf, req_size,
                                                  resp_buf, resp_size);

    LOGD("QSEECom_send_cmd res (errno): %d (%d)", invoke_ret, errno);
    // Write executor status to output stream
    if (!ds_write(out_ds, (char *)&ret, sizeof(int)))
    {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }

    if (*(uint32_t *)resp_buf != 0)
    {
        // only TA status if TA request failed
        resp_size = 4;
    } else {
        // optimization for zero padding of resp buffers
        off_t start_pad = 4;
        for(off_t i = 4; i < resp_size; i++) {
            // if `i` is not zero, we move the start of the padding forward
            if (resp_buf[i] != '\x00') start_pad = i+1;
        }
        resp_size = start_pad;
    }

    // <invoke ret sz> + <req sz> + <req> + <resp sz> + <resp>
    uint32_t out_chunk_sz = sizeof(uint32_t) + sizeof(uint32_t) + req_size + sizeof(uint32_t) + resp_size;

    LOGD("out_chunk_sz is %d", out_chunk_sz);

    // Write size of chunk
    if (!(data = ds_write(out_ds, (char *)&out_chunk_sz, sizeof(uint32_t))))
    {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }

    // Write invoke ret
    if (!(data = ds_write(out_ds, (char *)&invoke_ret, sizeof(uint32_t))))
    {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }

    // Write size req
    if (!(data = ds_write(out_ds, (char *)&req_size, sizeof(uint32_t))))
    {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }

    // serialize req buf
    if (!ds_write(out_ds, req_buf, req_size))
    {
        LOGE("ds_write: error writing to ds");
        goto err;
    }

    // Write size resp
    if (!(data = ds_write(out_ds, (char *)&resp_size, sizeof(uint32_t))))
    {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }

    // serialize resp buf
    if (!ds_write(out_ds, resp_buf, resp_size))
    {
        LOGE("ds_write: error writing to ds");
        goto err;
    }

    LOGD("serializing response done");

    return 0;
err_comm:
    ret = EXECUTOR_ERROR;
    if (!ds_write(out_ds, (char *)&ret, sizeof(int)))
    {
        LOGE("ds_write: error writing to ds");
    }
err:
    return -1;
}

static int qsee_cmd_end(qsee_state_t *state)
{

    int ret = 0;
    LOGD("%s", __FUNCTION__);

    // Set bandwidth to low
    ret = state->libteec->QSEECom_set_bandwidth(state->libteec->qseecom, false);
    if (ret < 0)
    {
        LOGE("Unable to disable clks: ret =%d\n", ret);
    }
    // free(state->libteec->libhandle);
    // free(state->libteec->qseecom);
    // TODO: close fd to /dev/qseecom
    return 0;
}

int qsee_execute(int data_sock)
{
    int ret = 0;
    bool is_end = false;

    char cmd = 0;
    uint32_t sz = 0;
    char *data = NULL;

    data_stream_t *in_ds = NULL;
    data_stream_t *out_ds = NULL;

    out_ds = ds_init(32);

    if (out_ds == NULL)
    {
        LOGE("ds_init: error allocating output ds");
        goto err;
    }

    LOGD("%s", __FUNCTION__);
    while (!is_end)
    {
        // Make sure these vars have their expected initial values
        cmd = 0;
        sz = 0;
        data = NULL;

        if (recv_tlv(data_sock, &cmd, &sz, &data))
        {
            LOGE("recv_tlv: error receiving tlv data");
            goto err;
        }

        // initialize input stream from incoming buffer
        in_ds = ds_init_from_buf(data, sz);

        switch (cmd)
        {
        case TEEZZ_CMD_START:
            if (qsee_cmd_start(in_ds, &QSEE_STATE) == EXECUTOR_ERROR)
                goto err;
            break;
        case TEEZZ_CMD_SEND:
            ds_reset(out_ds);
            if (qsee_cmd_send(in_ds, out_ds, &QSEE_STATE) == EXECUTOR_ERROR)
                goto err;
            if (send_buf(data_sock, out_ds->data, out_ds->pos) < 0)
            {
                LOGE("send_buf: error sending output data");
                goto err;
            }
            break;
        case TEEZZ_CMD_END:
            if (qsee_cmd_end(&QSEE_STATE) == EXECUTOR_ERROR)
                goto err;
            // we want to leave the loop
            is_end = true;
            break;
        case TEEZZ_CMD_TERMINATE:
            if (qsee_cmd_end(&QSEE_STATE) == EXECUTOR_ERROR)
                goto err;
            // we want to leave the loop
            is_end = true;
            ret = 130; // script terminated by CTRL+C
            break;
        default:
            LOGE("Client misbehaving");
            goto err;
        }
        // deinit the input stream, we initialize a new one for each request
        if (in_ds)
            ds_deinit(in_ds);
    }

    if (out_ds)
        ds_deinit(out_ds);

    return ret;
err:
    return -1;
}