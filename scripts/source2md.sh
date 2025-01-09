#!/bin/bash
# @author stephen

# 检查是否传入了 Java 项目路径和包路径
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: $0 <absolute_path_to_java_project> <package_path>"
    exit 1
fi

# 定义 Java 项目路径和包路径
PROJECT_DIR="$1"
PACKAGE_PATH="$2"

# 从包路径中提取包名（最后一部分）
PACKAGE_NAME=$(basename "$PACKAGE_PATH")

# 检查 Java 项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: Java project directory $PROJECT_DIR does not exist."
    exit 1
fi

# 检查包路径是否存在
if [ ! -d "$PACKAGE_PATH/src/main/java" ]; then
    echo "Error: Package directory $PACKAGE_PATH/src/main/java does not exist."
    exit 1
fi

# 生成目录结构
echo "Here is the source code of package $PACKAGE_NAME:"
echo "tree $PACKAGE_PATH/src/main/java:"
tree "$PACKAGE_PATH/src/main/java"

# 遍历包路径下的所有 Java 文件
find "$PACKAGE_PATH/src/main/java" -name "*.java" | while read -r java_file; do
    # 获取文件名
    filename=$(basename "$java_file")
    
    # 写入文件名
    echo -e "\n$filename"
    
    # 写入代码块开始标记
    echo '```java'
    
    # 写入文件内容
    cat "$java_file"
    
    # 写入代码块结束标记
    echo '```'
done