
## SETUP :wrench:

Build the docker image:
```
make build
```

Spawn a docker container:
```
make run
```

Make sure you can see the device from inside of the container
```
root@7582085cc876:/src/executor# adb devices
* daemon not running; starting now at tcp:5037
* daemon started successfully
List of devices attached
712KPBF1235565  device
```

Build the executor and deploy it on the device:
```
cd /src/executor
make

adb push libs/arm64-v8a/executor /data/local/tmp/teezz-executor
adb shell 'su 0 chmod u+x /data/local/tmp/teezz-executor'
adb forward tcp:4242 tcp:4242
adb forward tcp:4243 tcp:4243
```

The seeds in `/teezz-in` should have the following structure:
```
/teezz-in
└── 0
    ├── 0
    │   ├── onenter
    │   │   ├── qseecom_send_cmd_req
    │   │   ├── req
    │   │   └── resp
    │   └── onleave
    │       ├── qseecom_send_cmd_req
    │       ├── req
    │       └── resp
    ├── 1
    │   ├── onenter
    │   │   ├── qseecom_send_cmd_req
    │   │   ├── req
    │   │   └── resp
    │   └── onleave
    │       ├── qseecom_send_cmd_req
    │       ├── req
    │       └── resp
[...]
```

## Fuzzing

Now start fuzzing:
```
source ~/.venv/bin/activate
cd /src
make fuzz-adb TEE=qsee IN=/teezz-in OUT=/teezz-out
```

