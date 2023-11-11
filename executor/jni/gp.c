#include <string.h>
#include <assert.h>
#include <stdlib.h>
#include <gp.h>
#include "utils.h"
#include "logging.h"

/*
 * Helper functions for GlobalPlatform API-related tasks
 */

/*
 * Receive parameter from the fuzzer running on the host.
 *
 * \param host_sock  socket for host communication
 * \param ctx        The received parameter are stored in this context
 *
 * \return 0 on success, non-zero on error
 *
 * \todo refactor
 */
int get_params_from_host(int host_sock, TC_NS_ClientContext *ctx) {
    // get cmd_id
    char *cmd_id = NULL;
    ssize_t nread = 0;
    if ((nread = read_data_log("cmd_id", host_sock, &cmd_id)) == -1) {
        return -1;
    }

    if (nread != MEMBER_SIZE(TC_NS_ClientContext, cmd_id)) {
        LOGE("cmd_id size mismatch\n");
        return -1;
    }

    ctx->cmd_id = *((__u32 *)cmd_id);
    free(cmd_id);

    for (int i = 0; i < NPARAMS; i++) {
        __u32 param_type = 0;
        char *tmp_param_type = NULL;

        LOGD(" ### getting param %d ###\n", i);

        if ((nread = read_data_log("param_type", host_sock, &tmp_param_type)) ==
            -1) {
            return -1;
        }

        LOGD("param_type_sz: %lu\n", (unsigned long)nread);
        LOGD("sizeof(__u32): %lu\n", (unsigned long)sizeof(__u32));
        if (nread != sizeof(__u32)) {
            LOGE("param_type_size mismatch\n");
            return -1;
        }

        param_type = *((__u32 *)tmp_param_type);
        free(tmp_param_type);

        /*
         * This is a really ugly hack for avoiding the implementation of PARTIAL
         * MEMREF arguments. The parameter are treated as TEMP MEMREFs such that
         * the kernel copies the data from userland without using shared memory.
         *
         * TODO: This should be fixed.
         */
        if (param_type >= TEEC_MEMREF_PARTIAL_INPUT) {
            param_type -= 8;
        }

        LOGD(" ### param_type: %d ###\n", param_type);

        ctx->paramTypes = ctx->paramTypes | ((unsigned)param_type << (i * 4));

        switch (param_type) {
        case TEEC_NONE:
            ctx->params[i].memref.buffer = 0x00;
            ctx->params[i].memref.offset = 0x00;
            ctx->params[i].memref.size_addr = 0x00;
            break;
        case TEEC_VALUE_INPUT:
        case TEEC_VALUE_INOUT:
        case TEEC_VALUE_OUTPUT: {
            // process value_a
            LOGD(" ### val a ###\n");
            char *value_a_buf = 0;
            if (param_type != TEEC_VALUE_OUTPUT) {
                if ((nread = read_data_log("value.a_addr", host_sock,
                                           &value_a_buf)) == -1) {
                    LOGE("error reading value_a\n");
                    return -1;
                }
            } else {
                // consume empty line
                if ((nread = read_data_log("value.a_addr", host_sock,
                                           &value_a_buf)) == -1) {
                    LOGE("error reading value_a\n");
                    return -1;
                }
                assert(nread == 0);
            }
            ctx->params[i].value.a_addr = (__u64 *)value_a_buf;

            LOGD(" ### val b ###\n");
            // process value_b
            char *value_b_buf = 0;
            if (param_type != TEEC_VALUE_OUTPUT) {
                if ((nread = read_data_log("value.b_addr", host_sock,
                                           &value_b_buf)) == -1) {
                    LOGE("error reading value_b\n");
                    return -1;
                }
            } else {
                // consume empty line
                if ((nread = read_data_log("value.b_addr", host_sock,
                                           &value_b_buf)) == -1) {
                    LOGE("error reading value_b\n");
                    return -1;
                }
                assert(nread == 0);
            }
            //ctx->params[i].value.b_addr = (__u64 *)value_b_buf;
            // TODO: this is just a dirty hack to have val_a and val_b reside next to each
            // other in memory.
            // Fix this later by allocating one chunk of mem for val_a and val_b.
            // At this point, we are certain that TC handles it this way.
            ctx->params[i].value.b_addr = 
              (__u64*)(((char*)ctx->params[i].value.a_addr) + 4);
            *ctx->params[i].value.b_addr = *(uint32_t*)value_b_buf;
            break;
        }
        case TEEC_MEMREF_TEMP_INPUT:
        case TEEC_MEMREF_TEMP_OUTPUT:
        case TEEC_MEMREF_TEMP_INOUT: {
            // order of received data: size, buffer, offset

            // process size
            char *tmp_size = 0;

            if ((nread = read_data_log("size", host_sock, &tmp_size)) == -1) {
                return -1;
            }

            if (tmp_size) {
                ctx->params[i].memref.size_addr =
                    (__u64)calloc(1, sizeof(__u32));
                *(__u32 *)(ctx->params[i].memref.size_addr) =
                    *((__u32 *)tmp_size);
            } else {
                ctx->params[i].memref.size_addr = 0x00;
            }

            free(tmp_size);
            LOGD("received size %#x\n",
                 *(uint32_t *)ctx->params[i].memref.size_addr);

            // process buffer
            char *tmp_buf = 0;

            if ((nread = read_data_log("memref.buffer", host_sock, &tmp_buf)) ==
                -1) {
                return -1;
            }

            if (tmp_buf) {
                ctx->params[i].memref.buffer = (__u64)calloc(1, nread);
                if (nread > *(__u32 *)(ctx->params[i].memref.size_addr)) {
                    LOGI("received buffer (%#lx) is bigger "
                         "than expected size (%#x)\n",
                         (long)nread,
                         *(__u32 *)(ctx->params[i].memref.size_addr));
                }
                memcpy((void *)(ctx->params[i].memref.buffer), tmp_buf, nread);
            } else {
                ctx->params[i].memref.buffer = 0x00;
            }

            free(tmp_buf);
            LOGD("received buffer %#x %#x %#x ... (sz: %#lx)\n",
                 ((uint8_t *)ctx->params[i].memref.buffer)[0],
                 ((uint8_t *)ctx->params[i].memref.buffer)[2],
                 ((uint8_t *)ctx->params[i].memref.buffer)[3], (long)nread);

            // process offset
            char *tmp_offset = 0;

            if ((nread = read_data_log("offset", host_sock, &tmp_offset)) ==
                -1) {
                return -1;
            }

            /*
               if (tmp_offset) {
               ctx->params[i].memref.offset = (__u64)
               malloc(sizeof(__u64));
               *(__u64 *)(ctx->params[i].memref.offset) =
               *((__u64*)tmp_offset); } else {
               ctx->params[i].memref.offset = 0x00;
               }
             */
            // we do not care for offset for now, it is not used
            // anyway
            ctx->params[i].memref.offset = 0x00;
            free(tmp_offset);
            LOGD("received offset %#llx\n", ctx->params[i].memref.offset);

            break;
        }
        case TEEC_MEMREF_WHOLE:
            LOGE("param type %#x not implemented\n", param_type);
            return -1;
        case TEEC_MEMREF_PARTIAL_INPUT:
            LOGE("param type %#x not implemented\n", param_type);
            return -1;
        case TEEC_MEMREF_PARTIAL_OUTPUT:
            LOGE("param type %#x not implemented\n", param_type);
            return -1;
        case TEEC_MEMREF_PARTIAL_INOUT:
            LOGE("param type %#x not implemented\n", param_type);
            return -1;
        default:
            LOGE("param type %#x unknown\n", param_type);
            return -1;
        }
    }
    return 0;
}
