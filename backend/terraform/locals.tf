# Shared values for the backend stack (Phase 9A).

locals {
  account_id = "400778305315"
  region     = "us-east-1"

  # Env vars common to ALL backend Lambdas (the auth/db/secret baseline).
  # Per-Lambda extras (queue URLs, bucket names) are merged in per resource.
  common_env = {
    ACCESS_TOKEN_EXPIRE_MINUTES = "1440"
    ALGORITHM                   = "HS256"
    ALLOWED_EMAILS              = var.allowed_emails
    ALLOWED_ORIGINS             = var.allowed_origins
    DATABASE_URL                = var.database_url
    TEST_DATABASE_URL           = var.test_database_url
    GOOGLE_CLIENT_ID            = var.google_client_id
    GOOGLE_CLIENT_SECRET        = var.google_client_secret
    MCP_SERVICE_TOKEN           = var.mcp_service_token
    SECRET_KEY                  = var.secret_key
    VOYAGE_API_KEY              = var.voyage_api_key
  }

  crawler_queue_url   = "https://sqs.us-east-1.amazonaws.com/${local.account_id}/CrawlerQueue.fifo"
  extractor_queue_url = "https://sqs.us-east-1.amazonaws.com/${local.account_id}/ExtractorQueue"
  raw_bucket          = "jobhunt-raw-content-${local.account_id}"
  resume_bucket       = "jobhunt-resume-content-${local.account_id}"
}

# Lambda packaging is handled by the terraform-aws-lambda module (lambdas.tf):
# it reads requirements.txt, pip-installs in Docker (correct Linux wheels), and deploys.
# No hand-rolled archive_file / build script needed — the module does what `sam build` did.
