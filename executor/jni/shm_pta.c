#include <err.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>

#include <optee/tee_client_api.h>
#include <optee/opteelibteec.h>


#define SHM_PTA_UUID \
		{ 0x3e1c44bf, 0xf8c6, 0x4c3c, \
			{ 0x13, 0x37, 0x5d, 0xa2, 0x14, 0x00, 0xd0, 0xcb } }

#define SHM_PTA_CMD_REGISTER_SHM		0
#define SHM_PTA_CMD_UNREGISTER_SHM		3

int register_shm_pta(libteec_handle_t *libteec, TEEC_Context *ctx, TEEC_SharedMemory *in_shm)
{
	TEEC_Session sess;
	TEEC_Operation op;
	TEEC_UUID uuid = SHM_PTA_UUID;
	TEEC_Result res;
	uint32_t err_origin;

	res = libteec->ops.TEEC_OpenSession(ctx, &sess, &uuid,
			       TEEC_LOGIN_PUBLIC, NULL, NULL, &err_origin);
	if (res != TEEC_SUCCESS)
		errx(1, "TEEC_Opensession failed with code 0x%x origin 0x%x",
			res, err_origin);

	memset(&op, 0, sizeof(op));

	// call unregister first to remove potentially remaining shared mems
	op.paramTypes = TEEC_PARAM_TYPES(TEEC_NONE, TEEC_NONE,
					 TEEC_NONE, TEEC_NONE);

	res = libteec->ops.TEEC_InvokeCommand(&sess, SHM_PTA_CMD_UNREGISTER_SHM, &op,
				 &err_origin);

	memset(&op, 0, sizeof(op));
	op.paramTypes = TEEC_PARAM_TYPES(TEEC_MEMREF_PARTIAL_INOUT, TEEC_NONE,
					 TEEC_NONE, TEEC_NONE);

	op.params[0].memref.parent = in_shm;
	op.params[0].memref.size = in_shm->size;

	res = libteec->ops.TEEC_InvokeCommand(&sess, SHM_PTA_CMD_REGISTER_SHM, &op,
				 &err_origin);

	if (res != TEEC_SUCCESS)
		errx(1, "TEEC_InvokeCommand failed with code 0x%x origin 0x%x",
			res, err_origin);
	libteec->ops.TEEC_CloseSession(&sess);
        return res;
}

int unregister_shm_pta(libteec_handle_t *libteec, TEEC_Context *ctx)
{
	TEEC_Session sess;
	TEEC_Operation op;
	TEEC_UUID uuid = SHM_PTA_UUID;
	TEEC_Result res;
	uint32_t err_origin;

	res = libteec->ops.TEEC_OpenSession(ctx, &sess, &uuid,
			       TEEC_LOGIN_PUBLIC, NULL, NULL, &err_origin);
	if (res != TEEC_SUCCESS)
		errx(1, "TEEC_Opensession failed with code 0x%x origin 0x%x",
			res, err_origin);

	memset(&op, 0, sizeof(op));

	op.paramTypes = TEEC_PARAM_TYPES(TEEC_NONE, TEEC_NONE,
					 TEEC_NONE, TEEC_NONE);

	res = libteec->ops.TEEC_InvokeCommand(&sess, SHM_PTA_CMD_UNREGISTER_SHM, &op,
				 &err_origin);

	if (res != TEEC_SUCCESS)
		errx(1, "TEEC_InvokeCommand failed with code 0x%x origin 0x%x",
			res, err_origin);
	libteec->ops.TEEC_CloseSession(&sess);
        return res;
}
