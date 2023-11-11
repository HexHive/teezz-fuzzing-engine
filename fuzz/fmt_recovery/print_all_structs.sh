#!/bin/bash

set -e

FILES="$(find $1 -name '*.types')"


for FILE in $FILES; do echo $FILE; $(dirname $0)/unpickle.py $FILE; done
