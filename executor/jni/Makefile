CC := aarch64-linux-gnu-gcc

#ifndef OPTEE_CLIENT_LIB
#$(warning Warning: Failed to find libteec.so, please point OPTEE_CLIENT_LIB to \
#       the libteec.so dir, e.g., out-br/build/optee_client-1.0/libteec/.)
#endif

INCLUDE := -Iinclude/
CFLAGS := -std=gnu11 -ggdb -fno-omit-frame-pointer -fsanitize=address -static-libstdc++ -static-libasan
LDFLAGS= -L. -ldl # -L$(OPTEE_CLIENT_LIB) -ldl # -lteec
LOCAL_SRC_FILES := tzzz.c utils.c logging.c optee.c opteelibteec.c opteenet.c gp.c shm_pta.c


all: executor

executor: $(LOCAL_SRC_FILES)
	$(CC) $(CFLAGS) -o $@ $^ $(INCLUDE) $(LDFLAGS)

clean:
	$(RM) -f *.o executor
