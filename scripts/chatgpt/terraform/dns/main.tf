terraform {
  required_version = ">= 1.4"
  required_providers {
    cloudflare = { source = "cloudflare/cloudflare" }
    hetznerdns = { source = "timohirt/hetznerdns" }
  }
}

locals {
  use_cf = var.dns_provider == "cloudflare"
}

provider "cloudflare" {
  count = local.use_cf ? 1 : 0
  api_token = var.cloudflare_api_token
}

provider "hetznerdns" {
  count = local.use_cf ? 0 : 1
  apitoken = var.hetzner_dns_token
}

# --- Cloudflare path
data "cloudflare_zones" "zone" {
  count = local.use_cf ? 1 : 0
  filter { name = var.zone }
}

resource "cloudflare_record" "a_records" {
  count   = local.use_cf ? length(var.subdomains) : 0
  zone_id = data.cloudflare_zones.zone[0].zones[0].id
  name    = var.subdomains[count.index]
  type    = "A"
  value   = var.ipv4
  ttl     = 300
  proxied = false
}

# --- Hetzner DNS path
data "hetznerdns_zone" "zone" {
  count = local.use_cf ? 0 : 1
  name  = var.zone
}

resource "hetznerdns_record" "a_records" {
  count  = local.use_cf ? 0 : length(var.subdomains)
  zone_id = data.hetznerdns_zone.zone[0].id
  name    = var.subdomains[count.index]
  type    = "A"
  value   = var.ipv4
  ttl     = 300
}
