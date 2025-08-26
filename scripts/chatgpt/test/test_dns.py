#!/usr/bin/env python3
# Confirms A records resolve to expected IP for critical subdomains
import os, socket
import dns.resolver
import pytest

DOMAIN = os.getenv("DOMAIN", "opendiscourse.net")
IPV4   = os.getenv("EXPECTED_IPV4", None)
SUBS   = os.getenv("SUBS", "traefik,whoami,prometheus,grafana").split(",")

@pytest.mark.skipif(IPV4 is None, reason="Set EXPECTED_IPV4 to run DNS tests")
@pytest.mark.parametrize("sub", SUBS)
def test_dns_a_records(sub):
    name = f"{sub.strip()}.{DOMAIN}"
    answers = dns.resolver.resolve(name, "A")
    addrs = sorted([a.address for a in answers])
    assert IPV4 in addrs, f"{name} -> {addrs}, expected {IPV4}"
