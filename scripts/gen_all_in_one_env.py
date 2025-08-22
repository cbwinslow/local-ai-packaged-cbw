#!/usr/bin/env python3
"""Generate .env from .env.all-in-one.example filling random secrets where placeholders remain.

Usage:
  python scripts/gen_all_in_one_env.py [output=.env]
"""
from __future__ import annotations
import secrets
import string
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / ".env.all-in-one.example"
OUTPUT = ROOT / (sys.argv[1] if len(sys.argv) > 1 else ".env")

# Keys we want stronger length for
LONG_KEYS = {"JWT_SECRET", "SERVICE_ROLE_KEY", "ANON_KEY", "N8N_ENCRYPTION_KEY", "N8N_USER_MANAGEMENT_JWT_SECRET", "CLICKHOUSE_PASSWORD", "MINIO_ROOT_PASSWORD", "LANGFUSE_SALT", "ENCRYPTION_KEY", "NEXTAUTH_SECRET", "POSTGRES_PASSWORD",
             # Newly added keys we want long secrets for
             "SUPABASE_DB_PASSWORD", "SECRET_KEY_BASE", "VAULT_ENC_KEY", "LOGFLARE_PUBLIC_ACCESS_TOKEN", "LOGFLARE_PRIVATE_ACCESS_TOKEN"}

ALPHANUM = string.ascii_letters + string.digits
SYMBOLS = "!@#$%^&*-_"  # safe for most env uses


def random_value(length: int) -> str:
    return ''.join(secrets.choice(ALPHANUM + SYMBOLS) for _ in range(length))


def gen_for_key(key: str) -> str:
    base_len = 48 if key in LONG_KEYS else 32
    return random_value(base_len)


def main():
    if not TEMPLATE.exists():
        print(f"Template not found: {TEMPLATE}", file=sys.stderr)
        sys.exit(1)

    lines = TEMPLATE.read_text().splitlines()
    out_lines = []
    for line in lines:
        if not line or line.startswith('#') or '=' not in line:
            out_lines.append(line)
            continue
        key, value = line.split('=', 1)
        if value.startswith('change_me'):
            out_lines.append(f"{key}={gen_for_key(key)}")
        else:
            out_lines.append(line)

    if OUTPUT.exists():
        # create a timestamped backup instead of overwriting
        from datetime import datetime
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        backup = OUTPUT.with_name(f"{OUTPUT.name}.{ts}.bak")
        OUTPUT.replace(backup)
        print(f"Existing {OUTPUT.name} backed up to {backup.name}")

    OUTPUT.write_text("\n".join(out_lines) + "\n")
    print(f"Generated {OUTPUT}")

if __name__ == "__main__":
    main()
