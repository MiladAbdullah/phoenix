#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Please provide a folder as parameter"
    exit 1
fi

rawDataPath=$1

if [ ! -d $rawDataPath ]; then
	echo "Parameter should be a folder, but $rawDataPath is not a folder"
	exit 1
fi

start=$(pwd)

for year in 2020 2021 2022
do
	for month in {01..12}
	do
		cd $rawDataPath
		echo "Extracting $year-$month"	
		tar -xf $year-$month.tar.xz
		cd $start
		for benchmark in 136 109 291 292
		do
			echo "Calling extract script"
			python3 extract.py \
	       	     		  -y -w \
		        	  -d \
		         	$rawDataPath/$year-$month --extract \
		       		--benchmark $benchmark --machine_type 6
		done
		rm -r $rawDataPath/$year-$month
	done
done
