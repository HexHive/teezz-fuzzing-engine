#include <stdlib.h>
#include <fcntl.h>
#include <dlfcn.h>

#include <logging.h>
#include <optee/opteelibteec.h>

static int libteec_get_lib_sym(const char* libpath, libteec_handle_t *handle)
{
    handle->libhandle = dlopen(libpath, RTLD_NOW | RTLD_GLOBAL);
    if (handle->libhandle)
    {
        *(void **)(&handle->ops.TEEC_InitializeContext) =
            dlsym(handle->libhandle, "TEEC_InitializeContext");
        if (handle->ops.TEEC_InitializeContext == NULL)
        {
            LOGE("dlsym: Error loading TEEC_InitializeContext");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_FinalizeContext) =
            dlsym(handle->libhandle, "TEEC_FinalizeContext");
        if (handle->ops.TEEC_FinalizeContext == NULL)
        {
            LOGE("dlsym: Error loading TEEC_FinalizeContext");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_OpenSession) =
            dlsym(handle->libhandle, "TEEC_OpenSession");
        if (handle->ops.TEEC_OpenSession == NULL)
        {
            LOGE("dlsym: Error loading TEEC_OpenSession");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_CloseSession) =
            dlsym(handle->libhandle, "TEEC_CloseSession");
        if (handle->ops.TEEC_CloseSession == NULL)
        {
            LOGE("dlsym: Error loading TEEC_CloseSession");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_InvokeCommand) =
            dlsym(handle->libhandle, "TEEC_InvokeCommand");
        if (handle->ops.TEEC_InvokeCommand == NULL)
        {
            LOGE("dlsym: Error loading TEEC_InvokeCommand");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_RegisterSharedMemory) =
            dlsym(handle->libhandle, "TEEC_RegisterSharedMemory");
        if (handle->ops.TEEC_RegisterSharedMemory == NULL)
        {
            LOGE("dlsym: Error loading TEEC_RegisterSharedMemory");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_AllocateSharedMemory) =
            dlsym(handle->libhandle, "TEEC_AllocateSharedMemory");
        if (handle->ops.TEEC_AllocateSharedMemory == NULL)
        {
            LOGE("dlsym: Error loading TEEC_AllocateSharedMemory");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_ReleaseSharedMemory) =
            dlsym(handle->libhandle, "TEEC_ReleaseSharedMemory");
        if (handle->ops.TEEC_ReleaseSharedMemory == NULL)
        {
            LOGE("dlsym: Error loading TEEC_ReleaseSharedMemory");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
        *(void **)(&handle->ops.TEEC_RequestCancellation) =
            dlsym(handle->libhandle, "TEEC_RequestCancellation");
        if (handle->ops.TEEC_RequestCancellation == NULL)
        {
            LOGE("dlsym: Error loading TEEC_RequestCancellation");
            dlclose(handle->libhandle);
            handle->libhandle = NULL;
            return -1;
        }
    }
    else
    {
        LOGE("failed to load teec library");
        LOGE("%s", dlerror());
        return -1;
    }
    return 0;
}

libteec_handle_t *init_libteec_handle(const char* libpath)
{
    libteec_handle_t *handle =
        (libteec_handle_t *) calloc(1, sizeof(libteec_handle_t));
    if (handle == NULL)
    {
        LOGE("Memalloc for libteec handle failed!");
        return NULL;
    }
    handle->libhandle = NULL;
    int ret = libteec_get_lib_sym(libpath, handle);
    if (ret < 0)
    {
        LOGE("get_lib_syms failed!");
        free(handle);
        return NULL;
    }
    LOGI("Successfully loaded %s", libpath);
    return handle;
}