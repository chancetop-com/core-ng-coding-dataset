#!/bin/bash
# @author stephen

if [ -z "$1" ]; then
    echo "Usage: $0 <class_path>"
    exit 1
fi

if [ ! -f "$1" ]; then
  echo "File not found!"
  exit 1
fi

java_file=$1
filename=$(basename "$java_file")

echo -e "The source code of java class $filename:"
echo '```java'
cat "$java_file"
echo '```'