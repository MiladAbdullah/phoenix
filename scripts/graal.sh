#!/bin/bash

open_link() {
    # Check if both month and year arguments are provided
    if [ $# -ne 4 ]; then
        echo "Usage: $0 <month> <year> <downloads>"
        exit 1
    fi

    month=$1
    year=$2

    # Define the links for each month and year combination
    case $year in
        "2016")
            link="https://zenodo.org/records/7659890/files/$year-$month.tar.xz?download=1"
            ;;
        "2017")
            link="https://zenodo.org/records/7659885/files/$year-$month.tar.xz?download=1"
            ;;
        "2018")
            link="https://zenodo.org/records/7659844/files/$year-$month.tar.xz?download=1"
            ;;
        "2019")
            link="https://zenodo.org/records/7657656/files/$year-$month.tar.xz?download=1"
            ;;
        "2020")
            link="https://zenodo.org/records/7650322/files/$year-$month.tar.xz?download=1"
            ;;
        "2021")
            link="https://zenodo.org/records/7650320/files/$year-$month.tar.xz?download=1"
            ;;
        "2022")
            link="https://zenodo.org/records/7650318/files/$year-$month.tar.xz?download=1"
            ;;
        *)
            echo "Invalid year, please provide a year between 2016 and 2022."
            exit 1
            ;;
    esac

    # Open the link
    
    mkdir -p "$3"
    filename="$3/$month-$year.tar.xz"

    if grep -qF "$filename" "$3/downloads.log"; then
        echo "file $filename is already downloaded."
    else
        echo "downloading $link for $month/$year"
        wget $link -P "$3" -O "$filename" -q
        tar -xf $filename -C "$3" || return
        rm $filename 
        foldername="$3/${year}-${month}"
        echo "unzipiing to $foldername ..."
        python $PHOENIX_HOME/scripts/fetch.py $foldername "$4" && (echo "$filename" >> "$3/downloads.log") && rm $foldername -rf
        echo "removing $foldername ..."
    fi
    
    
}


# GraalVM dataset is on https://dl.acm.org/doi/10.1145/3578245.3585025

# Check if the script received at least two arguments
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 <FROM:m-yyyy> <TO:m-yyyy>"
    exit 1
fi

DOWNLOADS="downloads"
SOURCE="source"

download_directory="${PHOENIX_HOME:-.}/$DOWNLOADS"
source_directory="${PHOENIX_HOME:-.}/$SOURCE"

start_month=$(echo $1 | cut -d '-' -f 1)
start_year=$(echo $1 | cut -d '-' -f 2)
end_month=$(echo $2 | cut -d '-' -f 1)
end_year=$(echo $2 | cut -d '-' -f 2)

current_month=$start_month
current_year=$start_year

while [ $current_year -le $end_year ]; do
    while [ $current_month -le 12 ]; do
        # Call the function to open the link
        month=$(printf "%02d" "$current_month")
        open_link $month $current_year $download_directory $source_directory
        
        ((current_month++))
        if [ $current_year -eq $end_year ]; then
            if [ $current_month -gt $end_month ]; then
                break
            fi
        fi
    done

    # Reset month for the next year
    current_month=1

    # Increment the year
    ((current_year++))
done
