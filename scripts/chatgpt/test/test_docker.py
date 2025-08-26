#!/usr/bin/env python3
# Verifies expected containers are running
import subprocess, os

expected = ["traefik", "whoami", "prometheus", "grafana"]

def test_containers_running():
    out = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
    names = set(out.strip().splitlines())
    for e in expected:
        assert e in names, f"Container {e} not running. Found: {names}"
