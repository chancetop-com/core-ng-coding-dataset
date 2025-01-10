#!/bin/bash
# @author stephen

packages=("/mnt/d/wonder-core-ng-project/core-ng-api" "/mnt/d/wonder-core-ng-project/core-ng-json" "/mnt/d/wonder-core-ng-project/core-ng-common")

tmp="../.out/tmp.md"

for package in "${packages[@]}"; do
    project_path=$(dirname $package)
    bash package2md.sh $project_path $package > $tmp
    answer=$(bash md2answer.sh $tmp)
    package_name=$(basename $package)
    query="The source code of package $package_name."
    echo "{\"messages\": [{\"role\": \"system\", \"content\": \"You are a code agent that help user write java code and typescript code with CoreNG/CoreFE framework.\"}, {\"role\": \"user\", \"content\": \"$query\"}, {\"role\": \"assistant\", \"content\": $answer}]}" > ../train-source-code.jsonl
done