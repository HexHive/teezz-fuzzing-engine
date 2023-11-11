#include <alloca.h>
#include <arpa/inet.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <unistd.h>
#include <inttypes.h>

#include <gp.h>
#include <tc/tc.h>
#include <logging.h>
#include <tc/gk.h>
#include <tc/tc_logging.h>
#include <executor.h>
#include <utils.h>

#include <fcntl.h>
#include <dlfcn.h>

tc_state_t TC_STATE = {0};

typedef struct
{
    /* Implementation defined */
    int fd;
    bool reg_mem;
    // unknown stuff
    const char *appPath;
    uint64_t reserved[4];
} TEEC_Context;

typedef struct libtcteec_ops
{
    enum TEEC_Result (*TEEC_StartApp)(TEEC_Context *ctx, uint8_t *uuid);
} libtcteec_ops_t;

typedef struct libtcteec_handle
{
    void *libhandle;
    libtcteec_ops_t ops;
} libtcteec_handle_t;

static int libtcteec_get_lib_sym(libtcteec_handle_t *handle)
{
    handle->libhandle = dlopen("libteec.so", RTLD_NOW | RTLD_GLOBAL);
    if (handle->libhandle)
    {
        *(void **)(&handle->ops.TEEC_StartApp) =
            dlsym(handle->libhandle, "TEEC_StartApp");
        if (handle->ops.TEEC_StartApp == NULL)
        {
            LOGE("dlsym: Error loading TEEC_StartApp");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
    }
    else
    {
        LOGE("failed to load teec library");
        LOGE("%s", dlerror());
        return -1;
    }

    return 0;
}

libtcteec_handle_t *init_libtcteec_handle()
{
    libtcteec_handle_t *handle =
        (libtcteec_handle_t *)calloc(1, sizeof(libtcteec_handle_t));
    if (handle == NULL)
    {
        LOGE("Memalloc for libteec handle failed!");
        return NULL;
    }
    handle->libhandle = NULL;
    int ret = libtcteec_get_lib_sym(handle);
    if (ret < 0)
    {
        LOGE("get_lib_syms failed!");
        free(handle);
        return NULL;
    }
    LOGI("Successfully loaded libteec");
    return handle;
}

// TEE Communication

/*
 * This function sends a login request to a TA using ioctl.
 *
 * \param fd          file descriptor for communication with TA
 * \param login_data  buffer containing the login data for the TA
 *
 * \return always 0, no errors are checked
 */
static int tee_login(int fd, char login_data[])
{
    int ret = 0;
    LOGD("tee_login (fd = %d)", fd);
    // hexdump((char *)"login_data", login_data, 0x60);

    // send ioctl to perform login
    ret = ioctl(fd, TC_NS_CLIENT_IOCTL_LOGIN, login_data);
    if (0 > ret)
    {
        LOGE("TC_NS_CLIENT_IOCTL_LOGIN ret %#x", ret);
    }
    else
    {
        LOGD("TC_NS_CLIENT_IOCTL_LOGIN ret %#x", ret);
    }

    return ret;
}

/*
 * Requests that a TA is loaded, if not already loaded.
 *
 * \param fuzz_ctx  context which contains TA uuid and fd for ioctl
 *
 * \return 0 on success, non-zero on failure
 */
static int tee_ensure_ta_is_loaded(tc_state_t *state)
{
    libtcteec_handle_t *libteec = init_libtcteec_handle();
    TEEC_Context *ctx = calloc(1, sizeof(TEEC_Context));
    char app_path[128] = {0};

    snprintf(
        app_path,
        128,
        "/system/bin/%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x.sec",
        *(uint32_t *)&state->ctx.uuid[0],
        *(uint16_t *)&state->ctx.uuid[4],
        *(uint16_t *)&state->ctx.uuid[6],
        *(uint8_t *)&state->ctx.uuid[8],
        *(uint8_t *)&state->ctx.uuid[9],
        *(uint8_t *)&state->ctx.uuid[10],
        *(uint8_t *)&state->ctx.uuid[11],
        *(uint8_t *)&state->ctx.uuid[12],
        *(uint8_t *)&state->ctx.uuid[13],
        *(uint8_t *)&state->ctx.uuid[14],
        *(uint8_t *)&state->ctx.uuid[15]);

    if (access(app_path, F_OK) != 0)
    {
        snprintf(
            app_path,
            128,
            "/vendor/bin/%08x-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x.sec",
            *(uint32_t *)&state->ctx.uuid[0],
            *(uint16_t *)&state->ctx.uuid[4],
            *(uint16_t *)&state->ctx.uuid[6],
            *(uint8_t *)&state->ctx.uuid[8],
            *(uint8_t *)&state->ctx.uuid[9],
            *(uint8_t *)&state->ctx.uuid[10],
            *(uint8_t *)&state->ctx.uuid[11],
            *(uint8_t *)&state->ctx.uuid[12],
            *(uint8_t *)&state->ctx.uuid[13],
            *(uint8_t *)&state->ctx.uuid[14],
            *(uint8_t *)&state->ctx.uuid[15]);
    }
    LOGI("TEEC_StartApp for %s", app_path);
    ctx->appPath = app_path;
    ctx->fd = state->fd;
    ctx->reserved[0] = (uint64_t)&ctx->reserved;
    ctx->reserved[1] = (uint64_t)&ctx->reserved;

    ctx->reserved[2] = (uint64_t)&ctx->reserved[2];
    ctx->reserved[3] = (uint64_t)&ctx->reserved[2];
    int ret = libteec->ops.TEEC_StartApp(ctx, state->ctx.uuid);
    LOGI("TEEC_StartApp: %#x", ret);

    free(ctx);
    return 0;
}

/*
 * Updates the supplied ClientContext and sends an open session request
 * to a TA.
 *
 * \param fd        Opened file for ioctl communication with TA
 * \param ctx       This session is adjusted and used for TA communication
 *
 * \return 0 on success, non-zero on failure
 */
static int tee_open_session(int fd, TC_NS_ClientContext *ctx)
{

    LOGD("%s", __FUNCTION__);

    // Adjust ctx for opening a session
    // ctx->paramTypes =
    //     TEEC_PARAM_TYPES(TEEC_NONE, TEEC_NONE, TEEC_NONE, TEEC_NONE);
    ctx->paramTypes =
        TEEC_PARAM_TYPES(TEEC_VALUE_INPUT, TEEC_NONE, TEEC_MEMREF_TEMP_INPUT, TEEC_MEMREF_TEMP_INPUT);
    ctx->login.method = TEEC_LOGIN_IDENTIFY;
    ctx->cmd_id = GLOBAL_CMD_ID_OPEN_SESSION;
    ctx->started = 1;
    uint64_t sz = 0x1000;

    ctx->params[0].value.a_addr = (__u64 *)&sz;
    ctx->params[0].value.b_addr = (__u64 *)&sz;

    ctx->params[2].memref.buffer = (__u64)calloc(1, 0x1000);
    ctx->params[2].memref.size_addr = (__u64)&sz;

    ctx->params[3].memref.buffer = (__u64)calloc(1, 0x1000);
    ctx->params[3].memref.size_addr = (__u64)&sz;

#ifdef SECURITY_AUTH_ENHANCE
    ctx->teec_token = malloc(64);
    if (ctx->teec_token == NULL)
    {
        LOGE("cannot malloc security token!");
        return -1;
    }
#endif

    // open the session
    int ret = ioctl(fd, TC_NS_CLIENT_IOCTL_SES_OPEN_REQ, ctx);

    LOGD("ret %d", ret);
    LOGD("tz gave us session_id %#x", ctx->session_id);
    LOGD("client_context.return %#x", ctx->returns.code);

    if (ret != 0)
    {
        perror("ioctl");
        LOGE("cannot open session (ret: %d)", ret);
        return ret;
    }

    if (ctx->returns.code != 0)
    {
        LOGE("ta returned non-zero return code %d", ctx->returns.code);
        return ctx->returns.code;
    };

    return 0;
}

/*
 * Sends parameter back to the fuzzer running on the host.
 *
 * \param data_sock  socket for host communication
 * \param ctx        parameter in this context will be send to the host
 *
 * \return 0 on success, non-zero on error
 *
 * \todo refactor
 */
static int send_params_to_host(int data_sock, TC_NS_ClientContext *ctx)
{

    LOGD("%s", __FUNCTION__);

    for (int i = 0; i < NPARAMS; i++)
    {
        LOGD("\tparam[%i]:", i);
        int param_type = TEEC_PARAM_TYPE_GET(ctx->paramTypes, i);

        switch (param_type)
        {
        case TEEC_NONE:
        case TEEC_VALUE_INPUT:
        case TEEC_MEMREF_TEMP_INPUT:
            LOGD("\t\tNONE or INPUT param.");
            break;
        case TEEC_VALUE_OUTPUT:
        case TEEC_VALUE_INOUT:
            // send value back to host
            if (ctx->params[i].value.a_addr)
            {
                LOGD("\t\tvalue_a_addr: %p --> %#" PRIx64,
                     (void *)(ctx->params[i].value.a_addr),
                     *(uint64_t *)ctx->params[i].value.a_addr);
                write_data(data_sock, (char *)ctx->params[i].value.a_addr,
                           sizeof(uint64_t));
            }
            else
            {
                LOGD("value_a_addr: NULL");
            }

            if (ctx->params[i].value.b_addr)
            {
                LOGD("\t\tvalue_b_addr: %p --> %#" PRIx64,
                     (void *)(ctx->params[i].value.b_addr),
                     *(uint64_t *)ctx->params[i].value.b_addr);
                write_data(data_sock, (char *)ctx->params[i].value.b_addr,
                           sizeof(uint64_t));
            }
            else
            {
                LOGD("value_b_addr: NULL");
            }
            break;
        case TEEC_MEMREF_TEMP_OUTPUT:
        case TEEC_MEMREF_TEMP_INOUT:
            // send buffer back to host

            // send size first
            if (ctx->params[i].memref.size_addr)
            {
                LOGD("\t\tsize_addr: %p --> %#x",
                     (void *)(ctx->params[i].memref.size_addr),
                     *(uint32_t *)(ctx->params[i].memref.size_addr));
                write_data(data_sock, (char *)ctx->params[i].memref.size_addr,
                           sizeof(uint32_t));
            }
            else
            {
                LOGD("size_addr: NULL");
                assert(ctx->params[i].memref.size_addr != 0);
            }

            // send buffer
            if (*(uint32_t *)(ctx->params[i].memref.size_addr) > 0)
            {
                if (ctx->params[i].memref.buffer)
                {
                    LOGD("\t\tbuffer@ %p",
                         (void *)ctx->params[i].memref.buffer);
                    write_data(data_sock, (char *)ctx->params[i].memref.buffer,
                               *(uint32_t *)ctx->params[i].memref.size_addr);
                }
                else
                {
                    LOGD("\t\tbuffer: NULL");
                    assert(ctx->params[i].memref.buffer != 0);
                }
            }
            else
            {
                LOGD("\t\tbuffer: zero length");
                if (write(data_sock, "\n", 1) == -1)
                {
                    perror("write");
                    return -1;
                }
            }

            // send offset
            // offset does not seem to be used on VNS-L31/VNS-L21
            /*
               if (ctx->params[i].memref.offset) {
               LOGD("\t\toffset: 0x%x --> 0x%x",
               (uint64_t*)(ctx->params[i].memref.offset),
               *(uint64_t*)(ctx->params[i].memref.offset));
               write_data(data_sock, (char *)
               ctx->params[i].memref.offset, sizeof(uint64_t));
               }
             */
            break;
        default:
            LOGD(" ### WTF? ###");
        }
    }
    return 0;
}

static int tc_deserialize_param(data_stream_t *ds_in, uint32_t paramType,
                                TC_NS_ClientParam *param)
{
    int ret = 0;
    char *data = NULL;

    LOGD("%s", __FUNCTION__);

    switch (paramType)
    {
    case TEEC_NONE:
        break;
    case TEEC_VALUE_INPUT:
    case TEEC_VALUE_OUTPUT:
    case TEEC_VALUE_INOUT:
    {
        char *buf = NULL;
        ssize_t nread = 0;

        // get a_value
        if ((nread = parse_lv(ds_in, &buf)) < 0)
        {
            LOGD("error getting size of memref param");
            goto err;
        }
        LOGD("received a_value of sz %zd", nread);
        param->value.a_addr = (__u64 *)buf;

        // get b_value
        if ((nread = parse_lv(ds_in, &buf)) < 0)
        {
            LOGD("error getting size of memref param");
            goto err;
        }
        LOGD("received b_value of sz %zd", nread);
        param->value.b_addr = (__u64 *)buf;

        // dirty hack to mimic behavior on p9 lite
        memcpy(((char *)param->value.a_addr) + 4, param->value.b_addr, 4);
        param->value.b_addr = (__u64 *)(((char *)param->value.a_addr) + 4);
        break;
    }
    case TEEC_MEMREF_TEMP_INPUT:
    case TEEC_MEMREF_TEMP_OUTPUT:
    case TEEC_MEMREF_TEMP_INOUT:
    {
        char *buf = NULL;
        ssize_t nread = 0;

        // get buffer
        if ((nread = parse_lv(ds_in, &buf)) < 0)
        {
            LOGD("error getting size of memref param");
            goto err;
        }
        LOGD("received memref of sz %zd", nread);
        param->memref.buffer = (__u64)buf;

        // get size
        if ((nread = parse_lv(ds_in, &buf)) < 0)
        {
            LOGD("error getting size of memref param");
            goto err;
        }
        LOGD("received memref size of %zd", nread);
        param->memref.size_addr = (__u64)buf;
        break;
    }
    case TEEC_MEMREF_WHOLE:
        LOGE("Implement me!");
        break;
    default:
        LOGE("Error, unknown param type 0x%x", paramType);
    }

    return ret;
err:
    return -1;
}

static int tc_deserialize_input(data_stream_t *in_ds, TC_NS_ClientContext *ctx)
{

    int ret = 0;
    TC_NS_ClientContext inctx = {0};
    char *data = NULL;

    LOGD("%s", __FUNCTION__);

    data = ds_read(in_ds, sizeof(TC_NS_ClientContext));
    if (!data)
    {
        LOGE("ds_read: error parsing tee_ioctl_invoke_arg");
        goto err;
    }
    memcpy(&inctx, data, sizeof(TC_NS_ClientContext));

    uint32_t param_types = 0;
    for (int i = 0; i < NPARAMS; i++)
    {
        uint32_t param_type = TEEC_PARAM_TYPE_GET(inctx.paramTypes, i);

        if (param_type == TEEC_MEMREF_PARTIAL_INPUT ||
            param_type == TEEC_MEMREF_PARTIAL_OUTPUT ||
            param_type == TEEC_MEMREF_PARTIAL_INOUT)
        {
            param_type = param_type - 8;
        }
        param_types = param_types | param_type << (i * 4);
        LOGD("getting params[%i] of type %#x", i, param_type);
        ret = tc_deserialize_param(in_ds, param_type, &ctx->params[i]);
        if (ret < 0)
            goto err;
    }
    LOGD("getting param_types: %#x", param_types);
    ctx->paramTypes = param_types;
    ctx->cmd_id = inctx.cmd_id;

    return 0;
err:
    return -1;
}

int tc_serialize_params(data_stream_t *out_ds, TC_NS_ClientContext *ctx)
{
    size_t nsend = 0;
    char *data = NULL;
    uint32_t *sz_p = NULL;
    uint32_t sz = 0;

    LOGD("%s", __FUNCTION__);

    for (int i = 0; i < NPARAMS; i++)
    {
        LOGD("\tparam[%i]:", i);
        int param_type = TEEC_PARAM_TYPE_GET(ctx->paramTypes, i);

        switch (param_type)
        {
        case TEEC_NONE:
        case TEEC_VALUE_INPUT:
        case TEEC_MEMREF_TEMP_INPUT:
            LOGD("\t\tNONE or INPUT param.");
            // we do not serialize input params
            if (!ds_write(out_ds, (char *)&ZERO, sizeof(uint32_t)))
            {
                LOGE("ds_write: error writing to ds");
                goto err;
            }
            break;
        case TEEC_VALUE_OUTPUT:
        case TEEC_VALUE_INOUT:

            sz = sizeof(uint64_t);
            if (!ds_write(out_ds, (char *)&sz, sizeof(uint32_t)))
            {
                LOGE("ds_write: error writing sz of a value to ds");
                goto err;
            }

            data = (char *)ctx->params[i].value.a_addr;
            if (!ds_write(out_ds, (char *)data, sizeof(uint64_t)))
            {
                LOGE("ds_write: error writing a value to ds");
                goto err;
            }

            sz = sizeof(uint64_t);
            if (!ds_write(out_ds, (char *)&sz, sizeof(uint32_t)))
            {
                LOGE("ds_write: error writing sz of b value to ds");
                goto err;
            }
            data = (char *)ctx->params[i].value.b_addr;
            if (!ds_write(out_ds, (char *)data, sizeof(uint64_t)))
            {
                LOGE("ds_write: error writing b value to ds");
                goto err;
            }

            break;
        case TEEC_MEMREF_TEMP_OUTPUT:
        case TEEC_MEMREF_TEMP_INOUT:

            data = (char *)ctx->params[i].memref.buffer;
            sz_p = (uint32_t *)ctx->params[i].memref.size_addr;

            // write size
            if (!ds_write(out_ds, (char *)sz_p, sizeof(uint32_t)))
            {
                LOGE("ds_write: error writing to ds");
                goto err;
            }

            // write buffer
            if (*sz_p > 0)
            {
                assert(data != NULL);
                LOGD("\t\tbuffer@ %p with sz %d",
                     (void *)data, *sz_p);
                if (!ds_write(out_ds, (char *)data, *sz_p))
                {
                    LOGE("ds_write: error writing to ds");
                    goto err;
                }
            }
            break;
        default:
            return -1;
        }
    }

    return 0;
err:
    return -1;
}

int tc_serialize_output(data_stream_t *out_ds, TC_NS_ClientContext *ctx)
{

    LOGD("%s", __FUNCTION__);

    // serialize ctx size
    uint32_t ctx_sz = sizeof(TC_NS_ClientContext);
    if (!ds_write(out_ds, (char *)&ctx_sz, sizeof(uint32_t)))
    {
        LOGE("ds_write: error writing to ds");
        goto err;
    }

    // serialize ctx
    if (!ds_write(out_ds, (char *)ctx, sizeof(TC_NS_ClientContext)))
    {
        LOGE("ds_write: error writing to ds");
        goto err;
    }

    // serialize params if tee interaction succeeded
    if (ctx->returns.code == TEEC_SUCCESS)
    {
        LOGD("Sending params");
        // Send all output parameters
        if (tc_serialize_params(out_ds, ctx))
        {
            LOGE("Error writing data back to host.");
        }
    }

    return 0;
err:
    return -1;
}

/*
 * Receive challenge from the fuzzer running on the host.
 *
 * \param data_sock  socket for host communication
 * \param challenge  The received challenge is stored in this variable
 *
 * \return 0 on success, non-zero on error
 *
 * \todo implement
 */
static int get_challenge_from_host(int data_sock, uint64_t *challenge)
{
    // Implementation depends on the implementation in the fuzzer.
    // Here we want to receive a challenge (8 byte) from the host.
    ssize_t nread = 0;
    char *chal = NULL;

    nread = read_data_log("challenge", data_sock, &chal);
    if (nread == -1)
    {
        LOGE("read_data_log failed");
        return -1;
    }
    else if (nread != 8)
    {
        LOGE("chal size mismatch");
        return -1;
    }

    *challenge = *(uint64_t *)chal;
    return 0;
}

/*
 * Performs login and opens session for given context.
 *
 * \param fuzz_ctx      contents of the provided ctx are initialized
 * \param require_load  if true, a load request is sent to the TA
 *
 * \return 0 on success, doesn't return on error
 */
static int tc_start(tc_state_t *state, bool require_load)
{
    int ret = 0;

    LOGD("%s", __FUNCTION__);

    // tee login
    ret = tee_login(state->fd, state->login_blob);
    if (0 != ret)
    {
        LOGE("tee_login failed");
        goto err;
    }

    LOGD("fd is %d", state->fd);

    // if necessary, we request the TrustedOS to load the TA
    if (require_load)
    {
        ret = tee_ensure_ta_is_loaded(state);
        if (ret != 0)
        {
            LOGE("tee_ensure_ta_is_loaded failed: %#x", ret);
            goto err;
        }
    }

    // set uid/gid for interaction with ioctl device
    if (0 != setgid(state->uid))
    {
        perror("setgid");
        goto err;
    }

    if (0 != setuid(state->uid))
    {
        perror("setuid");
        goto err;
    }

    // don't need this yet, take a look at this for models >= Huawei P10
    // prctl(PR_SET_NAME, fuzz_ctx->pname);
    // LOGD("prctl to %s", fuzz_ctx->pname);

    // open a session
    ret = tee_open_session(state->fd, &state->ctx);
    if (ret != 0)
    {
        LOGE("failed to open session to "
             "%02x%02x%02x%02x%02x%02x%02x%02x",
             state->ctx.uuid[0], state->ctx.uuid[1],
             state->ctx.uuid[2], state->ctx.uuid[3],
             state->ctx.uuid[4], state->ctx.uuid[5],
             state->ctx.uuid[6], state->ctx.uuid[7]);
        goto err;
    }

    return 0;
err:
    return -1;
}

/*
 * Sends a command with id cmd_id to the TA. The corresponding context needs
 * to be passed in ctx.
 *
 * \param fd        Opened file for ioctl communication with TA
 * \param ctx  contains the request which is sent to the TA
 *
 * \return ioctl return value (>= 0), -1 on error
 */
static int invoke_cmd(int fd, TC_NS_ClientContext *ctx)
{

    LOGD("%s", __FUNCTION__);
    // set known values in return values to check error status
    // ctx->returns.code = PRESET_RETURN_CODE;
    // ctx->returns.origin = PRESET_RETURN_ORIGIN;

    // send the context
    int ret = ioctl(fd, TC_NS_CLIENT_IOCTL_SEND_CMD_REQ, ctx);

    // logging
    LOGD("ioctl ret: %#x", ret);
    LOGD("ctx->returns.code: %#x", ctx->returns.code);
    LOGD("ctx->returns.origin: %#x", ctx->returns.origin);

    return ret;
}

/*
 * Retrieves an authorization challenge. This functions handles the
 * interaction with the gatekeeper TA to retrieve the authorization token.
 *
 * \param tz_fd       file descriptor of an opened connection to the gk TA
 * \param auth_chall  the auth challenge which needs to be solved
 * \param auth_token  a buffer for placing the auth token. Must be at least
 *                    of size AUTH_TOKEN_SIZE
 *
 * \return 0 on success, -1 on failure
 *
 * \opt simplify
 */
/*
static int verify_auth_challenge(int tz_fd, uint64_t auth_chall,
                                 char *auth_token) {
    LOGD("### verify_auth_challenge ###");

    static bool gk_initialized = false;
    static TAFuzzContext fuzz_ctx = {};
    int ret;

    // some datastructures
    char weird_block_from_HDD[0x1000];

    fuzz_ctx.fd = tz_fd;

    LOGD(" ### tc_init ###");
    memcpy(fuzz_ctx.ctx.uuid, GK_UUID, MEMBER_SIZE(TC_NS_ClientContext, uuid));
    if (!gk_initialized) {
        LOGD("Initializing gk");
        fuzz_ctx.login_buf = (char *)LOGIN_BUF_GATEKEEPERD;
        tc_init(&fuzz_ctx, true);
        gk_initialized = true;
    }

    LOGD(" ### GK_CMD_ID_ENROLL ###");
    __u64 param_2_c = 0x04;
    __u64 param_3_c = 0x1000;
    char buf[param_3_c];
    memset(buf, 0, param_3_c);

    fuzz_ctx.ctx.cmd_id = GK_CMD_ID_ENROLL;
    fuzz_ctx.ctx.params[2].memref.buffer = (uint64_t) "1337";
    fuzz_ctx.ctx.params[2].memref.offset = 0;
    fuzz_ctx.ctx.params[2].memref.size_addr = (uint64_t)&param_2_c;
    fuzz_ctx.ctx.params[3].memref.buffer = (uint64_t)buf;
    fuzz_ctx.ctx.params[3].memref.offset = 0;
    fuzz_ctx.ctx.params[3].memref.size_addr = (uint64_t)&param_3_c;
    fuzz_ctx.ctx.paramTypes = TEEC_PARAM_TYPES(
        TEEC_NONE, TEEC_NONE, TEEC_MEMREF_TEMP_INPUT, TEEC_MEMREF_TEMP_INOUT);
    memcpy(fuzz_ctx.ctx.uuid, GK_UUID, MEMBER_SIZE(TC_NS_ClientContext, uuid));

    // Debug info
    LOGD("challenge: %#llx", (unsigned long long)auth_chall);
    dump_ctx(&fuzz_ctx.ctx);

    ret = ioctl(fuzz_ctx.fd, TC_NS_CLIENT_IOCTL_SEND_CMD_REQ, &fuzz_ctx.ctx);
    if (ret < 0) {
        perror("ioctl");
        LOGE("ioctl ret: %#x", ret);
        return -1;
    }

    if (fuzz_ctx.ctx.returns.code != 0) {
        LOGE("GK_CMD_ID_ENROLL %d", ret);
        return -1;
    };

    memcpy(weird_block_from_HDD, buf, 0x1000);

    LOGD(" ### GK_CMD_ID_VERIFY ###");

    char buf2[0x3a];
    memcpy(buf2, weird_block_from_HDD, 0x3a);
    __u64 param_1_c = 0x3a;
    __u64 param_0_a = 0;
    __u64 param_0_b = 0;

    fuzz_ctx.ctx.cmd_id = GK_CMD_ID_VERIFY;
    fuzz_ctx.ctx.paramTypes =
        TEEC_PARAM_TYPES(TEEC_VALUE_INOUT, TEEC_MEMREF_TEMP_INPUT,
                         TEEC_MEMREF_TEMP_INPUT, TEEC_MEMREF_TEMP_INOUT);

    fuzz_ctx.ctx.params[0].value.a_addr = &param_0_a;
    fuzz_ctx.ctx.params[0].value.b_addr = &param_0_b;

    fuzz_ctx.ctx.params[1].memref.buffer = (uint64_t)buf2;
    fuzz_ctx.ctx.params[1].memref.offset = 0;
    fuzz_ctx.ctx.params[1].memref.size_addr = (uint64_t)&param_1_c;

    fuzz_ctx.ctx.params[2].memref.buffer = (__u64) "1337";
    fuzz_ctx.ctx.params[2].memref.offset = 0;
    fuzz_ctx.ctx.params[2].memref.size_addr = (uint64_t)&param_2_c;

    memset(buf, 0, 8);
    param_3_c = 0x1000;
    fuzz_ctx.ctx.params[3].memref.buffer = (uint64_t)buf;
    fuzz_ctx.ctx.params[3].memref.offset = 0;
    fuzz_ctx.ctx.params[3].memref.size_addr = (uint64_t)&param_3_c;

    ret = ioctl(fuzz_ctx.fd, TC_NS_CLIENT_IOCTL_SEND_CMD_REQ, &fuzz_ctx.ctx);
    if (ret < 0) {
        perror("ioctl");
        LOGE("ioctl ret: %#x", ret);
        return -1;
    }

    if (fuzz_ctx.ctx.returns.code != 0) {
        LOGE("GK_CMD_ID_VERIFY 1 %d", ret);
        return -1;
    };

    LOGD(" ### GK_CMD_ID_VERIFY ###");
    *(__u64 *)buf = auth_chall;
    param_3_c = 0x1000;
    fuzz_ctx.ctx.params[3].memref.buffer = (uint64_t)buf;
    fuzz_ctx.ctx.params[3].memref.offset = 0;
    fuzz_ctx.ctx.params[3].memref.size_addr = (uint64_t)&param_3_c;

    ret = ioctl(fuzz_ctx.fd, TC_NS_CLIENT_IOCTL_SEND_CMD_REQ, &fuzz_ctx.ctx);
    if (ret < 0) {
        perror("ioctl");
        LOGE("ioctl ret: %#x", ret);
        return -1;
    }

    if (fuzz_ctx.ctx.returns.code != 0) {
        LOGE("GK_CMD_ID_VERIFY 2 %d", ret);
        return -1;
    };

    memcpy(auth_token, buf, AUTH_TOKEN_SIZE);

    return 0;
}
*/

static int tc_cmd_start(data_stream_t *in_ds, tc_state_t *state)
{
    ssize_t nread = 0;

    LOGD("%s", __FUNCTION__);

    // open ioctl device
    state->fd = open(TC_NS_CLIENT_DEV_NAME, O_RDWR);
    if (-1 == (state->fd))
    {
        perror("open");
        LOGE("failed to get an fd to %s", TC_NS_CLIENT_DEV_NAME);
        goto err;
    }

    // init struct with zeros
    memset(&state->ctx, 0x00, sizeof(TC_NS_ClientContext));

    // get uuid
    if (recv_item_by_name_exact(in_ds, "uuid", (char *)&state->ctx.uuid, MEMBER_SIZE(TC_NS_ClientContext, uuid)) < 0)
    {
        LOGE("Failed receiving uuid");
        goto err;
    }

    // get login blob
    if (recv_item_by_name(in_ds, "login_blob", state->login_blob, LOGIN_BLOB_MAX_SZ) < 0)
    {
        LOGE("Failed receiving login blob");
        goto err;
    }

    // get process name
    if (recv_item_by_name(in_ds, "process_name", state->process_name, PROCESS_NAME_MAX_SIZE) < 0)
    {
        LOGE("Failed receiving process_name");
        goto err;
    }

    // get process name
    if (recv_item_by_name_exact(in_ds, "uid", (char *)&state->uid, sizeof(uid_t)) < 0)
    {
        LOGE("Failed receiving uid");
        goto err;
    }

    // start context (tc_init does not return on failure)
    return tc_start(state, true);
err:
    return -1;
}

static int tc_cmd_send(data_stream_t *in_ds, data_stream_t *out_ds, tc_state_t *state)
{

    TC_NS_ClientContext *ctx = &state->ctx;
    char *data = NULL;
    ctx->paramTypes = 0x00;
    int invoke_ret = 0, ret = EXECUTOR_SUCCESS;

    LOGD("%s", __FUNCTION__);
    ctx->returns.code = TEEC_SUCCESS;
    ctx->returns.origin = 0;

    // receive params from host
    if (tc_deserialize_input(in_ds, ctx) < 0)
    {
        LOGE("processing param failed");
        goto err;
    }

    LOGD("Invoking %#x (%#x)", ctx->cmd_id, ctx->paramTypes);
    // dump_ctx(ctx);
    //  hexdump("param_2_a", ctx->params[2].memref.buffer,
    //  *(uint32_t*)ctx->params[2].memref.size_addr);

    dump_ctx(ctx);
    // invoke the requested command
    invoke_ret = invoke_cmd(state->fd, ctx);

    // dump_ctx(ctx);
    //  hexdump("param_2_a", ctx->params[2].memref.buffer,
    //  *(uint32_t*)ctx->params[2].memref.size_addr);

    // send context information back to host
    LOGD("Sending status");
    if (invoke_ret < 0)
        goto err_comm;

    // Write executor status to output stream
    if (!ds_write(out_ds, (char *)&ret, sizeof(int)))
    {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }

    // Write placeholder for size to output stream
    if (!(data = ds_write(out_ds, (char *)&ZERO, sizeof(uint32_t))))
    {
        LOGE("ds_write: error writing to ds");
        goto err_comm;
    }
    uint32_t pos_sz = out_ds->pos - sizeof(uint32_t);

    if (tc_serialize_output(out_ds, ctx) != 0)
        goto err;

    // overwrite size placeholder of output stream
    // we indicate the size of the buffer, hence the sizeof subtraction
    *((uint32_t *)&out_ds->data[pos_sz]) = out_ds->pos - 2 * sizeof(uint32_t);
    LOGD("out_ds->pos: %d", *((uint32_t *)&out_ds->data[pos_sz]));

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

static int tc_cmd_end(tc_state_t *state)
{

    LOGD("%s", __FUNCTION__);
    // close the context fd
    if (close(state->fd) == -1)
    {
        perror("close");
        LOGE("failed to close %s", TC_NS_CLIENT_DEV_NAME);
        goto err;
    }

#ifdef SECURITY_AUTH_ENHANCE
    free(state->ctx.teec_token);
#endif

    return 0;
err:
    return -1;
}

int tc_execute(int data_sock)
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
            if (tc_cmd_start(in_ds, &TC_STATE) == EXECUTOR_ERROR)
                goto err;
            break;
        case TEEZZ_CMD_SEND:
            ds_reset(out_ds);
            if (tc_cmd_send(in_ds, out_ds, &TC_STATE) == EXECUTOR_ERROR)
                goto err;
            if (send_buf(data_sock, out_ds->data, out_ds->pos) < 0)
            {
                LOGE("send_buf: error sending output data");
                goto err;
            }
            break;
        case TEEZZ_CMD_END:
            if (tc_cmd_end(&TC_STATE) == EXECUTOR_ERROR)
                goto err;
            // we want to leave the loop
            is_end = true;
            break;
        case TEEZZ_CMD_TERMINATE:
            if (tc_cmd_end(&TC_STATE) == EXECUTOR_ERROR)
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
