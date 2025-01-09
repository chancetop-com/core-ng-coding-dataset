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
  gsub(/"/, "\\\"");
  gsub(/\r/, "");
  if (NR > 1) printf "\\n";
  printf "%s", $0;
}' "$1")

echo -n "\"$java_string\""