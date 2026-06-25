# Terraform configuration for the CHAT stack (Phase 9A migration).
#
# This stack was originally deployed via SAM (jh-chat-stack). 9A migrates it to
# Terraform by IMPORTING the existing live resources (see imports.tf) so Terraform
# adopts them in-place with zero recreation. The resource .tf below is generated
# from the live state via `terraform plan -generate-config-out=` and then cleaned.
#
# Resources (5, from `aws cloudformation list-stack-resources --stack-name jh-chat-stack`):
#   ChatFunction              AWS::Lambda::Function    (JobHuntChat)
#   ChatFunctionRole          AWS::IAM::Role
#   ChatFunctionUrl           AWS::Lambda::Url
#   ChatFunctionURLInvoke...  AWS::Lambda::Permission  (public access)
#   ChatFunctionUrlPublic...  AWS::Lambda::Permission

terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state in S3 (shared with CI for 9D CD; state has secrets so NEVER in git).
  # use_lockfile = native S3 state locking (replaces the deprecated DynamoDB lock table).
  backend "s3" {
    bucket       = "jh-terraform-state-400778305315"
    key          = "chat/terraform.tfstate"
    region       = "us-east-1"
    use_lockfile = true
    encrypt      = true
  }
}

provider "aws" {
  region = "us-east-1"
}
