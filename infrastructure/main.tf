# TODO:
# - Figure out GCP container approach for bot (K8s Engine?  GCE w/ Container Optimized OS?  Cloud Run?  App Engine?)
# - Add secrets for bot service account and Discord token
# - Set up networking for access to internets
# - Set up Firestore
# - Set up Artifact Registry and Digest Bot Image
# - Set up service accounts and IAM permissions:
#     * discord bot service account - Firestore / Secrets
#     * artifact repo service account - access to artifact registry for discord bot 
# - Probably lots more............

terraform {
  required_providers {
    google = {
      source = "hashicorp/google"
      version = "4.3.0"
    }
    google-beta = {
      source = "hashicorp/google-beta"
      version = "4.3.0"
    }
  }
}

provider "google" {
  credentials = file("../src/secret_store/techpod-discord-digest-53f499c735d6.json")
  project = var.gcp_project
  region  = var.gcp_region
  zone    = "${var.gcp_region}-${var.gcp_zone}"
}

provider "google-beta" {
  credentials = file("../src/secret_store/techpod-discord-digest-53f499c735d6.json")
  project = var.gcp_project
  region  = var.gcp_region
  zone    = "${var.gcp_region}-${var.gcp_zone}"
}
variable "environment" {
    type = string
    default = "dev"
}
variable "gcp_project" {
    type = string
    default = "techpod-discord-digest"
}
variable "gcp_region" {
    type = string
    default = "us-central1"
}
variable "gcp_zone" {
    type = string
    default = "a"
}
variable "gcp_admin" {
    type = string
    default = "teqonix@gmail.com"
}
variable "env" {
    type = string
    default = "dev"
}
resource "google_compute_network" "vpc_network" {
  name = "${var.env}-techpod-dicord-digest-network"
  auto_create_subnetworks = true
}

resource "google_container_registry" "registry" {
  location = "US"
}

resource "google_service_account" "sa_runner" {
  account_id   = "${var.env}-techpod-digest-bot-sa"
  display_name = "Service Account"
}

resource "google_project_iam_binding" "sa-service-account-user" {
  project = var.gcp_project
  role = "roles/iam.serviceAccountUser" 
  members = [
    "serviceAccount:${google_service_account.sa_runner.email}",
  ]
}

resource "google_project_iam_binding" "sa-artifact-registry-admin" {
  project = var.gcp_project
  role = "roles/artifactregistry.admin" 
  members = [
    "serviceAccount:${google_service_account.sa_runner.email}",
  ]
}

resource "google_project_iam_binding" "sa-datastore-user" {
  project = var.gcp_project
  role = "roles/datastore.user" 
  members = [
    "serviceAccount:${google_service_account.sa_runner.email}",
  ]
}

resource "google_project_iam_binding" "sa-k8s-developer" {
  project = var.gcp_project
  role = "roles/container.developer" 
  members = [
    "user:${var.gcp_admin}",
  ]
}

resource "google_project_iam_binding" "sa-secretsmanager-accessor" {
  project = var.gcp_project
  role    = "roles/secretmanager.secretAccessor"

  members = [
     "serviceAccount:${google_service_account.sa_runner.email}",
  ]
}

resource "google_project_iam_binding" "sa-secretsmanager-viewer" {
  project = var.gcp_project
  role = "roles/secretmanager.viewer" 
  members = [
    "serviceAccount:${google_service_account.sa_runner.email}",
  ]
}

resource "google_container_cluster" "techpod-discord-digest-k8s-cluster" {
  name     = "techpod-digest-bot-k8s-cluster-${var.env}"
  location = var.gcp_region
  network = google_compute_network.vpc_network.name
  enable_autopilot = true
}

resource "google_artifact_registry_repository" "digest-bot-docker-repo" {
  provider = google-beta

  location = var.gcp_region
  repository_id = "techpod-digest-docker-repo-${var.env}"
  description = "Docker repository for Techpod Discord Digest Bot Docker Images"
  format = "DOCKER"
}