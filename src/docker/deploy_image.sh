#!/bin/zsh

set -e

gcloud auth print-access-token | \
  docker login \
  -u oauth2accesstoken \
  --password-stdin https://us-central1-docker.pkg.dev

docker tag techpod_digest_bot:latest us-central1-docker.pkg.dev/techpod-discord-digest/gcp-console-artifact-repo-01/techpod_digest_bot:latest

docker push us-central1-docker.pkg.dev/techpod-discord-digest/gcp-console-artifact-repo-01/techpod_digest_bot:latest