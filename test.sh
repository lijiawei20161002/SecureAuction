#!/bin/bash

for i in `seq 0 8`
do
    echo "$(python main.py -M 9 -I $i 5 10) \n\n" &
done
wait