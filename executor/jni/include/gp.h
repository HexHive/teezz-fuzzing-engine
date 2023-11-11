#ifndef _GP_H_
#define _GP_H_

#include <tc/tc_ns_client.h>

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
int get_params_from_host(int host_sock, TC_NS_ClientContext *ctx);

#endif // _GP_H_

