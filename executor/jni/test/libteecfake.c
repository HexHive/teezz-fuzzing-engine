#include <optee/tee_client_api.h>

TEEC_Result TEEC_InitializeContext (const char *name, TEEC_Context *ctx) {
  return 0;

}

void TEEC_FinalizeContext (TEEC_Context *ctx) {
  return;
}

TEEC_Result TEEC_OpenSession (TEEC_Context *ctx, TEEC_Session *session,
                                const TEEC_UUID *destination,
                                uint32_t connection_method,
                                const void *connection_data,
                                TEEC_Operation *operation,
                                uint32_t *returnOrigin) {
  return 0;
}

void TEEC_CloseSession (TEEC_Session *session) {
  return;
}

TEEC_Result TEEC_InvokeCommand (TEEC_Session *session, uint32_t commandID,
                                  TEEC_Operation *operation,
                                  uint32_t *returnOrigin) {
  return 0;
}

TEEC_Result TEEC_RegisterSharedMemory (TEEC_Context *context,
                                         TEEC_SharedMemory *sharedMem) {
  return 0;
}

TEEC_Result TEEC_AllocateSharedMemory (TEEC_Context *context,
                                         TEEC_SharedMemory *sharedMem) {
  return 0;
}

void TEEC_ReleaseSharedMemory (TEEC_SharedMemory *sharedMemory) {

  return;
}

void TEEC_RequestCancellation (TEEC_Operation *operation) {

  return;
}

