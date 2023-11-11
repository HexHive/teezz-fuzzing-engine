#include <tc/tc_logging.h>
#include <tc/tc.h>
#include <logging.h>
#include <inttypes.h>


void dump_tc_state(tc_state_t *state) {

    LOGD("uid: %d", state->uid);
    LOGD("process_name: %s", state->process_name);
    LOGD("cmd_id: 0x%02hhx", (char)state->ctx.cmd_id);

    LOGD("login blob: ");
    for (int j = 0; j < 16; j++) {
        LOGD("%02hhx", state->login_blob[j]);
    }
    LOGD("...");

    dump_ctx(&state->ctx);
}

void dump_ctx(TC_NS_ClientContext *ctx) {

    LOGD("uuid: %02x%02x%02x%02x%02x%02x%02x%02x", ctx->uuid[0], ctx->uuid[1],
         ctx->uuid[2], ctx->uuid[3], ctx->uuid[4], ctx->uuid[5], ctx->uuid[6],
         ctx->uuid[7]);

    LOGD("session_id: %#x", ctx->session_id);
    ;
    LOGD("cmd_id: %#x", ctx->cmd_id);

    LOGD("returns:");
    LOGD("\tcode: %#x", ctx->returns.code);
    LOGD("\torigin: %#x", ctx->returns.origin);

    LOGD("login:");
    LOGD("\tmethod: %#x", ctx->login.method);
    LOGD("\tmdata: %#x", ctx->login.mdata);

    LOGD("params:");
    for (int i = 0; i < NPARAMS; i++) {
        LOGD("\tparam[%i]:", i);
        if (TEEC_PARAM_TYPE_GET(ctx->paramTypes, i) >= TEEC_MEMREF_TEMP_INPUT) {
            char print_buf[128] = {0};
            if (ctx->params[i].memref.buffer) {
                for (int j = 0; j < 16; j++) {
                    snprintf(&print_buf[j * 4], 5, "\\x%02hhx",
                             ((char *)ctx->params[i].memref.buffer)[j]);
                    // LOGD("%02hhx", ((char*)ctx->params[i].memref.buffer)[j]);
                }
                LOGD("\t\tbuffer: %s [...]", print_buf);
            } else {
                LOGD("\t\tbuffer: NULL");
            }
            if (ctx->params[i].memref.offset) {
                LOGD("\t\toffset: 0x%llx --> 0x%llx",
                     (unsigned long long)(ctx->params[i].memref.offset),
                     *(unsigned long long *)(ctx->params[i].memref.offset));
            } else {
                LOGD("\t\toffset: 0x0");
            }

            if (ctx->params[i].memref.size_addr) {
                LOGD("\t\tsize_addr: 0x%llx --> 0x%llx",
                     (unsigned long long)(ctx->params[i].memref.size_addr),
                     *(unsigned long long *)(ctx->params[i].memref.size_addr));
            } else {
                LOGD("\t\tsize_addr: NULL");
            }
        } else if (TEEC_PARAM_TYPE_GET(ctx->paramTypes, i) <= TEEC_NONE) {
            LOGD("\t\tNONE");
        } else {
            // print value a
            if (ctx->params[i].value.a_addr) {
                LOGD("\t\tvalue_a_addr: %p--> 0x%" PRIx64,
                     (void*)(ctx->params[i].value.a_addr),
                     *(uint64_t*)ctx->params[i].value.a_addr);
            } else {
                LOGD("\t\tvalue_a_addr: NULL");
            }
            // print value b
            if (ctx->params[i].value.b_addr) {
                LOGD("\t\tvalue_b_addr: %p --> 0x%" PRIx64,
                     (void*)(ctx->params[i].value.b_addr),
                     *(uint64_t*)ctx->params[i].value.b_addr);
            } else {
                LOGD("\t\tvalue_b_addr: NULL");
            }
        }
    }

    LOGD("paramTypes: %x", ctx->paramTypes);
    LOGD("started: %x", ctx->started);

    return;
}
