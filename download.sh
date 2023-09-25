#!/bin/bash

start=$(pwd)

cd $1
echo "Downloading to..."$(pwd)

cd $start

for month in {01..12}
do 
	echo "Getting $month"
	if [ ! -f 2020-$month.tar.xz ]
	then
		wget https://zenodo.org/record/7650322/files/2020-$month.tar.xz?download=1
		mv 2020-$month.tar.xz?download=1 2020-$month.tar.xz
	fi
	if [ ! -f 2022-$month.tar.xz ]
	then
		wget https://zenodo.org/record/7650318/files/2022-$month.tar.xz?download=1
		mv 2022-$month.tar.xz?download=1 2022-$month.tar.xz
	fi
	if [ ! -f 2021-$month.tar.xz ]
	then
		wget https://zenodo.org/record/7650320/files/2021-$month.tar.xz?download=1
		mv 2021-$month.tar.xz?download=1 2021-$month.tar.xz
	fi
done
