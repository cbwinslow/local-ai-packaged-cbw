variable "dns_provider" {
  description = "cloudflare or hetzner"
  type        = string
  default     = "cloudflare"
}

variable "zone" {
  description = "DNS zone (e.g., opendiscourse.net)"
  type        = string
}

variable "ipv4" {
  description = "Public IPv4 of your dedicated server"
  type        = string
}

variable "subdomains" {
  description = "List of subdomains to create (A records)"
  type        = list(string)
  default     = ["traefik","whoami","prometheus","grafana"]
}

# Cloudflare auth
variable "cloudflare_api_token" {
  type        = string
  default     = null
  sensitive   = true
}

# Hetzner DNS auth
variable "hetzner_dns_token" {
  type        = string
  default     = null
  sensitive   = true
}
