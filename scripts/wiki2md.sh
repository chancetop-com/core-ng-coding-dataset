#!/bin/bash
# @author stephen


check_dependency() {
  if ! command -v "$1" &> /dev/null; then
    echo "Error: $1 is not installed. Please install it and try again."
    exit 1
  fi
}

check_dependency "jq"
check_dependency "pandoc"


if [ -z "$1" ]; then
    echo "Usage: $0 <page_url>"
    exit 1
fi

CONFLUENCE_URL=$1
BASE_URL=$(echo "$CONFLUENCE_URL" | grep -oP '^https://[^/]+/wiki')
API_TOKEN=$CONFLUENCE_API_TOKEN

if [ -z "$API_TOKEN" ]; then
    echo "Need CONFLUENCE_API_TOKEN env"
    exit 1
fi

PAGE_ID=$(echo "$CONFLUENCE_URL" | grep -oP '(?<=/pages/)[0-9]+')
if [ -z "$PAGE_ID" ]; then
  echo "Failed to extract PAGE_ID from the URL."
  exit 1
fi

JSON_RESPONSE=$(curl -s -u "$API_TOKEN" -X GET "$BASE_URL/rest/api/content/$PAGE_ID?expand=body.storage" -H "Accept: application/json")
HTML_CONTENT=$(echo "$JSON_RESPONSE" | jq -r '.body.storage.value')
# TITLE=$(echo "$JSON_RESPONSE" | jq -r '.title')

if [ -z "$HTML_CONTENT" ]; then
  echo "Failed to fetch content. Please check your credentials or page ID."
  exit 1
fi

echo "$HTML_CONTENT" | pandoc -f html -t markdown