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

for year in 2021 2022
do
	for month in {01..12}
	do
		cd $rawDataPath
		echo "Extracting $year-$month"	
		tar -xf $year-$month.tar.xz
		cd $start
		for benchmark in 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 117 118 119 120 121 122 123 126 127 128 129 130 131 132 135 136 137 138 139 140 141 142 143 144 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239 240 241 242 243 244 245 246 247 248 249 251 252 253 254 255 256 257 258 259 260 261 263 265 266 267 268 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 285 286 287 288 289 290 291 292 293 294 295 296 297 298 299 300 301 302 303 304 305 306 307 308 309 310 311 312 313 314 315 316 317 318 319 320 321 322 323 324 325 99
		do
			echo "Calling extract script"
			python3 extract.py \
	       	     		  -y -w \
		        	  -d \
		         	$rawDataPath/$year-$month --extract 
		done
		rm -r $rawDataPath/$year-$month
	done
done
