#!/bin/bash
touch commits.txt

if (( $# != 3 ));then
    echo "Usage examples: \n."
    exit 1
else
    code_path=$1
    class_name=$3
    file_name="$code_path/$2/$class_name.java"
fi
echo $file_name

git log --format="%h" $file_name > commits.txt
python ../../android-static-analyzer/get_data.py $1 $2 $3 # get the current commit first

while read p; do
    git checkout $p 2>/dev/null 1>/dev/null
    python ../../android-static-analyzer/get_data.py $1 $2 $3
done <commits.txt

git checkout develop 2>/dev/null 1>/dev/null

rm commits.txt
