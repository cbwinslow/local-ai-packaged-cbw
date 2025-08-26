#!/usr/bin/env python3
# Validates required env vars and secret presence
import os

REQUIRED = [
    "DOMAIN", "ACME_EMAIL",
    # Optional, but if present should be strong:
    # "NEXTAUTH_SECRET", "SUPABASE_JWT_SECRET"
]

def test_env_basics_present():
    for k in REQUIRED:
        assert os.getenv(k), f"Missing env var: {k}"

def test_nextauth_secret_strength():
    sec = os.getenv("NEXTAUTH_SECRET", "")
    if sec:
        assert len(sec) >= 32, "NEXTAUTH_SECRET should be >= 32 chars"

def test_supabase_jwt_secret_strength():
    sec = os.getenv("SUPABASE_JWT_SECRET", "")
    if sec:
        assert len(sec) >= 32, "SUPABASE_JWT_SECRET should be >= 32 chars"
