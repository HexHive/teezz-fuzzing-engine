#!/usr/bin/env bash
set -e

ndk-build
adb push libs/arm64-v8a/executor /data/local/tmp/teezz-executor
adb shell 'su -c "chmod 777 /data/local/tmp/teezz-executor"'
adb shell 'su -c "md5sum /data/local/tmp/teezz-executor"'
adb forward tcp:4242 tcp:4242
adb forward tcp:4243 tcp:4243
md5sum libs/arm64-v8a/executor

