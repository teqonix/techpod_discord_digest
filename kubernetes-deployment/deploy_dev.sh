#!/bin/bash

# This is a real dumb hacky way to do this.  We need to fetch a GCP Secret and inject it into the k8s deployment
# but I can't find an easy way to inject this secret name into the deployment manifest programatically at runtime
# so.. Hardcoding it into a dev-specific manifest. :(
cp -f ./bot_client.deployment.dev.yaml ../kubernetes-manifests/bot_client.deployment.yaml