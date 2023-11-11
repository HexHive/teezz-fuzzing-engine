#include <optee/tee_client_api.h>
#include <optee/opteecom.h>
#include <utils.h>

#ifndef _OPTEENET_H_
#define _OPTEENET_H_


int optee_deserialize_input(data_stream_t *ds, struct tee_ioctl_invoke_arg *arg, TEEC_Operation *op, uint32_t *cmd_id);
int optee_serialize_output(data_stream_t *ds, struct tee_ioctl_invoke_arg *arg, TEEC_Operation *op);
int optee_deserialize_param(data_stream_t *ds, uint32_t paramType,
                    TEEC_Parameter *param);
/*
 * Write params to ds.
 *
 * \param ds output data stream to write to
 * \param op TEEC_Operation holding the params we'll send to the host
 *
 * \return 0 on success, non-zero on error
 */
int optee_serialize_op(data_stream_t *ds, TEEC_Operation *op);

#endif // _OPTEENET_H_