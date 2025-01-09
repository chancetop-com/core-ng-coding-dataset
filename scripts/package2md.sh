#!/bin/bash
# @author stephen

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <absolute_path_to_java_project> <package_path>"
    exit 1
fi

PROJECT_DIR="$1"
PACKAGE_PATH="$2"

PACKAGE_NAME=$(basename "$PACKAGE_PATH")

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Java project directory $PROJECT_DIR does not exist."
    exit 1
fi

if [ ! -d "$PACKAGE_PATH/src/main/java" ]; then
    echo "Error: Package directory $PACKAGE_PATH/src/main/java does not exist."
    exit 1
fi

echo "Here is the source code of package $PACKAGE_NAME:"
echo "tree $PACKAGE_PATH/src/main/java:"
tree "$PACKAGE_PATH/src/main/java"

find "$PACKAGE_PATH/src/main/java" -name "*.java" | while read -r java_file; do
    filename=$(basename "$java_file")
    
    echo -e "\n$filename"
    
    echo '```java'
    
    cat "$java_file"
    
    echo '```'
done