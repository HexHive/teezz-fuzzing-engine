#!/bin/bash

cd ../..

dir="crashSequence/tc/keystore/BUC4C16B24013822/2019-*"

crashes=0
num_sequences=0

for crash in $dir;
do
	echo "Running crash sequence" ${crash}
	success=$(python -m fuzz.fuzz \
		-t ${crash} \
		--config ./fuzz/config/tc-BUC4C16B24013822/tc_km.json \
		-x tc -d BUC4C16B24013822 \
		-p 4263 2>&1 | grep "App crashed" | wc -l)
	if [ $success -ge 1 ]
	then
		crashes=$((crashes+1))
	fi
	num_sequences=$((num_sequences+1))
	echo "Detected" $crashes "crashes of" $num_sequences "crash sequences"
done


