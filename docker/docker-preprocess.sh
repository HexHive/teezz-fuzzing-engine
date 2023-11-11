#!/usr/bin/env bash

################################################################################
# GLOBALS
################################################################################

RAW_DIR=/seeds-raw
OUT_DIR=/seeds-dirty
TMP_DIR=`mktemp -d`

set -eu

################################################################################
# ENTRYPOINT LOGIC
################################################################################

echo "Intermediate results in tmpdir: ${TMP_DIR}"

# copy raw seeds to tmpdir
for d in `find $RAW_DIR -maxdepth 2 -mindepth 2 -type d`
do
  echo "$d"
  dir=`dirname $d`
  cp -r $d $TMP_DIR/`basename $dir`-test;
done

source /root/.venv/bin/activate

python3 -m fuzz.fmt_recovery.rearrange_dualrecord $TMP_DIR
python3 -m fuzz.fmt_recovery ${TEE} $TMP_DIR/out $TMP_DIR/out

for d in `find ${TMP_DIR}/out -maxdepth 1 -mindepth 1 -type d`;
do
  if [[ "`ls $d | wc -l`" == 0 ]]; then
    echo "${d} is empty and removed"
    rm -rf ${d}
  fi
done

mv $TMP_DIR/out/* $OUT_DIR
