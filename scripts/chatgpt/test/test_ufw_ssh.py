#!/usr/bin/env python3
# Ensure UFW is enabled and SSH port allowed
import subprocess, re, os

SSH_PORT = os.getenv("SSH_PORT", "22")

def test_ufw_enabled_and_ssh_allowed():
    out = subprocess.check_output(["ufw", "status"], text=True)
    assert "Status: active" in out
    pat = re.compile(rf"^{SSH_PORT}\/tcp\s+ALLOW", re.M)
    assert pat.search(out), f"SSH port {SSH_PORT} not allowed in UFW:\n{out}"
