#!/bin/zsh 

set -e

docker buildx build --platform linux/amd64,linux/arm64 -t techpod_digest_bot:latest -f ./Dockerfile ../.
docker run --env-file ./debug_vars.env techpod_digest_bot:latest