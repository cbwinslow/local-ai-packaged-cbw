#!/usr/bin/env python3
# =============================================================================
# File         : tools/check_recommendations.py
# Author       : CBW & ChatGPT
# Date         : 2025-08-11
# Summary      : Parse RECOMMENDATIONS_*.md files and report coverage vs
#                implemented features (naming, idempotency, UFW, ACME, Terraform,
#                tests, CI, hygiene).
# Inputs       : none
# Outputs      : Prints a coverage matrix to stdout; exit code 0 (informational).
# Security     : Read-only; does not modify repo.
# =============================================================================
import glob, os, re, sys

# Simple keywords -> feature map we commit to satisfying
FEATURES = {
    "naming":        ["supa-container", "systemd unit", "/opt/supa-container"],
    "idempotent":    ["bootstrap", "deploy", "idempotent", "safe re-run"],
    "ufw":           ["UFW", "allow 22/tcp", "deny incoming", "fail2ban"],
    "acme":          ["Traefik", "ACME", "HTTP-01", "acme.json"],
    "dns":           ["Terraform", "Cloudflare", "Hetzner DNS", "A records"],
    "tests":         ["pytest", "DNS", "TLS", "UFW", "Docker", "HTTP"],
    "ci":            ["GitHub Actions", "workflow", "pytest"],
    "hygiene":       ["gitignore", "backup files", "#config.sh#", ".#config.sh"],
    "folders":       ["/var/www/html", "nginx", "www subdomain"],
}

def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().lower()
    except Exception as e:
        return f"__ERR__ {e}"

def main():
    files = sorted(glob.glob("RECOMMENDATIONS_*.md"))
    if not files:
        print("No RECOMMENDATIONS_*.md files found.")
        return 0
    print(f"Found {len(files)} recommendations files.\n")

    # Collate text
    combined = "\n".join(read(p) for p in files)

    # Check per feature
    print("Coverage matrix (heuristic keyword match):")
    covered = {}
    for key, words in FEATURES.items():
        hit = any(w.lower() in combined for w in words)
        covered[key] = hit
        print(f" - {key:10} : {'OK' if hit else 'MISSING'}")

    # Always exit 0 (informational), rely on CI to display result
    return 0

if __name__ == "__main__":
    sys.exit(main())
