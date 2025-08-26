#!/usr/bin/env python3
# Checks basic HTTP/S reachability and 2xx/3xx codes
import os, pytest, requests
DOMAIN = os.getenv("DOMAIN", "opendiscourse.net")

URLS = [
    f"http://traefik.{DOMAIN}",
    f"https://traefik.{DOMAIN}",
    f"https://whoami.{DOMAIN}",
    f"https://grafana.{DOMAIN}",
    f"https://prometheus.{DOMAIN}",
]

@pytest.mark.parametrize("url", URLS)
def test_http_ok(url):
    r = requests.get(url, timeout=20, verify=False)
    assert r.status_code in (200, 301, 302, 401), f"{url} -> {r.status_code}"
