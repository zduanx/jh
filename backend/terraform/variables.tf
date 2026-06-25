# Secret + config variables for the backend stack (Phase 9A / 9E).
# Values come from TF_VAR_<name> (local: dev.sh helper from root .env.local; CI: GitHub Secrets).
# sensitive=true redacts them in plan/apply output.

variable "database_url" {
  type      = string
  sensitive = true
}

variable "test_database_url" {
  type      = string
  sensitive = true
}

variable "secret_key" {
  type      = string
  sensitive = true
}

variable "google_client_id" {
  type = string
}

variable "google_client_secret" {
  type      = string
  sensitive = true
  default   = "optional-for-token-validation"
}

variable "mcp_service_token" {
  type      = string
  sensitive = true
}

variable "voyage_api_key" {
  type      = string
  sensitive = true
}

variable "allowed_emails" {
  type    = string
  default = "zduanx@gmail.com"
}

variable "allowed_origins" {
  type    = string
  default = "http://localhost:3000,https://zduan-job.vercel.app"
}
