# Supporting backend resources (Phase 9A): IAM roles, SQS, S3, API Gateway,
# permissions, event-source mappings. All imported in-place.

# --- IAM roles (one per Lambda; assume-role for lambda.amazonaws.com) ---
locals {
  lambda_assume_role = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role" "api" {
  name               = "jh-backend-stack-JobHuntTrackerAPIRole-3l6gSkVjsXPw"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
  tags               = { "lambda:createdBy" = "SAM" }
}
resource "aws_iam_role" "ingestion" {
  name               = "jh-backend-stack-IngestionWorkerRole-fyH1NGsstYUi"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
  tags               = { "lambda:createdBy" = "SAM" }
}
resource "aws_iam_role" "crawler" {
  name               = "jh-backend-stack-CrawlerWorkerRole-Uz2p5IRd9TZ0"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
  tags               = { "lambda:createdBy" = "SAM" }
}
resource "aws_iam_role" "extractor" {
  name               = "jh-backend-stack-ExtractorWorkerRole-9ZOovvAAizGK"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
  tags               = { "lambda:createdBy" = "SAM" }
}
resource "aws_iam_role" "mcp" {
  name               = "jh-backend-stack-McpServerRole-I2zP6DH7tfzC"
  path               = "/"
  assume_role_policy = local.lambda_assume_role
  tags               = { "lambda:createdBy" = "SAM" }
}

# --- SQS queues ---
resource "aws_sqs_queue" "crawler" {
  name                        = "CrawlerQueue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  deduplication_scope         = "queue"
  fifo_throughput_limit       = "perQueue"
  message_retention_seconds   = 86400
  visibility_timeout_seconds  = 120
  sqs_managed_sse_enabled     = true
  # Live queue uses 1 MB (AWS max), but the provider validates max 256 KB —
  # so we can't declare it. Ignore it to adopt the live value unchanged.
  lifecycle { ignore_changes = [max_message_size] }
}

resource "aws_sqs_queue" "extractor" {
  name                       = "ExtractorQueue"
  message_retention_seconds  = 86400
  visibility_timeout_seconds = 60
  sqs_managed_sse_enabled    = true
  lifecycle { ignore_changes = [max_message_size] }
}

# --- SQS -> Lambda event source mappings (the triggers) ---
resource "aws_lambda_event_source_mapping" "crawler" {
  event_source_arn = aws_sqs_queue.crawler.arn
  function_name    = module.crawler.lambda_function_arn
  batch_size       = 1
  enabled          = true
}
resource "aws_lambda_event_source_mapping" "extractor" {
  event_source_arn = aws_sqs_queue.extractor.arn
  function_name    = module.extractor.lambda_function_arn
  batch_size       = 1
  enabled          = true
}

# --- S3 buckets ---
resource "aws_s3_bucket" "raw_content" {
  bucket = "jobhunt-raw-content-400778305315"
}
resource "aws_s3_bucket" "resume_content" {
  bucket = "jobhunt-resume-content-400778305315"
}

# --- HTTP API Gateway + stage ---
resource "aws_apigatewayv2_api" "http" {
  name          = "jh-backend-stack"
  protocol_type = "HTTP"
  version       = "1.0"

  cors_configuration {
    allow_credentials = true
    allow_headers     = ["*"]
    allow_methods     = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]
    allow_origins     = ["http://localhost:3000", "https://zduan-job.vercel.app"]
    expose_headers    = []
    max_age           = 0
  }

  tags = { "httpapi:createdBy" = "SAM" }
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "prod"
  auto_deploy = true
  tags        = { "httpapi:createdBy" = "SAM" }
}

# --- Lambda permissions ---
resource "aws_lambda_permission" "api_http_event" {
  statement_id  = "jh-backend-stack-JobHuntTrackerAPIHttpApiEventPermission-9DvSInGp51Mw"
  action        = "lambda:InvokeFunction"
  function_name = module.api.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:400778305315:${aws_apigatewayv2_api.http.id}/*/*/*"
}
resource "aws_lambda_permission" "api_root_event" {
  statement_id  = "jh-backend-stack-JobHuntTrackerAPIRootEventPermission-0FSJVdo8cNnS"
  action        = "lambda:InvokeFunction"
  function_name = module.api.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "arn:aws:execute-api:us-east-1:400778305315:${aws_apigatewayv2_api.http.id}/*/*/"
}
resource "aws_lambda_permission" "mcp_url_invoke" {
  statement_id  = "jh-backend-stack-McpServerURLInvokeAllowPublicAccess-uHmH0D2d76TY"
  action        = "lambda:InvokeFunction"
  function_name = module.mcp.lambda_function_name
  principal     = "*"
}
resource "aws_lambda_permission" "mcp_url_public" {
  statement_id           = "jh-backend-stack-McpServerUrlPublicPermissions-BUs597GtDM64"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = module.mcp.lambda_function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# --- MCP server Lambda URL ---
resource "aws_lambda_function_url" "mcp" {
  function_name      = module.mcp.lambda_function_name
  authorization_type = "NONE"
  invoke_mode        = "BUFFERED"
}

output "api_url" {
  value = "https://${aws_apigatewayv2_api.http.id}.execute-api.us-east-1.amazonaws.com/prod"
}
output "mcp_url" {
  value = aws_lambda_function_url.mcp.function_url
}
