#!/usr/bin/env bash

# usage: ./run_aggregation.sh qsee ./tmp/qsee_random/
#        ./run_aggregation.sh tc ./tmp/tc_format/

set -e
set -u

SCRIPTPATH="$( cd "$(dirname "$0")" ; pwd -P )"

tee=$1 # tc|qsee
evaldir=$2 # dir containing tzlogger.log logs from same tee

for log in `find $evaldir -type f -name "tzlogger.log"`; do
  logdir=`dirname $log`
  outdir="$logdir/`basename $logdir`time/"
  if [ $tee == "tc" ]; then
    $SCRIPTPATH/filter_time.py $log 8 $outdir
    $SCRIPTPATH/aggregate_kernel.py tc $outdir/tzlogger.log.8h | python -m json.tool > $outdir/eval.json
  elif [ $tee == "qsee" ]; then
    $SCRIPTPATH/filter_time.py $log 6 $outdir
    $SCRIPTPATH/aggregate_kernel.py qsee $outdir/tzlogger.log.6h | python -m json.tool > $outdir/eval.json
  else
    echo "tee $tee not known"
    exit
  fi
done

