# Practical Security Baseline (Focus: Access & Not Getting Locked Out)

Goal: You can always log in (SSH key preferred, password fallback) and reduce easy external attacks without over‑engineering.

## 1. SSH Access Strategy

1. Keep root login via password disabled, but allow root via SSH key (default on many images).
2. Create a non-root admin user (e.g. `ops`) with:
   - SSH public key in `~ops/.ssh/authorized_keys`
   - Strong fallback password stored in an offline password manager.
3. Keep at least TWO distinct valid SSH keys on the box (yours + a recovery key on secure hardware).
4. Test new key BEFORE closing the original session.

### Fast Commands (run as root once)
```bash
adduser --disabled-password --gecos "" ops
mkdir -p /home/ops/.ssh
chmod 700 /home/ops/.ssh
nano /home/ops/.ssh/authorized_keys   # paste your primary public key
chmod 600 /home/ops/.ssh/authorized_keys
chown -R ops:ops /home/ops/.ssh
# (optional) set password fallback
echo "ops:STRONGTEMPORARYPASS" | chpasswd
usermod -aG sudo ops || usermod -aG wheel ops 2>/dev/null || true
```

### Optional Recovery Key
```bash
# append a second public key
cat >> /home/ops/.ssh/authorized_keys
```
Paste, then Ctrl+D.

## 2. SSH Daemon Settings (Minimal Adjustments)
Edit `/etc/ssh/sshd_config` (or a drop-in under `/etc/ssh/sshd_config.d/`) and ensure:
```
PasswordAuthentication yes      # keep ON until you're 100% sure keys work, then you may switch to no
ChallengeResponseAuthentication no
PermitRootLogin prohibit-password
PubkeyAuthentication yes
PermitEmptyPasswords no
MaxAuthTries 4
LoginGraceTime 30
ClientAliveInterval 300
ClientAliveCountMax 2
```
Then restart:
```bash
systemctl restart sshd || service ssh restart
```

## 3. Basic Firewall (UFW Example)
Allow only what you need (SSH + HTTP/HTTPS):
```bash
ufw allow 22/tcp
ufw allow 80,443/tcp
ufw default deny incoming
ufw default allow outgoing
ufw enable
ufw status
```
If using a non-standard SSH port (optional), update `sshd_config` and firewall accordingly.

## 4. Fail2ban (Brute Force Throttle)
```bash
apt-get update && apt-get install -y fail2ban
cat >/etc/fail2ban/jail.d/ssh.local <<'EOF'
[sshd]
enabled = true
port    = 22
maxretry = 4
bantime = 15m
findtime = 10m
EOF
systemctl enable --now fail2ban
fail2ban-client status sshd
```
(Keep bantime modest early; you don't want to ban yourself for typos.)

## 5. Time Sync & Logs
```bash
apt-get install -y chrony
systemctl enable --now chrony
journalctl -u sshd -n 100 --no-pager
```
Accurate time helps audit and TLS.

## 6. Minimal Web Surface
While still in lean mode:
- No extra security headers needed yet (avoid breaking functionality early).
- Ensure reverse proxy only exposes needed ports (80/443).
- Do NOT map internal DB / admin ports directly.

## 7. Backups of Access
Store separately (encrypted):
- Authorized public keys
- The fallback password
- A copy of `sshd_config`

## 8. Verify Access Before Hardening Further
Open a SECOND terminal and confirm you can:
```bash
ssh ops@your.server.ip
```
If that works with key, then test password login intentionally once (optional). Only after that consider turning `PasswordAuthentication no`.

## 9. Optional: SSH Key Ed25519 Generation Command
```bash
ssh-keygen -t ed25519 -a 100 -f ~/.ssh/ops_ed25519 -C "ops-access"
```
Add the contents of `ops_ed25519.pub` to `authorized_keys`.

## 10. Quick Lockout Recovery Plan
If you lose access:
1. Use provider console (Hetzner) to mount a rescue system.
2. Mount the root filesystem, edit `/root/.ssh/authorized_keys` or revert `sshd_config`.
3. Reboot back into normal mode.

---
This baseline: ensures you keep access + trims common brute force risk without blocking functional debugging. Harden later (headers, rate limits, OAuth) after feature stability.
