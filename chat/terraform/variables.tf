# Secret variables for the chat stack (Phase 9A / 9E).
# Values are NEVER hardcoded here — they come from the environment as TF_VAR_<name>:
#   - locally:  a dev.sh helper exports TF_VAR_* from the root .env.local (9E)
#   - in CI/CD: GitHub Actions sets TF_VAR_* from GitHub Secrets (9D)
# `sensitive = true` redacts them in plan/apply output so they never print to logs.

variable "secret_key" {
  type      = string
  sensitive = true
}

variable "anthropic_api_key" {
  type      = string
  sensitive = true
}

variable "mcp_service_token" {
  type      = string
  sensitive = true
}

variable "mcp_server_url" {
  type = string
}

variable "upstash_redis_rest_url" {
  type = string
}

variable "upstash_redis_rest_token" {
  type      = string
  sensitive = true
}
