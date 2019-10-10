#!/usr/bin/env bash

set -euo pipefail

REPO=materialize/mcli
NOW=$(date +%Y-%m-%d)

usage() {
    echo "usage: $0 [-p|-n] [--push|--no-push]"
    exit 0
}

main() {
    local push=$1 && shift
    case $push in
        -p|--push) response=Y ;;
        -n|--no-push) response=N ;;
        -h|--help) usage ;;
        *) read -r -p "Run docker push [y/N] " response
    esac

    build
    if [[ ${response^^} =~ Y.* ]] ; then
        push
    else
        echo "Skipping docker push"
    fi
    echo "finished"
}

build() {
    run docker build -t "${REPO}:latest" -t "${REPO}:${NOW}" .
}

push() {
    for tag in latest "$NOW"; do
        run docker push "${REPO}:${tag}"
    done
}

run() {
    echo "$ $*"
    "$@"
}

main "$@"
