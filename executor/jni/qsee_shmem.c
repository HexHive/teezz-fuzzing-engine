#include "logging.h"

#include <stdlib.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "include/qsee_shmem.h"
#include <errno.h>
#include <fcntl.h>
#include <ion/ion.h>

struct ion_info *finger_alloc_shared() {
    int ret;
    struct ion_allocation_data ion_data;
    struct ion_fd_data fd_data;

    struct ion_info *ion_info = malloc(sizeof(ion_info));

    if (!ion_info) {
        LOGE("malloc failed: %s\n", strerror(errno));
        goto exit;
    }

    int ion_fd = open("/dev/ion", O_RDONLY | O_CLOEXEC);
    if (ion_fd == -1) {
        LOGE("open /dev/ion failed: %s\n", strerror(errno));
        goto error_free;
    }

    LOGI("ion_fd %d\n", ion_fd);

    ion_data.len = 4096;
    ion_data.align = 0x1000;
    ion_data.flags = 0;
    ion_data.heap_id_mask = 0x8000000;

    ion_user_handle_t handle;

    ret = ioctl(ion_fd, ION_IOC_ALLOC, &ion_data);
    if (ret < 0) {
        LOGE("ioctl ion failed: %s\n", strerror(errno));
        goto error_close;
    }

    fd_data.handle = ion_data.handle;
    ret = ioctl(ion_fd, ION_IOC_MAP, &fd_data);
    if (ret < 0) {
        LOGE("ioctl ion failed: %s\n", strerror(errno));
        goto error_close;
    }

    void *addr = mmap(0, 0x1000, 3, 1, fd_data.fd, 0);
    if (addr == (void *)-1) {
        LOGE("mmap failed: %s\n", strerror(errno));
        goto error_close;
    }

    ion_info->addr = addr;
    ion_info->handle = ion_data.handle;
    ion_info->length = ion_data.len;
    ion_info->ion_fd = ion_fd;
    ion_info->fd = fd_data.fd;

exit:
    return ion_info;
error_close:
    close(ion_fd);
error_free:
    free(ion_info);
    return NULL;
}
