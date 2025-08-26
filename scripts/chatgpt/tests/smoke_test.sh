#!/usr/bin/env python3
# =============================================================================
# File         : tests/smoke_test.py
# Author       : CBW & ChatGPT
# Date         : 2025-08-10
# Summary      : Validates required environment and performs HTTP smoke checks.
# Inputs       : Env vars + optional BASE_URL, API_URL
# Outputs      : Pytest pass/fail
# Modification :
#   2025-08-10  Initial version
# =============================================================================
import os
import json
import pytest
import requests

REQUIRED_ENV = [
    # Traefik/ACME
    "TRAEFIK_DASHBOARD_USER",
    "TRAEFIK_DASHBOARD_PASS",
    # Supabase (managed or self-hosted)
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    # OAuth (NextAuth or custom)
    "NEXTAUTH_URL",
    "NEXTAUTH_SECRET",
    # DBs
    "POSTGRES_HOST",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
]

BASE_URL = os.getenv("BASE_URL", "https://your-domain.com")
API_URL = os.getenv("API_URL", "https://api.your-domain.com")

@pytest.mark.parametrize("key", REQUIRED_ENV)
def test_required_env_present(key):
    assert os.getenv(key), f"Missing required env: {key}"

@pytest.mark.parametrize("url", [BASE_URL, f"{API_URL}/docs", f"{API_URL}/health", f"{BASE_URL}/api/health"])
def test_http_endpoints(url):
    if "your-domain.com" in url:
        pytest.skip("Set BASE_URL and API_URL to real domains before running.")
    r = requests.get(url, timeout=15, verify=True)
    assert r.status_code in (200, 301, 302), f"{url} -> {r.status_code}"
