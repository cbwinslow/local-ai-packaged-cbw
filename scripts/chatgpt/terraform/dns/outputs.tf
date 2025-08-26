output "fqdn_records" {
  value = [for s in var.subdomains : "${s}.${var.zone} -> ${var.ipv4}"]
}
