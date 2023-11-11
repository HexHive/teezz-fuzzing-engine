#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <assert.h>

#include <logging.h>
#include <utils.h>
#include <optee/tee_client_api.h>
#include <optee/opteecom.h>
#include <optee/opteenet.h>


int optee_deserialize_param(data_stream_t *ds, uint32_t paramType,
                    TEEC_Parameter *param)
{
    int ret = 0;

    switch (paramType)
    {
    case TEEC_NONE:
        break;
    case TEEC_VALUE_INPUT:
    case TEEC_VALUE_OUTPUT:
    case TEEC_VALUE_INOUT:
    {

        uint32_t a_val = 0, b_val = 0;
        char *data_p = NULL;

        // get `TEEC_Value.a`
        data_p = ds_read(ds, sizeof(uint32_t));
        if (data_p == NULL) {
            LOGE("ds_read: error receiving `TEEC_Value.a`");
            goto err;
        }
        param->value.a = *(uint32_t*)data_p;

        // get `TEEC_Value.b`
        data_p = ds_read(ds, sizeof(uint32_t));
        if (data_p == NULL) {
            LOGE("ds_read: error receiving `TEEC_Value.b`");
            goto err;
        }
        param->value.b = *(uint32_t*)data_p;

        break;
    }
    case TEEC_MEMREF_TEMP_INPUT:
    case TEEC_MEMREF_TEMP_INOUT:
    {
        char *data_p = NULL;
        char *buf = NULL;
        ssize_t nread = 0;
        ssize_t signaled_buf_sz = 0;

        // get buffer
        if ((nread = parse_lv(ds, &buf)) < 0) {
            LOGD("parse_lv: error parsing memref buffer");
            goto err;
        }
        LOGD("received TEEC_TempMemoryReference.buffer of sz %zd", nread);
        param->tmpref.buffer = buf;

        // get size
        data_p = ds_read(ds, sizeof(uint32_t));
        if (data_p == NULL) {
            LOGE("ds_read: error receiving `size`");
            goto err;
        }
        param->tmpref.size = *(uint32_t*)data_p;
        LOGD("received TEEC_TempMemoryReference.size of %zd", param->tmpref.size);
        if (nread < param->tmpref.size) {
            // TEEC_MEMREF_TEMP_* buffers get copied later. Thus, sizes have to
            // match to prevent corrupting the executor.
            param->tmpref.size = nread;
        }

        break;
    }
    case TEEC_MEMREF_TEMP_OUTPUT:
    {
        // Output buffers deserve special treatment.
        // Instead of receiving a buffer, we receive the actual size of the
        // output buffer first. This is the size our buffer will have in 
        // memory. Second, we receive the size of the buffer communicated to
        // the TEE.
        char *data_p = NULL;

        // get actual size
        data_p = ds_read(ds, sizeof(uint32_t));
        if (data_p == NULL) {
            LOGE("ds_read: error receiving actual `size`");
            goto err;
        }
        param->tmpref.buffer = calloc(1, *(uint32_t*)data_p);
        LOGD("received TEEC_TempMemoryReference.size of %d", *(uint32_t*)data_p);

        // get signaled size
        data_p = ds_read(ds, sizeof(uint32_t));
        if (data_p == NULL) {
            LOGE("ds_read: error receiving signaled `size`");
            goto err;
        }
        param->tmpref.size = *(uint32_t*)data_p;
        LOGD("received signaled output buffer size of %zd", param->tmpref.size);
        break;
    }
    case TEEC_MEMREF_WHOLE:
    case TEEC_MEMREF_PARTIAL_INPUT:
    case TEEC_MEMREF_PARTIAL_OUTPUT:
    case TEEC_MEMREF_PARTIAL_INOUT:
        LOGE("Implement me!");
        break;
    default:
        LOGE("Error, unknown param type 0x%x", paramType);
    }

    return ret;
err:
    return -1;
}

int optee_serialize_op(data_stream_t *ds, TEEC_Operation *op)
{
    uint32_t nsend = 0;
    for (int i = 0; i < TEEC_CONFIG_PAYLOAD_REF_COUNT; i++)
    {
        LOGD("\tparam[%i]:", i);
        int param_type = TEEC_PARAM_TYPE_GET(op->paramTypes, i);

        switch (param_type)
        {
        case TEEC_NONE:
        case TEEC_VALUE_INPUT:
        case TEEC_MEMREF_TEMP_INPUT:
            LOGD("\t\tNONE or INPUT param.");
            // we do not serialize input params
            if(!ds_write(ds, (char*)&ZERO, sizeof(uint32_t))) {
                LOGE("ds_write: error writing to ds");
                goto err;
            }
            break;
        case TEEC_VALUE_OUTPUT:
        case TEEC_VALUE_INOUT:
            // expect two `uint32_t`s
            nsend = 2 * sizeof(uint32_t);
            if(!ds_write(ds, (char*)&nsend, sizeof(uint32_t))) {
                LOGE("ds_write: error writing to ds");
                goto err;
            }
            // write values
            if(!ds_write(ds, (char *)&op->params[i].value.a, sizeof(uint32_t))) {
                LOGE("ds_write: error writing to ds");
                goto err;
            }
            if(!ds_write(ds, (char *)&op->params[i].value.b, sizeof(uint32_t))) {
                LOGE("ds_write: error writing to ds");
                goto err;
            }
            break;
        case TEEC_MEMREF_TEMP_OUTPUT:
        case TEEC_MEMREF_TEMP_INOUT:
            // write size
            if(!ds_write(ds, (char *)&op->params[i].tmpref.size, sizeof(uint32_t))) {
                LOGE("ds_write: error writing to ds");
                goto err;
            }

            // write buffer
            if (op->params[i].tmpref.size > 0)
            {
                assert(op->params[i].tmpref.buffer != NULL);
                LOGD("\t\tbuffer@ %p with sz %zd",
                     (void *)op->params[i].tmpref.buffer, op->params[i].tmpref.size);
                if(!ds_write(ds, (char *)op->params[i].tmpref.buffer, op->params[i].tmpref.size)) {
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

int optee_deserialize_input(data_stream_t *ds, struct tee_ioctl_invoke_arg *arg, TEEC_Operation *op, uint32_t *cmd_id) {
    int ret = 0;
    uint32_t *param_types_p = NULL;
    char* data = NULL;

    data = ds_read(ds, sizeof(struct tee_ioctl_invoke_arg));
    if (!data) {
        LOGE("ds_read: error parsing tee_ioctl_invoke_arg");
        goto err;
    }
    memcpy(arg, data, sizeof(struct tee_ioctl_invoke_arg));

    *cmd_id = arg->func;
    LOGD("cmdid: %#x", *cmd_id);

    param_types_p = (uint32_t*) ds_read(ds, sizeof(uint32_t));
    if (param_types_p == NULL) {
        LOGE("ds_read: error parsing param types");
        goto err;
    }
    op->paramTypes = *param_types_p;
    LOGD("paramTypes: 0x%x", op->paramTypes);

    for (int i = 0; i < TEEC_CONFIG_PAYLOAD_REF_COUNT; i++)
    {
        ret = optee_deserialize_param(ds,
                              TEEC_PARAM_TYPE_GET(op->paramTypes, i),
                              &op->params[i]);
        if(ret < 0)
            goto err;
        LOGD("got param: %i", i);
    }

    return 0;
err:
    return -1;
}

int optee_serialize_output(data_stream_t *ds, struct tee_ioctl_invoke_arg *arg, TEEC_Operation *op) {

    uint32_t sz = sizeof(struct tee_ioctl_invoke_arg);
    if(!ds_write(ds, (char*)&sz, sizeof(uint32_t))) {
        LOGE("ds_write: error writing `tee_ioctl_invoke_arg` size.");
        goto err;
    }

    if(!ds_write(ds, (char*)arg, sz)) {
        LOGE("ds_write: error writing `tee_ioctl_invoke_arg`.");
        goto err;
    }

    // do not serialize output params if call was not successful
    if(arg->ret == TEEC_SUCCESS) {
        // Serialize all output parameters
        if (optee_serialize_op(ds, op))
        {
            LOGE("Error writing data back to host.");
            goto err;
        }
    }

    return 0;
err:
    return -1;
}