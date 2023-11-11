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

typedef struct optee_state {
    libteec_handle_t *libteec;
    TEEC_Context ctx;
    TEEC_SharedMemory shm;
    uint8_t stop_soon;
    struct timespec start;
} optee_state_t;

typedef struct {
  size_t nentries;
  void* faddr; // addr to func (`TA_CreateEntryPoint`) during runtime within TA
  uint64_t pcs[];
} coverage_t;

// enable afl-like coverage map
static const char COVFEEDBACK_ENV_VAR[] = "COVFEEDBACK";
// directory to store sancov-like files used to collect pcs
static const char COVCOLLECT_DIR_ENV_VAR[] = "COVCOLLECTDIR";
// shm size to register with the SHM PTA
static const char SHMSZ_ENV_VAR[] = "SHMSZ";


optee_state_t OPTEE_STATE = { 0 };


uint8_t *COVERAGE_GLOBAL = NULL;
static int has_new_cov(uint8_t *buf, size_t sz) {

    bool new_cov = false;

    if (!COVERAGE_GLOBAL) {
        COVERAGE_GLOBAL = calloc(1, sz);
    }

    for (int i = 0; i < sz; i++) {
        if (buf[i] && !COVERAGE_GLOBAL[i]) {
            COVERAGE_GLOBAL[i] = 1;
            new_cov = true;
        }
    }

    return new_cov;
}

int optee_cmd_start(data_stream_t *ds, libteec_handle_t *handle, TEEC_Context *ctx, TEEC_Session *sess)
{

    TEEC_Result res;
    uint32_t err_origin;

    TEEC_UUID uuid = {0};
    int ret = 0;

    if (recv_item_by_name_exact(ds, "uuid", (char *)&uuid, sizeof(uuid)) < 0)
    {
        LOGE("Failed receiving uuid");
        goto err;
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

int optee_cmd_send(data_stream_t *in_ds, data_stream_t *out_ds, libteec_handle_t *handle, TEEC_Context *ctx, TEEC_Session *sess)
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
    LOGE("optee_cmd_send error.");
    return -1;
}

static int register_shm(optee_state_t *state, void *shm, size_t sz)
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

static int optee_init_shm() {
    LOGD("Initializing SHM");

    char* shm = NULL;
    int nbytes = atoi(getenv(SHMSZ_ENV_VAR));

    if (nbytes <= 0) {
        LOGE("Bad value for COVCOLLECT: %d", nbytes);
        goto err;
    }

    shm = mmap(NULL, nbytes, PROT_READ | PROT_WRITE, MAP_ANONYMOUS | MAP_SHARED, -1, 0);
    if (shm == MAP_FAILED)
    {
        perror("mmap");
        LOGE("Error in mmap");
        goto err;
    }

    if (register_shm(&OPTEE_STATE, shm, nbytes) == -1)
    {
        LOGE("Failed to register the afl map with the TEE context, aborting.");
        goto err;
    }

    if (register_shm_pta(OPTEE_STATE.libteec, &OPTEE_STATE.ctx, &OPTEE_STATE.shm) != TEEC_SUCCESS)
    {
        LOGE("Failed to register the AFL map with the shm pta, aborting.");
        goto err;
    }
    LOGI("Successfully registered shm with shm_pta");
    return 0;
err:
    return -1;
}


int optee_cmd_end(libteec_handle_t *handle, TEEC_Session *sess)
{
    handle->ops.TEEC_CloseSession(sess);
    return 0;
}

// return time difference in milliseconds
uint64_t diff(struct timespec* start, struct timespec* end)
{
    struct timespec temp;
    if ((end->tv_nsec - start->tv_nsec) < 0)
    {
        temp.tv_sec = end->tv_sec - start->tv_sec - 1;
        temp.tv_nsec = 1000000000 + end->tv_nsec - start->tv_nsec;
    }
    else
    {
        temp.tv_sec = end->tv_sec - start->tv_sec;
        temp.tv_nsec = end->tv_nsec - start->tv_nsec;
    }
    return (temp.tv_sec * 1000ULL) + (temp.tv_nsec / 1000000);
}

static void log_coverage(coverage_t *cov)
{
    pid_t pid;
    char filename[1024];
    int ret;
    size_t nwritten;
    static size_t pc_count_global = 0;  // how many pcs did we see so far?
    FILE *f;
    struct timespec current_time;
    uint64_t tdiff = 0;

    if (cov->nentries)
    {
        pid = getpid();
        clock_gettime(CLOCK_MONOTONIC, &current_time);

        tdiff = diff(&OPTEE_STATE.start, &current_time);
        if(getenv(COVCOLLECT_DIR_ENV_VAR)) {
            ret = snprintf(filename, 1024, "%s/time:%08" PRIu64 ",pid:%d.cov", getenv(COVCOLLECT_DIR_ENV_VAR), tdiff, pid);
        } else {
            ret = snprintf(filename, 1024, "time:%08" PRIu64 ",pid:%d.cov", tdiff, pid);
        }

        if (ret < 0)
        {
            LOGE("error encountered in snprintf");
            return;
        }

        f = fopen(filename, "w");
        if (!f)
        {
            LOGE("fopen");
            return;
        }

        nwritten = fwrite(cov, 1,
                          sizeof(coverage_t) + sizeof(uint64_t) * cov->nentries, f);

        if (nwritten != sizeof(coverage_t) + sizeof(uint64_t) * cov->nentries)
        {
            LOGE("error encountered in fwrite");
            return;
        }

        ret = fclose(f);
        if (ret)
        {
            LOGE("fclose");
            return;
        }

        LOGI("Coverage written to %s", filename);
    }
    else
    {
        LOGI("No coverage entries.");
    }
}

// executed by forkserver
int optee_init(void) {
    int ret = 0;

    LOGD("%s", __FUNCTION__);

    OPTEE_STATE.libteec = init_libteec_handle("libteec.so");

    if (!OPTEE_STATE.libteec)
    {
        LOGE("init_libteec_handle failed.");
        return -1;
    }

    TEEC_Result res = OPTEE_STATE.libteec->ops.TEEC_InitializeContext(NULL, &OPTEE_STATE.ctx);
    if (res != TEEC_SUCCESS)
    {
        LOGE("TEEC_InitializeContext()");
        return -1;
    }

    if (getenv(SHMSZ_ENV_VAR)) {
        ret = optee_init_shm();
    }

    clock_gettime(CLOCK_MONOTONIC, &OPTEE_STATE.start);
    return ret;
err:
    return -1;
}


// executed by forkserver
int optee_deinit(void) {
    LOGD("%s", __FUNCTION__);

    if (getenv(SHMSZ_ENV_VAR)) {
        LOGD("Deinitializing SHM");
        int nbytes = atoi(getenv(SHMSZ_ENV_VAR));
        if (unregister_shm_pta(OPTEE_STATE.libteec, &OPTEE_STATE.ctx) != TEEC_SUCCESS)
        {
            LOGE("Failed to unregister the AFL map from the shm pta.");
        }

        OPTEE_STATE.libteec->ops.TEEC_ReleaseSharedMemory(&OPTEE_STATE.shm);
        munmap(OPTEE_STATE.shm.buffer, nbytes);
    }

    OPTEE_STATE.libteec->ops.TEEC_FinalizeContext(&OPTEE_STATE.ctx);
    dlclose(OPTEE_STATE.libteec->libhandle);
    return 0;
}

// executed by forkserver
int optee_pre_execute(int status_sock) {
    LOGD("%s", __FUNCTION__);
    if (OPTEE_STATE.shm.buffer) {
        if (getenv(COVCOLLECT_DIR_ENV_VAR)) {
            // zero the collected pcs
            memset(&((coverage_t*) OPTEE_STATE.shm.buffer)->pcs, '\x00', ((coverage_t*) OPTEE_STATE.shm.buffer)->nentries * sizeof(uint64_t));
        }
    }
    return 0;
}

// executed by forkserver
int optee_post_execute(int status_sock) {
    LOGD("%s", __FUNCTION__);
    uint32_t zero = 0;
    uint32_t one = 1;
    if (OPTEE_STATE.shm.buffer) {
        if (getenv(COVCOLLECT_DIR_ENV_VAR)) {
            log_coverage((coverage_t*) OPTEE_STATE.shm.buffer);
        } else if (getenv(COVFEEDBACK_ENV_VAR)) {
            // tell the host if we have new coverage
            if(has_new_cov(OPTEE_STATE.shm.buffer, OPTEE_STATE.shm.size)){
                write(status_sock, &one, sizeof(uint32_t));
            } else {
                write(status_sock, &zero, sizeof(uint32_t));
            }
        }
    }
    return 0;
}

// executed by target
int optee_execute(int data_sock)
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
            if (optee_cmd_start(in_ds, OPTEE_STATE.libteec, &OPTEE_STATE.ctx, &sess) != 0)
                goto err;
            break;
        case TEEZZ_CMD_SEND:
            LOGD(" ### TEEZZ_CMD_SEND ###");
            // reset the output stream
            ds_reset(out_ds);
            if (optee_cmd_send(in_ds, out_ds, OPTEE_STATE.libteec, &OPTEE_STATE.ctx, &sess) != 0)
                goto err;
            if(send_buf(data_sock, out_ds->data, out_ds->pos) < 0) {
                LOGE("send_buf: error sending output data");
                goto err;
            }
            break;
        case TEEZZ_CMD_END:
            LOGD(" ### TEEZZ_CMD_END ###");
            is_end = 1;
            if (optee_cmd_end(OPTEE_STATE.libteec, &sess) != 0)
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
