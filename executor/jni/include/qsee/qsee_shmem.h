#ifndef _QSEE_SHMEM_H_
#define _QSEE_SHMEM_H_
#include <ion/ion.h>

struct ion_info {
    void *addr;
    ion_user_handle_t handle;
    size_t length;
    int ion_fd;
    int fd;
};

struct ion_info *finger_alloc_shared();

#endif //_QSEE_SHMEM_H_
