#include <optee/tee_client_api.h>

#ifndef SHM_PTA_H
#define SHM_PTA_H

int register_shm_pta(libteec_handle_t *libteec, TEEC_Context *ctx, TEEC_SharedMemory *in_shm);
int unregister_shm_pta(libteec_handle_t *libteec, TEEC_Context *ctx);

#endif /*SHM_PTA_H*/
