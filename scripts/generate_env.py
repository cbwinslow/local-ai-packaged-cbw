#!/usr/bin/env python3
"""Generate a secure .env file for deployment.

Example:
  python scripts/generate_env.py --base-domain example.com --email admin@example.com > .env

If you already issued API keys to clients, preserve ANON_KEY & SERVICE_ROLE_KEY manually; this script rotates them.
"""
import argparse
import secrets


def rand_hex(n_bytes: int) -> str:
    return secrets.token_hex(n_bytes)


def rand_url(length: int) -> str:
    s = secrets.token_urlsafe(length)
    return s[:length]


def gen_jwt_like(role: str) -> str:
    header = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
    bodies = {
        'anon': 'eyAgCiAgICAicm9sZSI6ICJhbm9uIiwgImlzcyI6ICJzdXBhYmFzZS1sb2NhbCIsICJpYXQiOiAxNjQxNzY5MjAwLCAiZXhwIjogMTk5OTk5OTk5OSB9',
        'service_role': 'eyAgCiAgICAicm9sZSI6ICJzZXJ2aWNlX3JvbGUiLCAiaXNzIjogInN1cGFiYXNlLWxvY2FsIiwgImlhdCI6IDE2NDE3NjkyMDAsICJleHAiOiAxOTk5OTk5OTk5IH0'
    }
    signature = rand_hex(24)
    return f"{header}.{bodies[role]}.{signature}"


def build(args):
    domain = args.base_domain or 'localhost'
    def host(sub):
        return f"{sub}.{domain}" if domain != 'localhost' else f"{sub}.localhost"

    lines = []
    add = lines.append
    add("############")
    add("# Auto-generated environment file")
    add("############")
    add("N8N_ENCRYPTION_KEY=" + rand_hex(24))
    add("N8N_USER_MANAGEMENT_JWT_SECRET=" + rand_hex(32))
    add("")
    add("POSTGRES_PASSWORD=" + rand_url(32))
    add("JWT_SECRET=" + rand_url(48))
    add("ANON_KEY=" + gen_jwt_like('anon'))
    add("SERVICE_ROLE_KEY=" + gen_jwt_like('service_role'))
    add("DASHBOARD_USERNAME=supabase")
    add("DASHBOARD_PASSWORD=" + rand_url(24))
    add("POOLER_TENANT_ID=" + rand_hex(12))
    add("POOLER_DB_POOL_SIZE=5")
    add("POSTGRES_DB=postgres")
    add("POSTGRES_HOST=db")
    add("POSTGRES_PORT=5432")
    add("POSTGRES_USER=postgres")
    add("POOLER_DEFAULT_POOL_SIZE=20")
    add("POOLER_MAX_CLIENT_CONN=500")
    add("POOLER_PROXY_PORT_TRANSACTION=6543")
    add("KONG_HTTP_PORT=8000")
    add("KONG_HTTPS_PORT=8443")
    add("PGRST_DB_SCHEMAS=public,storage,graphql_public")
    add(f"API_EXTERNAL_URL=https://{host('supabase')}")
    add(f"SITE_URL=https://{host('supabase')}")
    add("STUDIO_DEFAULT_ORGANIZATION=Default")
    add("STUDIO_DEFAULT_PROJECT=Default")
    add("DISABLE_SIGNUP=false")
    add("ENABLE_EMAIL_SIGNUP=true")
    add("ENABLE_EMAIL_AUTOCONFIRM=true")
    add("ENABLE_PHONE_SIGNUP=false")
    add("ENABLE_PHONE_AUTOCONFIRM=false")
    add("ENABLE_ANONYMOUS_USERS=false")
    add("JWT_EXPIRY=3600")
    add("FUNCTIONS_VERIFY_JWT=true")
    add(f"SMTP_ADMIN_EMAIL=admin@{domain}")
    add("SMTP_HOST=smtp.example.com")
    add("SMTP_PORT=587")
    add("SMTP_USER=user")
    add("SMTP_PASS=change_me")
    add("SMTP_SENDER_NAME=LocalAI")
    for p in ["CONFIRMATION","INVITE","RECOVERY","EMAIL_CHANGE"]:
        add(f"MAILER_URLPATHS_{p}=\"/auth/v1/verify\"")
    add("NEO4J_AUTH=neo4j/" + rand_url(24))
    add("CLICKHOUSE_PASSWORD=" + rand_url(24))
    add("MINIO_ROOT_PASSWORD=" + rand_url(24))
    add("LANGFUSE_SALT=" + rand_url(24))
    add("NEXTAUTH_SECRET=" + rand_url(32))
    add("ENCRYPTION_KEY=" + rand_hex(32))
    add("FLOWISE_USERNAME=admin")
    add("FLOWISE_PASSWORD=" + rand_url(24))
    add("DOCKER_SOCKET_LOCATION=/var/run/docker.sock")
    add("VAULT_ENC_KEY=" + rand_hex(32))
    add("SECRET_KEY_BASE=" + rand_hex(64))
    add("LOGFLARE_PUBLIC_ACCESS_TOKEN=" + rand_hex(32))
    add("LOGFLARE_PRIVATE_ACCESS_TOKEN=" + rand_hex(32))
    add(f"N8N_HOSTNAME={host('n8n')}")
    add(f"WEBUI_HOSTNAME={host('openwebui')}")
    add(f"FLOWISE_HOSTNAME={host('flowise')}")
    add(f"SUPABASE_HOSTNAME={host('supabase')}")
    add(f"LANGFUSE_HOSTNAME={host('langfuse')}")
    add(f"OLLAMA_HOSTNAME={host('ollama')}")
    add(f"SEARXNG_HOSTNAME={host('searxng')}")
    add(f"NEO4J_HOSTNAME={host('neo4j')}")
    add(f"LETSENCRYPT_EMAIL={args.email}")
    add(f"SUPABASE_PUBLIC_URL=https://{host('supabase')}")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-domain')
    parser.add_argument('--email', default='admin@example.com')
    args = parser.parse_args()
    print(build(args))


if __name__ == '__main__':
    main()
