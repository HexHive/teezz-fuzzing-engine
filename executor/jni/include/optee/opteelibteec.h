#ifndef _OPTEE_H_
#define _OPTEE_H_

#include <optee/tee_client_api.h>

typedef struct libteec_ops {
    TEEC_Result (*TEEC_InitializeContext)(const char *name, TEEC_Context *ctx);
    void (*TEEC_FinalizeContext)(TEEC_Context *ctx);
    TEEC_Result (*TEEC_OpenSession)(TEEC_Context *ctx, TEEC_Session *session,
                                    const TEEC_UUID *destination,
                                    uint32_t connection_method,
                                    const void *connection_data,
                                    TEEC_Operation *operation,
                                    uint32_t *returnOrigin);
    void (*TEEC_CloseSession)(TEEC_Session *session);
    TEEC_Result (*TEEC_InvokeCommand)(TEEC_Session *session, uint32_t commandID,
                                      TEEC_Operation *operation,
                                      uint32_t *returnOrigin);
    TEEC_Result (*TEEC_RegisterSharedMemory)(TEEC_Context *context,
                                             TEEC_SharedMemory *sharedMem);
    TEEC_Result (*TEEC_AllocateSharedMemory)(TEEC_Context *context,
                                             TEEC_SharedMemory *sharedMem);
    void (*TEEC_ReleaseSharedMemory)(TEEC_SharedMemory *sharedMemory);
    void (*TEEC_RequestCancellation)(TEEC_Operation *operation);
    // TODO imports
} libteec_ops_t;

typedef struct libteec_handle {
    void *libhandle;
    libteec_ops_t ops;
} libteec_handle_t; 

libteec_handle_t *init_libteec_handle(const char* libpath);

#endif // _OPTEE_H_
