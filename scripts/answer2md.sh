#!/bin/bash
# @author stephen

if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 <input-jsonl-file> <line-number>"
  exit 1
fi

INPUT_FILE="$1"
LINE_NUMBER="$2"

if [ ! -f "$INPUT_FILE" ]; then
  echo "Input file not found!"
  exit 1
fi

if ! [[ "$LINE_NUMBER" =~ ^[0-9]+$ ]] || [ "$LINE_NUMBER" -le 0 ]; then
  echo "Invalid line number!"
  exit 1
fi

java_string=$(sed -n "${LINE_NUMBER}p" "$INPUT_FILE" | jq -r '.messages[2].content')

if [ -z "$java_string" ] || [ "$java_string" == "null" ]; then
  echo "Failed to extract content or content is null at specified line."
  exit 1
fi

java_string="${java_string#\"}"
java_string="${java_string%\"}"

markdown_content=$(echo "$java_string" | sed 's/\\n/\n/g' | sed 's/\\"/"/g')

echo "$markdown_content"