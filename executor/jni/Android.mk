LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE := executor
LOCAL_CFLAGS += -std=gnu11 -ggdb -Werror #-DSECURITY_AUTH_ENHANCE
LOCAL_SRC_FILES := tzzz.c tc.c utils.c logging.c tc_logging.c qsee.c beanpod.c \
  qsee_shmem.c gp.c optee.c opteenet.c opteelibteec.c shm_pta.c
LOCAL_LDFLAGS += -L. -ldl
LOCAL_C_INCLUDES := $(LOCAL_PATH)/include
include $(BUILD_EXECUTABLE)
