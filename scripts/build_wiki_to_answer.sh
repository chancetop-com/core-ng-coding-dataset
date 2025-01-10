#!/bin/bash
# @author stephen

urls=(
    "https://wonder.atlassian.net/wiki/spaces/T/pages/360808487/CoreNg+Guide"
    "https://wonder.atlassian.net/wiki/spaces/T/pages/360808494/1.2+Getting+Started"
    "https://wonder.atlassian.net/wiki/spaces/T/pages/361136208/1.3+-+A+Basic+Web+Service+Module"
    "https://wonder.atlassian.net/wiki/spaces/T/pages/360972321/1.4+-+Using+Core-ng+Repositories"
    "https://wonder.atlassian.net/wiki/spaces/T/pages/361136228/1.5+-+Core-ng+Async"
    "https://wonder.atlassian.net/wiki/spaces/T/pages/2066677990/1.6+-+Running+Core-NG+projects+locally"
    "https://wonder.atlassian.net/wiki/spaces/T/pages/2537030081/1.7+-+API+Rate+Limiting")

tmp="../.out/tmp.md"

for url in "${urls[@]}"; do
    bash wiki2md.sh "$url" > $tmp
    answer=$(bash md2answer.sh $tmp)
    title=$(echo "$url" | awk -F'/pages/[0-9]+/' '{print $2}' | awk -F'/' '{print $1}')
    title="${title//+/ }"
    title="${title//%20/ }"
    query="CoreNG article: $title."
    echo "{\"messages\": [{\"role\": \"system\", \"content\": \"You are a code agent that help user write java code and typescript code with CoreNG/CoreFE framework.\"}, {\"role\": \"user\", \"content\": \"$query\"}, {\"role\": \"assistant\", \"content\": $answer}]}" >> ../train-wiki.jsonl
done