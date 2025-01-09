#!/bin/bash
# @author stephen

DIR="/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/internal"

tmp="../.out/tmp.md"

find "$DIR" -name "*.java" | while read -r java_file; do
    bash class2md.sh $java_file > $tmp
    classname=$(basename $java_file)
    query="The source code of java class $classname."
    answer=$(bash md2answer.sh $tmp)
    echo "{\"messages\": [{\"role\": \"system\", \"content\": \"You are a code agent that help user write java code and typescript code with CoreNG/CoreFE framework.\"}, {\"role\": \"user\", \"content\": \"$query\"}, {\"role\": \"assistant\", \"content\": $answer}]}" >> ../train.jsonl
done