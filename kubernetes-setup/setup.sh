#!/bin/zsh

# TODO: Invoke this via Terraform to set up cluster using Infra as Code

gcloud container clusters get-credentials techpod-discord-digest-dev-gke-cls-02 --region us-central1

gcloud iam service-accounts add-iam-policy-binding techpod-discord-digest-dev-run@techpod-discord-digest.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:techpod-discord-digest.svc.id.goog[default/default]"

kubectl annotate serviceaccount default \
    --namespace default \
    iam.gke.io/gcp-service-account=techpod-discord-digest-dev-run@techpod-discord-digest.iam.gserviceaccount.com

# DEBUG interactive container deployment to see if workload identity is working in GKE for k8s service account --> IAM translation
# kubectl exec -it workload-identity-test \
#     --namespace default -- /bin/bash
