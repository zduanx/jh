# The 5 backend Lambdas (Phase 9A) — via the terraform-aws-lambda module.
#
# The module does what `sam build` does: reads requirements.txt, pip-installs the
# deps in Docker (correct Linux x86_64 wheels for numpy/cryptography/psycopg2),
# packages, and deploys. Idiomatic Terraform (use the community module, don't
# hand-roll archive_file). create_role=false reuses our imported IAM roles (infra.tf);
# use_existing_cloudwatch_log_group=true adopts the log groups SAM already created.
#
# All 5 share backend/ as source, differing by handler + env. The migration imported
# the raw functions; `terraform state mv` moved them into these module addresses so
# adoption is preserved (no recreation).
#
# NOTE on redeploys: the Docker build isn't byte-reproducible, so each `terraform apply`
# produces a new package hash and redeploys the code (even if unchanged). We accept this
# rather than ignore_source_code_hash, because in CD (9D) every apply runs on a merge —
# we WANT it to deploy the merged code, and ignoring the hash would risk CD skipping a
# real code change. The only cost is a redundant ~78MB re-upload on a no-op local run.

locals {
  # source_path: build from backend/, pip-install requirements.txt (the
  # pip_requirements key is what TRIGGERS the install — without it the module
  # packages source only, no deps), then filter cruft with patterns.
  backend_source_path = [{
    path             = "${path.module}/.."
    pip_requirements = "${path.module}/../requirements.txt"
    patterns = [
      "!\\.aws-sam/.*",
      "!venv/.*",
      "!.*/__pycache__/.*",
      "!.*\\.pyc$",
      "!\\.mypy_cache/.*",
      "!\\.pytest_cache/.*",
      "!.*/__tests__/.*",
      "!\\.env.*",
      "!samconfig.*",
      "!template\\.yaml",
      "!.*\\.log",
      "!extractors_v2/.*",
      "!scripts/.*",
      "!jh\\.egg-info/.*",
      "!lambda/.*",
      "!extractor_agent/.*",
      "!trials/.*",
    ]
  }]

  # Build x86_64 binaries (our Lambda arch) even on an ARM Mac — without this the
  # Docker build produces ARM wheels that crash on x86_64 Lambda.
  docker_amd64 = ["--platform", "linux/amd64"]
}

module "api" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "JobHuntTrackerAPI"
  description   = "FastAPI backend for Job Hunt Tracker"
  handler       = "main.handler"
  runtime       = "python3.13"
  architectures = ["x86_64"]
  memory_size   = 512
  timeout       = 30

  create_role = false
  lambda_role = aws_iam_role.api.arn

  source_path               = local.backend_source_path
  build_in_docker           = true
  docker_additional_options = local.docker_amd64
  use_existing_cloudwatch_log_group = true

  # Package is >50MB (deps) → must upload via S3, not direct API (avoids 413).
  store_on_s3 = true
  s3_bucket   = "jh-terraform-state-400778305315"
  s3_prefix   = "lambda-builds/"


  # 9A STABILIZED: infra is fully managed by Terraform, but code deploy via the
  # module hit a >50MB-upload edge case mid-session. ignore_source_code_hash keeps
  # apply from redeploying code (prod runs the known-good package) until the code-
  # deploy path is finished + verified. Flip to false to resume Terraform code deploys.
  

  environment_variables = merge(local.common_env, {
    RESUME_CONTENT_BUCKET = local.resume_bucket
    WORKER_FUNCTION_NAME  = "IngestionWorker"
  })

  create_current_version_allowed_triggers = false
  tags = { "lambda:createdBy" = "terraform" }
}

module "ingestion" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "IngestionWorker"
  description   = "Async worker for job ingestion (15 min timeout)"
  handler       = "workers.ingestion_worker.handler"
  runtime       = "python3.13"
  architectures = ["x86_64"]
  memory_size   = 512
  timeout       = 900

  create_role = false
  lambda_role = aws_iam_role.ingestion.arn

  source_path               = local.backend_source_path
  build_in_docker           = true
  docker_additional_options = local.docker_amd64
  use_existing_cloudwatch_log_group = true

  # Package is >50MB (deps) → must upload via S3, not direct API (avoids 413).
  store_on_s3 = true
  s3_bucket   = "jh-terraform-state-400778305315"
  s3_prefix   = "lambda-builds/"


  # 9A STABILIZED: infra is fully managed by Terraform, but code deploy via the
  # module hit a >50MB-upload edge case mid-session. ignore_source_code_hash keeps
  # apply from redeploying code (prod runs the known-good package) until the code-
  # deploy path is finished + verified. Flip to false to resume Terraform code deploys.
  

  environment_variables = merge(local.common_env, {
    CRAWLER_QUEUE_URL = local.crawler_queue_url
  })

  create_current_version_allowed_triggers = false
  tags = { "lambda:createdBy" = "terraform" }
}

module "crawler" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "CrawlerWorker"
  description   = "SQS-triggered crawler worker"
  handler       = "workers.crawler_worker.handler"
  runtime       = "python3.13"
  architectures = ["x86_64"]
  memory_size   = 512
  timeout       = 60

  create_role = false
  lambda_role = aws_iam_role.crawler.arn

  source_path               = local.backend_source_path
  build_in_docker           = true
  docker_additional_options = local.docker_amd64
  use_existing_cloudwatch_log_group = true

  # Package is >50MB (deps) → must upload via S3, not direct API (avoids 413).
  store_on_s3 = true
  s3_bucket   = "jh-terraform-state-400778305315"
  s3_prefix   = "lambda-builds/"


  # 9A STABILIZED: infra is fully managed by Terraform, but code deploy via the
  # module hit a >50MB-upload edge case mid-session. ignore_source_code_hash keeps
  # apply from redeploying code (prod runs the known-good package) until the code-
  # deploy path is finished + verified. Flip to false to resume Terraform code deploys.
  

  environment_variables = merge(local.common_env, {
    EXTRACTOR_QUEUE_URL = local.extractor_queue_url
    RAW_CONTENT_BUCKET  = local.raw_bucket
  })

  create_current_version_allowed_triggers = false
  tags = { "lambda:createdBy" = "terraform" }
}

module "extractor" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name                  = "ExtractorWorker"
  description                    = "SQS-triggered extractor worker"
  handler                        = "workers.extractor_worker.handler"
  runtime                        = "python3.13"
  architectures                  = ["x86_64"]
  memory_size                    = 256
  timeout                        = 30
  reserved_concurrent_executions = 5

  create_role = false
  lambda_role = aws_iam_role.extractor.arn

  source_path               = local.backend_source_path
  build_in_docker           = true
  docker_additional_options = local.docker_amd64
  use_existing_cloudwatch_log_group = true

  # Package is >50MB (deps) → must upload via S3, not direct API (avoids 413).
  store_on_s3 = true
  s3_bucket   = "jh-terraform-state-400778305315"
  s3_prefix   = "lambda-builds/"


  # 9A STABILIZED: infra is fully managed by Terraform, but code deploy via the
  # module hit a >50MB-upload edge case mid-session. ignore_source_code_hash keeps
  # apply from redeploying code (prod runs the known-good package) until the code-
  # deploy path is finished + verified. Flip to false to resume Terraform code deploys.
  

  environment_variables = merge(local.common_env, {
    RAW_CONTENT_BUCKET = local.raw_bucket
  })

  create_current_version_allowed_triggers = false
  tags = { "lambda:createdBy" = "terraform" }
}

module "mcp" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "McpServer"
  description   = "MCP server (FastMCP over HTTP) exposing job/resume tools"
  handler       = "mcp_server.handler.handler"
  runtime       = "python3.13"
  architectures = ["x86_64"]
  memory_size   = 512
  timeout       = 60

  create_role = false
  lambda_role = aws_iam_role.mcp.arn

  source_path               = local.backend_source_path
  build_in_docker           = true
  docker_additional_options = local.docker_amd64
  use_existing_cloudwatch_log_group = true

  # Package is >50MB (deps) → must upload via S3, not direct API (avoids 413).
  store_on_s3 = true
  s3_bucket   = "jh-terraform-state-400778305315"
  s3_prefix   = "lambda-builds/"


  # 9A STABILIZED: infra is fully managed by Terraform, but code deploy via the
  # module hit a >50MB-upload edge case mid-session. ignore_source_code_hash keeps
  # apply from redeploying code (prod runs the known-good package) until the code-
  # deploy path is finished + verified. Flip to false to resume Terraform code deploys.
  

  environment_variables = local.common_env

  create_current_version_allowed_triggers = false
  tags = { "lambda:createdBy" = "terraform" }
}
