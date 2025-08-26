#!/usr/bin/env python3
# Verifies a cert is presented on port 443 (ACME flow via Traefik)
import os, socket, ssl, pytest

DOMAIN = os.getenv("DOMAIN", "opendiscourse.net")
HOSTS = [f"traefik.{DOMAIN}", f"whoami.{DOMAIN}"]

@pytest.mark.parametrize("host", HOSTS)
def test_tls_cert_present(host):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=10) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
            assert cert, "No cert presented"
