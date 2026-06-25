# The 5 backend Lambdas (Phase 9A) — via the terraform-aws-lambda module.
#
# BUILD ONCE, DEPLOY 5×: all 5 Lambdas share the same backend/ code (only the handler
# differs), so a single `builder` module builds the package ONCE (Docker pip-install),
# and the 5 function modules reuse it (create_package=false + local_existing_package).
# This is ~5× faster + ~1/5 the CPU vs. each module building independently (which pegged
# the CPU with 5 parallel pip installs). It mirrors `sam build`'s single-build behavior.
#
# create_role=false reuses the imported IAM roles (infra.tf);
# use_existing_cloudwatch_log_group=true adopts the log groups SAM created.
# The migration imported the raw functions; `terraform state mv` moved them into these
# module addresses so adoption is preserved (no recreation).
#
# NOTE on redeploys: the Docker build isn't byte-reproducible, so each `terraform apply`
# produces a new package hash and redeploys (even if code is unchanged). We accept this
# rather than ignore_source_code_hash — in CD (9D) every apply runs on a merge, so we WANT
# the merged code deployed; ignoring the hash would risk CD skipping a real change.

locals {
  # source_path: build from backend/, pip-install requirements.txt (pip_requirements
  # TRIGGERS the install), then filter dev/test/eval/SAM cruft with patterns.
  backend_source_path = [{
    path             = "${path.module}/.."
    pip_requirements = "${path.module}/../requirements.txt"
    patterns = [
      "!terraform/.*",  # the co-located terraform/ dir (incl. .terraform/ provider bins + builds/)
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

  # Build x86_64 binaries (our Lambda arch) even on an ARM Mac.
  docker_amd64 = ["--platform", "linux/amd64"]
}

# --- The single builder: builds the package ONCE (no function created) ---
module "builder" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  create_function = false # build only, deploy nothing
  runtime         = "python3.13"

  source_path               = local.backend_source_path
  build_in_docker           = true
  docker_additional_options = local.docker_amd64

  # Stage the >50MB package in S3 (direct upload caps at 50MB → 413).
  store_on_s3 = true
  s3_bucket   = "jh-terraform-state-400778305315"
  s3_prefix   = "lambda-builds/"
}

# Shared args for all 5 function modules: reuse the builder's package (no rebuild,
# no re-upload). The builder already uploaded the zip to S3 (store_on_s3); each function
# references that SAME S3 object via s3_existing_package — so they deploy from the one
# uploaded package, not their own builds/uploads.
locals {
  fn_common = {
    runtime       = "python3.13"
    architectures = ["x86_64"]
    create_role   = false
    create_package      = false                  # don't build
    s3_existing_package = module.builder.s3_object # deploy the builder's uploaded zip
    use_existing_cloudwatch_log_group       = true
    create_current_version_allowed_triggers = false
  }
}

module "api" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "JobHuntTrackerAPI"
  description   = "FastAPI backend for Job Hunt Tracker"
  handler       = "main.handler"
  memory_size   = 512
  timeout       = 30
  lambda_role   = aws_iam_role.api.arn

  runtime                                 = local.fn_common.runtime
  architectures                           = local.fn_common.architectures
  create_role                             = local.fn_common.create_role
  create_package                          = local.fn_common.create_package
  s3_existing_package                     = local.fn_common.s3_existing_package
  use_existing_cloudwatch_log_group       = local.fn_common.use_existing_cloudwatch_log_group
  create_current_version_allowed_triggers = local.fn_common.create_current_version_allowed_triggers

  environment_variables = merge(local.common_env, {
    RESUME_CONTENT_BUCKET = local.resume_bucket
    WORKER_FUNCTION_NAME  = "IngestionWorker"
  })
  tags = { "lambda:createdBy" = "terraform" }
}

module "ingestion" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "IngestionWorker"
  description   = "Async worker for job ingestion (15 min timeout)"
  handler       = "workers.ingestion_worker.handler"
  memory_size   = 512
  timeout       = 900
  lambda_role   = aws_iam_role.ingestion.arn

  runtime                                 = local.fn_common.runtime
  architectures                           = local.fn_common.architectures
  create_role                             = local.fn_common.create_role
  create_package                          = local.fn_common.create_package
  s3_existing_package                     = local.fn_common.s3_existing_package
  use_existing_cloudwatch_log_group       = local.fn_common.use_existing_cloudwatch_log_group
  create_current_version_allowed_triggers = local.fn_common.create_current_version_allowed_triggers

  environment_variables = merge(local.common_env, {
    CRAWLER_QUEUE_URL = local.crawler_queue_url
  })
  tags = { "lambda:createdBy" = "terraform" }
}

module "crawler" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "CrawlerWorker"
  description   = "SQS-triggered crawler worker"
  handler       = "workers.crawler_worker.handler"
  memory_size   = 512
  timeout       = 60
  lambda_role   = aws_iam_role.crawler.arn

  runtime                                 = local.fn_common.runtime
  architectures                           = local.fn_common.architectures
  create_role                             = local.fn_common.create_role
  create_package                          = local.fn_common.create_package
  s3_existing_package                     = local.fn_common.s3_existing_package
  use_existing_cloudwatch_log_group       = local.fn_common.use_existing_cloudwatch_log_group
  create_current_version_allowed_triggers = local.fn_common.create_current_version_allowed_triggers

  environment_variables = merge(local.common_env, {
    EXTRACTOR_QUEUE_URL = local.extractor_queue_url
    RAW_CONTENT_BUCKET  = local.raw_bucket
  })
  tags = { "lambda:createdBy" = "terraform" }
}

module "extractor" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name                  = "ExtractorWorker"
  description                    = "SQS-triggered extractor worker"
  handler                        = "workers.extractor_worker.handler"
  memory_size                    = 256
  timeout                        = 30
  reserved_concurrent_executions = 5
  lambda_role                    = aws_iam_role.extractor.arn

  runtime                                 = local.fn_common.runtime
  architectures                           = local.fn_common.architectures
  create_role                             = local.fn_common.create_role
  create_package                          = local.fn_common.create_package
  s3_existing_package                     = local.fn_common.s3_existing_package
  use_existing_cloudwatch_log_group       = local.fn_common.use_existing_cloudwatch_log_group
  create_current_version_allowed_triggers = local.fn_common.create_current_version_allowed_triggers

  environment_variables = merge(local.common_env, {
    RAW_CONTENT_BUCKET = local.raw_bucket
  })
  tags = { "lambda:createdBy" = "terraform" }
}

module "mcp" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 7.0"

  function_name = "McpServer"
  description   = "MCP server (FastMCP over HTTP) exposing job/resume tools"
  handler       = "mcp_server.handler.handler"
  memory_size   = 512
  timeout       = 60
  lambda_role   = aws_iam_role.mcp.arn

  runtime                                 = local.fn_common.runtime
  architectures                           = local.fn_common.architectures
  create_role                             = local.fn_common.create_role
  create_package                          = local.fn_common.create_package
  s3_existing_package                     = local.fn_common.s3_existing_package
  use_existing_cloudwatch_log_group       = local.fn_common.use_existing_cloudwatch_log_group
  create_current_version_allowed_triggers = local.fn_common.create_current_version_allowed_triggers

  environment_variables = local.common_env
  tags                  = { "lambda:createdBy" = "terraform" }
}
