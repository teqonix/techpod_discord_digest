#!/bin/bash 

# DEBUG - fyi gcloud is unavailable in docker image and needs to be added if debugging with it
# gcloud auth activate-service-account --key-file=/data/techpod_runner_sa_secret.json

python3 ./digest_bot/main.py