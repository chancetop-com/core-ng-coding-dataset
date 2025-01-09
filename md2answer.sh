#!/bin/bash
# @author stephen

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
} END {
  if (NR > 0) printf "\\n";
}' "$1")

echo "\"$java_string\""