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
      version = "3.5.0"
    }
  }
}

variable "environment" {
    type = string
    default = "dev"
}

variable "gcp_project" {
    type = string
}

variable "gcp_region" {
    type = string
}

variable "gcp_zone" {
    type = string
    default = "a"
}

provider "google" {
  credentials = file("../secret_store/techpod-discord-digest-9d2a57588530.json")

  project = var.gcp_project
  region  = var.gcp_region
  zone    = "${var.gcp_region}-${var.gcp_zone}"
}

resource "google_compute_network" "vpc_network" {
  name = "terraform-network"
}

resource "google_container_registry" "registry" {
  location = "US"
}