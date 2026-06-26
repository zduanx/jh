# ============================================================================
# Phase 9E: GitHub Actions OIDC → AWS (keyless CD auth)
# ============================================================================
# Lets the CD workflow assume an AWS role via a short-lived OIDC token instead
# of storing long-lived AWS access keys in GitHub Secrets.
#
#   1. aws_iam_openid_connect_provider — trust GitHub's token issuer
#   2. aws_iam_role (jh-github-actions-cd) — trust policy scoped to THIS repo's
#      main branch only; PRs and other repos cannot assume it
#   3. permissions policy — the AWS services `terraform apply` touches
#
# Bootstrap: this is created by a normal `jpushapi` (local terraform apply) ONCE,
# BEFORE CD can use it. After apply, `terraform output github_actions_role_arn`
# gives the ARN to reference in .github/workflows/deploy-*.yml.
# ============================================================================

data "aws_caller_identity" "current" {}

# --- 1. Trust GitHub's OIDC token issuer -----------------------------------
# One provider per AWS account. If GitHub Actions OIDC is already configured in
# this account, import it instead of creating a duplicate.
resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # GitHub's OIDC cert thumbprint. AWS now validates via a trusted CA, but the
  # provider still requires this field; this is GitHub's well-known thumbprint.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = {
    Project = "jh"
    Purpose = "github-actions-cd"
  }
}

# --- 2. The role CD assumes, scoped to THIS repo's main branch --------------
resource "aws_iam_role" "github_actions_cd" {
  name = "jh-github-actions-cd"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          # audience must be the AWS STS audience
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # ONLY the main branch of zduanx/jh — not PRs, not other repos/branches
          "token.actions.githubusercontent.com:sub" = "repo:zduanx/jh:ref:refs/heads/main"
        }
      }
    }]
  })

  tags = {
    Project = "jh"
    Purpose = "github-actions-cd"
  }
}

# --- 3. Permissions: what `terraform apply` needs ---------------------------
# Scoped to the service families this stack manages (Lambda, S3, IAM, API
# Gateway, SQS, CloudWatch Logs) + the Terraform state bucket. Not full admin,
# but broad within these services (resource-level least-privilege is a later
# hardening pass — see ADR-036 / Phase 10).
resource "aws_iam_role_policy" "github_actions_cd" {
  name = "jh-cd-permissions"
  role = aws_iam_role.github_actions_cd.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "DeployServices"
        Effect = "Allow"
        Action = [
          "lambda:*",
          "s3:*",
          "apigateway:*",
          "sqs:*",
          "logs:*",
          # IAM: both stacks' terraform MANAGES roles (backend's 4 Lambda roles,
          # chat's role + policy attachment), so CD needs create/update/delete, not
          # just read. (Resource-level scoping to jh-* roles is a later hardening pass.)
          "iam:GetRole",
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:UpdateRole",
          "iam:PassRole",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:ListRolePolicies",
          "iam:GetRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:ListAttachedRolePolicies",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:ListInstanceProfilesForRole",
        ]
        Resource = "*"
      },
      {
        # Terraform remote state: read/write the state object + lock
        Sid    = "TerraformState"
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket", "s3:DeleteObject"]
        Resource = [
          "arn:aws:s3:::jh-terraform-state-${data.aws_caller_identity.current.account_id}",
          "arn:aws:s3:::jh-terraform-state-${data.aws_caller_identity.current.account_id}/*",
        ]
      },
    ]
  })
}

# --- Output the role ARN for the CD workflow --------------------------------
output "github_actions_role_arn" {
  description = "ARN of the OIDC role for GitHub Actions CD (use in deploy-*.yml role-to-assume)"
  value       = aws_iam_role.github_actions_cd.arn
}
