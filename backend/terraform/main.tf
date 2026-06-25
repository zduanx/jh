# Terraform configuration for the BACKEND stack (Phase 9A migration).
#
# Migrates jh-backend-stack (23 resources, originally SAM) to Terraform by importing
# the live resources in-place (see imports.tf). Same proven flow as the chat stack:
# import blocks → `terraform plan -generate-config-out` → clean (secrets→vars, code
# packaging) → verify plan shows 0 destroy/replace → apply.
#
# 23 resources: 5 Lambdas, 5 IAM roles, 2 SQS queues, 2 SQS event-source-mappings,
# 1 HTTP API + 1 stage, 4 Lambda permissions, 1 Lambda URL, 2 S3 buckets.

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }

  backend "s3" {
    bucket       = "jh-terraform-state-400778305315"
    key          = "backend/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = "us-east-1"
}
