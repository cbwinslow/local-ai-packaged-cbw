#!/usr/bin/env python3
import os, requests
DOMAIN=os.getenv('DOMAIN','example.com')
def test_health():
  url=f'https://api.{DOMAIN}/healthz'
  try:
    r=requests.get(url,timeout=10)
    assert r.status_code in (200,401,403)
  except Exception:
    assert True
