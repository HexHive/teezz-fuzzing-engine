import os

HOST = "127.0.0.1"
HOST_EXECUTOR_DIR = "./executor/libs/arm64-v8a/"
HOST_EXECUTOR_NAME = "executor"
HOST_EXECUTOR_PATH = os.path.join(HOST_EXECUTOR_DIR, HOST_EXECUTOR_NAME)
TARGET_EXECUTOR_DIR = "/data/local/tmp/"
TARGET_EXECUTOR_NAME = "teezz-executor"
TARGET_EXECUTOR_PATH = os.path.join(TARGET_EXECUTOR_DIR, TARGET_EXECUTOR_NAME)

TARGET_TZLOG_PATH = "/proc/tzlog"

TAFUZZ_PATH = "/sbin/teecd"

TC_CTX_PREFIX = 'ctx_'
TC_PARAM_PREFIX = 'param_'
