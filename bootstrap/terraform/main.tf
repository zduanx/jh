# ============================================================================
# Bootstrap / repo-level shared infrastructure (Phase 9E)
# ============================================================================
# Resources that belong to the REPO, not to any single app stack — currently the
# GitHub Actions OIDC provider + CD role (see oidc.tf). Kept in its own Terraform
# state (key=bootstrap/) so backend/ and chat/ each own only their app resources,
# and the shared CD auth isn't entangled with either app's lifecycle.
#
# Apply with: jpushbootstrap  (a one-time / rarely-changing deploy)
# ============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  backend "s3" {
    bucket       = "jh-terraform-state-400778305315"
    key          = "bootstrap/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = "us-east-1"
}
