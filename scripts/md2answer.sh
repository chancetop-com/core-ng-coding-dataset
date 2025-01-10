#!/bin/bash
# @author stephen

# caution: pipe the output to a file, not copy from the console

if [ -z "$1" ]; then
  echo "Usage: $0 <markdown-file>"
  exit 1
fi

if [ ! -f "$1" ]; then
  echo "File not found!"
  exit 1
fi

java_string=$(awk '{
  # 首先将反斜杠替换为双反斜杠
  gsub(/\\/, "\\\\");
  # 然后将双引号替换为转义的双引号
  gsub(/"/, "\\\"");
  # 将换行符替换为转义的换行符
  gsub(/\n/, "\\n");
  # 将回车符替换为转义的回车符
  gsub(/\r/, "\\r");
  # 将制表符替换为转义的制表符
  gsub(/\t/, "\\t");
  # 将每一行用双引号包裹，并在行尾添加换行符（除了最后一行）
  if (NR > 1) printf "\\n";
  printf "%s", $0;
}' "$1")

echo -n "\"$java_string\""