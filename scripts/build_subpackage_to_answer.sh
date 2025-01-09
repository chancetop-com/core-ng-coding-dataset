#!/bin/bash
# @author stephen

packages=(
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/async"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/cache"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/crypto"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/db"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/http"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/inject"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/json"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/kafka"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/log"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/module"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/redis"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/scheduler"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/template"
    "/mnt/d/wonder-core-ng-project/core-ng/src/main/java/core/framework/web")

project_path="/mnt/d/wonder-core-ng-project"

tmp="../.out/tmp.md"

for package in "${packages[@]}"; do
    bash subpackage2md.sh $project_path $package > $tmp
    answer=$(bash md2answer.sh $tmp)
    package_name=$(basename $(echo $package | awk -F'/src/main/java' '{print $1}'))
    sub_package_name=$(basename $package)
    query="The source code of $package_name package $sub_package_name."
    echo "{\"messages\": [{\"role\": \"system\", \"content\": \"You are a code agent that help user write java code and typescript code with CoreNG/CoreFE framework.\"}, {\"role\": \"user\", \"content\": \"$query\"}, {\"role\": \"assistant\", \"content\": $answer}]}" >> ../train.jsonl
done