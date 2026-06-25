# Chat stack resources (Phase 9A) — cleaned from the import-generated draft.
# Secrets are var.* references (see variables.tf); code is packaged via archive_file.

# --- Package the chat Node code into a deploy zip (replaces `sam build`) ---
data "archive_file" "chat" {
  type        = "zip"
  source_dir  = "${path.module}/.."
  output_path = "${path.module}/.build/chat.zip"
  excludes = [
    ".aws-sam", "node_modules/.cache", "__tests__",
    ".env.local", ".env", "samconfig.toml", "*.test.js",
  ]
}

# --- IAM execution role ---
resource "aws_iam_role" "chat" {
  name = "jh-chat-stack-ChatFunctionRole-IHBj3C1O8SrM"
  path = "/"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = { "lambda:createdBy" = "SAM" }
}

resource "aws_iam_role_policy_attachment" "chat_basic" {
  role       = aws_iam_role.chat.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- The chat Lambda ---
resource "aws_lambda_function" "chat" {
  function_name = "JobHuntChat"
  description   = "Streaming chat service (Node.js) for Job Hunt Tracker"
  role          = aws_iam_role.chat.arn
  handler       = "handler.handler"
  runtime       = "nodejs22.x"
  architectures = ["x86_64"]
  memory_size   = 256
  timeout       = 300

  filename         = data.archive_file.chat.output_path
  source_code_hash = data.archive_file.chat.output_base64sha256

  environment {
    variables = {
      ALGORITHM                = "HS256"
      SECRET_KEY               = var.secret_key
      ANTHROPIC_API_KEY        = var.anthropic_api_key
      MCP_SERVER_URL           = var.mcp_server_url
      MCP_SERVICE_TOKEN        = var.mcp_service_token
      UPSTASH_REDIS_REST_URL   = var.upstash_redis_rest_url
      UPSTASH_REDIS_REST_TOKEN = var.upstash_redis_rest_token
    }
  }

  tags = { "lambda:createdBy" = "SAM" }
}

# --- Function URL (streaming) ---
resource "aws_lambda_function_url" "chat" {
  function_name      = aws_lambda_function.chat.function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"

  cors {
    allow_credentials = false
    allow_headers     = ["*"]
    allow_methods     = ["GET", "POST"]
    allow_origins     = ["http://localhost:3000", "https://zduan-job.vercel.app"]
    expose_headers    = []
    max_age           = 0
  }
}

# --- Public-access permissions for the Function URL ---
resource "aws_lambda_permission" "chat_url_public" {
  statement_id           = "jh-chat-stack-ChatFunctionUrlPublicPermissions-ysIacygRNZHo"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.chat.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "chat_url_invoke" {
  statement_id  = "jh-chat-stack-ChatFunctionURLInvokeAllowPublicAccess-ztYWTfAeWf2i"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.chat.function_name
  principal     = "*"
}

output "chat_function_url" {
  value = aws_lambda_function_url.chat.function_url
}
