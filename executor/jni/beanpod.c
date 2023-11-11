#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <signal.h>
#include <unistd.h>
#include <assert.h>
#include <time.h>
#include <inttypes.h>
#include <dlfcn.h>
#include <sys/mman.h>

#include <logging.h>
#include <optee/opteelibteec.h>
#include <optee/opteenet.h>
#include <executor.h>
#include <utils.h>
#include <optee/tee_client_api.h>
#include <optee/opteecom.h>
#include <optee/shm_pta.h>

typedef struct beanpod_state {
    libteec_handle_t *libteec;
    TEEC_Context ctx;
    TEEC_SharedMemory shm;
    uint8_t stop_soon;
    struct timespec start;
} beanpod_state_t;

beanpod_state_t BEANPOD_STATE = { 0 };

int beanpod_cmd_start(data_stream_t *ds, libteec_handle_t *handle, TEEC_Context *ctx, TEEC_Session *sess)
{

    TEEC_Result res;
    uint32_t err_origin;

    char tmp_uuid[16] = {0};
    TEEC_UUID uuid = {0};
    int ret = 0;

    if (recv_item_by_name_exact(ds, "uuid", (char *)&tmp_uuid, sizeof(tmp_uuid)) < 0)
    {
        LOGE("Failed receiving uuid");
        goto err;
    }

    uint32_t timeLow;
    uuid.timeLow = (uint32_t)tmp_uuid[0] << 24 |
      (uint32_t)tmp_uuid[1] << 16 |
      (uint32_t)tmp_uuid[2] << 8  |
      (uint32_t)tmp_uuid[3];
    uuid.timeMid = (uint16_t)tmp_uuid[4] << 8 | (uint16_t)tmp_uuid[5];
    uuid.timeHiAndVersion = (uint16_t)tmp_uuid[6] << 8 | (uint16_t)tmp_uuid[7];
    for(int i = 0; i<8; i++){
        uuid.clockSeqAndNode[i] = (uint8_t)tmp_uuid[8+i];
    }

    res = handle->ops.TEEC_OpenSession(ctx, sess, &uuid,
                                   TEEC_LOGIN_PUBLIC, NULL, NULL,
                                   &err_origin);
    if (res != TEEC_SUCCESS)
    {
        LOGE("TEEC_Opensession failed with code 0x%x origin 0x%x",
             res, err_origin);
        goto err;
    }

    return ret;
err:
    return -1;
}

int beanpod_cmd_send(data_stream_t *in_ds, data_stream_t *out_ds, libteec_handle_t *handle, TEEC_Context *ctx, TEEC_Session *sess)
{

    TEEC_Result res = 0;
    TEEC_Operation op = { 0 };
    struct tee_ioctl_invoke_arg arg = { 0 };
    uint32_t err_origin = 0;
    char *data = NULL;
    int ret = 0;
    uint32_t cmd_id = 0;

    memset(&op, 0, sizeof(op));

    if(optee_deserialize_input(in_ds, &arg, &op, &cmd_id) != 0) {
        LOGE("optee_get_input: error parsing input");
        goto err_comm;
    }

    LOGD("\t\tbuffer@ %p with sz %zd",
         (void *)op.params[1].tmpref.buffer, op.params[1].tmpref.size);
    res = handle->ops.TEEC_InvokeCommand(sess, cmd_id, &op, &err_origin);
    LOGD("\t\tbuffer@ %p with sz %zd",
         (void *)op.params[1].tmpref.buffer, op.params[1].tmpref.size);

    arg.ret = res;
    arg.ret_origin = err_origin;
    ret = EXECUTOR_SUCCESS;

    LOGD("TEEC_InvokeCommand %#x (%#x) --> %#x", arg.ret, arg.ret_origin, ret);
    // Write executor status to output stream
    if(!ds_write(out_ds, (char*)&ret, sizeof(int))) {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }

    // Write placeholder for size to output stream
    if(!(data = ds_write(out_ds, (char*)&ZERO, sizeof(uint32_t)))) {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }
    uint32_t pos_sz = out_ds->pos - sizeof(uint32_t);

    // write content to output stream
    if(optee_serialize_output(out_ds, &arg, &op) != 0)
        goto err;

    // overwrite size placeholder of output stream
    // we indicate the size of the buffer, hence the sizeof subtraction
    *((uint32_t*) &out_ds->data[pos_sz]) = out_ds->pos - 2*sizeof(uint32_t);
    LOGD("out_ds->pos: %d", *((uint32_t*)&out_ds->data[pos_sz]));

    for (int i = 0; i < TEEC_CONFIG_PAYLOAD_REF_COUNT; i++)
    {
        if (TEEC_PARAM_TYPE_GET(op.paramTypes, i) ==
                TEEC_MEMREF_TEMP_OUTPUT)
        {
            TEEC_TempMemoryReference *tmp_ref =
                (TEEC_TempMemoryReference *)&op.params[i];
            free(tmp_ref->buffer);
        }
    }
    return 0;
err_comm:
    ret = EXECUTOR_ERROR;
    LOGE("Comm error.");
    if(!ds_write(out_ds, (char*)&ret, sizeof(int))) {
        LOGE("ds_write: error writing to ds");
    }
err:
    LOGE("beanpod_cmd_send error.");
    return -1;
}

static int register_shm(beanpod_state_t *state, void *shm, size_t sz)
{
    TEEC_Result res;
    state->shm.buffer = shm;
    state->shm.size = sz;
    state->shm.flags = TEEC_MEM_INPUT | TEEC_MEM_OUTPUT;

    res = state->libteec->ops.TEEC_RegisterSharedMemory(&state->ctx, &state->shm);
    if (res != TEEC_SUCCESS)
    {
        LOGE("TEEC_RegisterSharedMemory()");
        state->shm.buffer = NULL;
        state->shm.size = 0;
        state->shm.flags = 0;
        return -1;
    }
    return 0;
}

int beanpod_cmd_end(libteec_handle_t *handle, TEEC_Session *sess)
{
    handle->ops.TEEC_CloseSession(sess);
    return 0;
}


// executed by forkserver
int beanpod_init(void) {
    int ret = 0;

    LOGD("%s", __FUNCTION__);

    BEANPOD_STATE.libteec = init_libteec_handle("/vendor/lib/libTEECommon.so");

    if (!BEANPOD_STATE.libteec)
    {
        LOGE("init_libteec_handle failed.");
        return -1;
    }

    TEEC_Result res = BEANPOD_STATE.libteec->ops.TEEC_InitializeContext(NULL, &BEANPOD_STATE.ctx);
    if (res != TEEC_SUCCESS)
    {
        LOGE("TEEC_InitializeContext()");
        return -1;
    }

    clock_gettime(CLOCK_MONOTONIC, &BEANPOD_STATE.start);
    return ret;
err:
    return -1;
}


// executed by forkserver
int beanpod_deinit(void) {
    LOGD("%s", __FUNCTION__);
    BEANPOD_STATE.libteec->ops.TEEC_FinalizeContext(&BEANPOD_STATE.ctx);
    dlclose(BEANPOD_STATE.libteec->libhandle);
    return 0;
}

// executed by forkserver
int beanpod_pre_execute(int status_sock) {
    LOGD("%s", __FUNCTION__);
    return 0;
}

// executed by forkserver
int beanpod_post_execute(int status_sock) {
    LOGD("%s", __FUNCTION__);
    return 0;
}

// executed by target
int beanpod_execute(int data_sock)
{
    TEEC_Result res;
    uint32_t err_origin;
    TEEC_Session sess = {0};
    int ret = 0;

    data_stream_t *in_ds = NULL;
    data_stream_t *out_ds = NULL;

    char cmd = 0;
    uint32_t sz = 0;
    char* data = NULL;

    ssize_t nread = 0;
    int is_end = 0;

    out_ds = ds_init(32);

    if (out_ds == NULL) {
        LOGE("ds_init: error allocating output ds");
        goto err;
    }

    LOGD("%s", __FUNCTION__);
    while (!is_end)
    {
        LOGD(" ### Waiting for TZZZ_CMD ###");
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
            LOGD(" ### TEEZZ_CMD_START ###");
            if (beanpod_cmd_start(in_ds, BEANPOD_STATE.libteec, &BEANPOD_STATE.ctx, &sess) != 0)
                goto err;
            break;
        case TEEZZ_CMD_SEND:
            LOGD(" ### TEEZZ_CMD_SEND ###");
            // reset the output stream
            ds_reset(out_ds);
            if (beanpod_cmd_send(in_ds, out_ds, BEANPOD_STATE.libteec, &BEANPOD_STATE.ctx, &sess) != 0)
                goto err;
            if(send_buf(data_sock, out_ds->data, out_ds->pos) < 0) {
                LOGE("send_buf: error sending output data");
                goto err;
            }
            break;
        case TEEZZ_CMD_END:
            LOGD(" ### TEEZZ_CMD_END ###");
            is_end = 1;
            if (beanpod_cmd_end(BEANPOD_STATE.libteec, &sess) != 0)
                goto err;
            ret = 0;
            break;
        case TEEZZ_CMD_TERMINATE:
            LOGD(" ### TEEZZ_CMD_TERMINATE ###");
            is_end = 1;
            ret = 130; // script terminated by CTRL+C
            break;
        default:
            LOGD(" ### UNKNOWN COMMAND %#x ###", cmd);
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
    return EXECUTOR_ERROR;
}
