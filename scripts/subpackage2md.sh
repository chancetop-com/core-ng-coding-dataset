#!/bin/bash
# @author stephen

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <absolute_path_to_java_project> <sub_package_path>"
    exit 1
fi

PROJECT_DIR="$1"
SUB_PACKAGE_PATH="$2"

PACKAGE_NAME=$(basename "$(echo "$SUB_PACKAGE_PATH" | awk -F'/src/main/java' '{print $1}')")
SUB_PACKAGE_NAME=$(echo "$SUB_PACKAGE_PATH" | awk -F'/src/main/java' '{print $2}' | sed 's#^/##' | tr '/' '.')

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Java project directory $PROJECT_DIR does not exist."
    exit 1
fi

if [ ! -d "$SUB_PACKAGE_PATH" ]; then
    echo "Error: Package directory $SUB_PACKAGE_PATH does not exist."
    exit 1
fi

echo "Here is the source code of $PACKAGE_NAME package $SUB_PACKAGE_NAME:"

find "$SUB_PACKAGE_PATH" -name "*.java" | while read -r java_file; do
    filename=$(basename "$java_file")
    echo -e "\n$filename" 
    echo '```java'
    cat "$java_file"
    echo '```'
done