executor
========

# Deploying

If you are building for newer Huawei devices, check if you need `-DSECURITY_AUTH_ENHANCE` in your `CFLAGS` in `Android.mk`.

```
./deploy.sh
```

# Coding Convention

The coding convention can be applied to `file.c` using the following command:
```
clang-format <file>.c -i -style="{BasedOnStyle: llvm, IndentWidth: 4}"
```

# OPTEE Modes

afl

```
COVFEEDBACK=1 SHMSZ=65536 executor optee 4242
```

edgecov
```
mkdir /mnt/share/cov
COVCOLLECTDIR=/mnt/share/cov SHMSZ=65536 executor optee 4242
```
