#!/bin/bash

for i in `seq 0 3`
do
    echo "$(python main.py -M 4 -I $i 5 10) \n\n" &
done
wait