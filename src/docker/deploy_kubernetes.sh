#!/bin/zsh

set -e

gcloud container clusters get-credentials --region us-central1 autopilot-cluster-1
kubectl create deployment discord-digest-server \
    --image=us-central1-docker.pkg.dev/techpod-discord-digest/gcp-console-artifact-repo-01/techpod_digest_bot:latest