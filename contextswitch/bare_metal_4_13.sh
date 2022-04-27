#!/bin/bash
for i in `seq 1 1 13`
do
	c=0
	for b in `seq 1 1 $i`
	do
		for d in `seq 0 1 3`
		do
			mkdir -p test_4_13/test_4_13_$i/$c/
			sudo taskset -c $c ./cpubench.sh test_4_13/test_4_13_$i/$c &
			c=`expr $c + 1`
		done
		
	done
	wait
done
