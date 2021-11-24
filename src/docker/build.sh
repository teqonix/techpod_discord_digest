#!/bin/zsh 

set -e

docker buildx build \
--platform linux/amd64 \
-t us-central1-docker.pkg.dev/techpod-discord-digest/gcp-console-artifact-repo-01/techpod_digest_bot:latest \
-f ./Dockerfile ../.