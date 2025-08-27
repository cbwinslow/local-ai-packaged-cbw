#!/usr/bin/env python3
"""
start_services.py

This script starts the Supabase stack first, waits for it to initialize, and then starts
the local AI stack. Both stacks use the same Docker Compose project name ("localai")
so they appear together in Docker Desktop.
"""

import os
import subprocess
import shutil
import time
import argparse

import urllib.request
import sys
import re
import tempfile
import yaml

def run_command(cmd, cwd=None, env_override=None, ignore_errors=False, timeout=None):
    """Run a shell command with enhanced error handling.

    Args:
        cmd: Command list to execute
        cwd: Working directory for the command
        env_override: dict of environment variables to add/override for this command
        ignore_errors: If True, don't raise exception on command failure
        timeout: Command timeout in seconds
    
    Returns:
        subprocess.CompletedProcess object
    
    Raises:
        CommandExecutionError: If command fails and ignore_errors=False
    """
    print("Running:", " ".join(cmd))
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            check=not ignore_errors, 
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode != 0 and not ignore_errors:
            raise CommandExecutionError(
                f"Command failed with exit code {result.returncode}",
                cmd, result.returncode, result.stdout, result.stderr
            )
        
        # Print output if command succeeded or if we're ignoring errors
        if result.stdout:
            print("STDOUT:", result.stdout)
        if result.stderr and result.returncode == 0:
            print("STDERR:", result.stderr)
        
        return result
    
    except subprocess.TimeoutExpired as e:
        error_msg = f"Command timed out after {timeout} seconds: {' '.join(cmd)}"
        print(f"ERROR: {error_msg}")
        if not ignore_errors:
            raise CommandExecutionError(error_msg, cmd, -1, "", "Timeout")
        return None
    except FileNotFoundError as e:
        error_msg = f"Command not found: {cmd[0]}. Please ensure it's installed and in your PATH."
        print(f"ERROR: {error_msg}")
        if not ignore_errors:
            raise CommandExecutionError(error_msg, cmd, -1, "", str(e))
        return None
    except Exception as e:
        error_msg = f"Unexpected error running command: {e}"
        print(f"ERROR: {error_msg}")
        if not ignore_errors:
            raise CommandExecutionError(error_msg, cmd, -1, "", str(e))
        return None

class CommandExecutionError(Exception):
    """Custom exception for command execution failures."""
    
    def __init__(self, message, cmd, exit_code, stdout, stderr):
        self.message = message
        self.cmd = cmd
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(self.message)
    
    def __str__(self):
        lines = [
            f"Command execution failed: {' '.join(self.cmd)}",
            f"Exit code: {self.exit_code}",
            f"Error: {self.message}"
        ]
        
        if self.stderr:
            lines.append(f"STDERR: {self.stderr}")
        if self.stdout:
            lines.append(f"STDOUT: {self.stdout}")
            
        # Add troubleshooting suggestions
        if "docker" in self.cmd[0].lower():
            lines.extend([
                "",
                "Docker troubleshooting suggestions:",
                "- Ensure Docker is running: sudo systemctl start docker",
                "- Check Docker permissions: sudo usermod -aG docker $USER",
                "- Try restarting Docker service",
                "- Check available disk space: df -h"
            ])
        elif "git" in self.cmd[0].lower():
            lines.extend([
                "",
                "Git troubleshooting suggestions:",
                "- Check internet connectivity",
                "- Verify repository URL and access permissions",
                "- Check if git is installed: git --version"
            ])
        
        return "\n".join(lines)

def patch_supabase_compose():
    """Remove Supabase supavisor service to avoid missing image errors."""
    compose_file = os.path.join("supabase", "docker", "docker-compose.yml")
    if not os.path.exists(compose_file):
        return
    try:
        with open(compose_file, "r") as f:
            data = yaml.safe_load(f) or {}
        services = data.get("services", {})
        removed = False
        for svc in ["supabase-pooler", "supavisor"]:
            if services.pop(svc, None) is not None:
                removed = True
        if removed:
            with open(compose_file, "w") as f:
                yaml.safe_dump(data, f, sort_keys=False)
            print("Removed Supabase supavisor service from docker-compose.yml")
    except Exception as e:
        print(f"Warning: unable to patch Supabase compose file: {e}")

def clone_supabase_repo():
    """Clone the Supabase repository using sparse checkout if not already present."""
    try:
        if not os.path.exists("supabase"):
            print("Cloning the Supabase repository...")
            run_command([
                "git", "clone", "--filter=blob:none", "--no-checkout",
                "https://github.com/supabase/supabase.git"
            ], timeout=300)  # 5 minute timeout for clone
            
            os.chdir("supabase")
            try:
                run_command(["git", "sparse-checkout", "init", "--cone"])
                run_command(["git", "sparse-checkout", "set", "docker"])
                run_command(["git", "checkout", "master"], ignore_errors=True)
                if not os.path.exists("docker"):
                    # Try main branch if master didn't work
                    run_command(["git", "checkout", "main"], ignore_errors=True)
            finally:
                os.chdir("..")
        else:
            print("Supabase repository already exists, attempting to update (non-fatal)...")
            original_dir = os.getcwd()
            try:
                os.chdir("supabase")
                # Fetch all remotes and try to set a known branch
                run_command(["git", "fetch", "--all"], ignore_errors=True, timeout=120)
                
                # Try to checkout master, fall back to main, otherwise leave as-is
                master_result = run_command(["git", "checkout", "master"], ignore_errors=True)
                if master_result and master_result.returncode != 0:
                    main_result = run_command(["git", "checkout", "main"], ignore_errors=True)
                    if main_result and main_result.returncode != 0:
                        print("Could not checkout master or main; leaving current branch as-is")

                # Try a pull but don't let it hard-fail the whole script
                run_command(["git", "pull"], ignore_errors=True, timeout=120)
            except Exception as e:
                print(f"Warning: failed to update supabase repo: {e}; continuing")
            finally:
                try:
                    os.chdir(original_dir)
                except Exception:
                    pass
        
        # Verify the docker directory exists
        if not os.path.exists("supabase/docker"):
            raise Exception("Supabase docker directory not found after clone/update. This may indicate a repository structure change.")
        
        patch_supabase_compose()
        
    except CommandExecutionError as e:
        print(f"Failed to setup Supabase repository: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check internet connectivity")
        print("2. Verify git is installed: git --version")
        print("3. Try manual clone: git clone https://github.com/supabase/supabase.git")
        print("4. Check if there are any firewall restrictions")
        raise
    except Exception as e:
        print(f"Unexpected error setting up Supabase repository: {e}")
        raise

def prepare_supabase_env():
    """Ensure a usable .env exists in repo root and copy it into supabase/docker/.env.

    If .env is missing or appears incomplete, attempt to auto-generate it using the
    repository helper scripts `scripts/gen_all_in_one_env.py` or `scripts/generate_env.py`.
    """
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    root_env = os.path.join(repo_dir, ".env")
    supabase_env = os.path.join(repo_dir, "supabase", "docker", ".env")

    def generate_env_if_missing():
        gen_script = os.path.join(repo_dir, "scripts", "gen_all_in_one_env.py")
        gen_fallback = os.path.join(repo_dir, "scripts", "generate_env.py")
        if os.path.exists(gen_script):
            print("Generating .env from scripts/gen_all_in_one_env.py...")
            try:
                # Run the generator with the repository root as cwd so it can
                # write .env and backup files in the expected location.
                run_command([sys.executable, gen_script], cwd=repo_dir)
                print("gen_all_in_one_env.py completed; expecting .env in repo root")
            except subprocess.CalledProcessError:
                print("gen_all_in_one_env.py failed; trying generate_env.py fallback")
        if not os.path.exists(root_env) and os.path.exists(gen_fallback):
            print("Generating .env from scripts/generate_env.py (fallback)...")
            try:
                out = subprocess.check_output([sys.executable, gen_fallback])
                with open(root_env, "wb") as f:
                    f.write(out)
                print("Wrote generated .env to repo root")
            except Exception as e:
                print("Failed to auto-generate .env:", e)

    if not os.path.exists(root_env):
        print("No .env found in repo root; attempting to auto-generate one...")
        generate_env_if_missing()

    def read_env(path):
        vals = {}
        if not os.path.exists(path):
            return vals
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                vals[k] = v
        return vals

    required = ["POSTGRES_HOST", "POSTGRES_DB", "POSTGRES_PORT", "NEO4J_AUTH", "DOCKER_SOCKET_LOCATION"]
    env_vals = read_env(root_env)
    missing = [k for k in required if not env_vals.get(k)]
    if missing:
        print("Some required .env keys are missing or empty:", missing)
        print("Attempting to regenerate .env once more...")
        generate_env_if_missing()
        env_vals = read_env(root_env)
        missing = [k for k in required if not env_vals.get(k)]
        # If still missing, try the more complete generator which prints a full .env
        if missing:
            gen_fallback = os.path.join(repo_dir, "scripts", "generate_env.py")
            if os.path.exists(gen_fallback):
                print("Running fallback scripts/generate_env.py to produce a more complete .env...")
                try:
                    out = subprocess.check_output([sys.executable, gen_fallback])
                    with open(root_env, "wb") as f:
                        f.write(out)
                    print("Wrote fallback-generated .env to repo root")
                except Exception as e:
                    print("Failed to run fallback generate_env.py:", e)
                env_vals = read_env(root_env)
                missing = [k for k in required if not env_vals.get(k)]
        if missing:
            print("Warning: after auto-generation, these keys are still missing:", missing)
            print("Docker compose may fail; please inspect .env or run scripts/generate_env.py manually.")

    if os.path.exists(root_env):
        print("Copying .env in root to .env in supabase/docker...")
        try:
            # Ensure supabase/docker exists
            supabase_dir = os.path.dirname(supabase_env)
            os.makedirs(supabase_dir, exist_ok=True)
            shutil.copyfile(root_env, supabase_env)
        except Exception as e:
            print("Failed to copy .env to supabase/docker/.env:", e)

def stop_existing_containers(profile=None):
    print("Stopping and removing existing containers for the unified project 'localai'...")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml", "down"])
    env_override = {"DOCKER_SOCKET_LOCATION": os.environ.get("DOCKER_SOCKET_LOCATION", "/var/run/docker.sock")}
    try:
        run_command(cmd, env_override=env_override)
    except subprocess.CalledProcessError as e:
        print("docker compose down failed:", e)
        print("If this is due to a bad .env, try running scripts/generate_env.py to create a complete .env, then re-run this script.")

def start_supabase(environment=None):
    """Start the Supabase services (using its compose file)."""
    print("Starting Supabase services...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "supabase/docker/docker-compose.yml"]
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.supabase.yml"])
    cmd.extend(["up", "-d"])
    env_override = {"DOCKER_SOCKET_LOCATION": os.environ.get("DOCKER_SOCKET_LOCATION", "/var/run/docker.sock")}
    try:
        run_command(cmd, env_override=env_override)
    except subprocess.CalledProcessError as e:
        print("docker compose up for Supabase failed:", e)
        print("Common causes: incomplete .env, docker registry auth issues, or insufficient memory for extracting images.")
        print("Suggested actions:")
        print("  - Ensure .env exists and contains keys like POSTGRES_HOST, POSTGRES_DB, POSTGRES_PORT, DOCKER_SOCKET_LOCATION")
        print("  - Run: python3 scripts/generate_env.py > .env and then re-run")
        print("  - If pulling images fails due to credentials, run 'docker login' and retry.")
        raise


def start_neo4j():
    """Start Neo4j service via docker compose (if defined in compose file)."""
    print("Starting Neo4j service (if present in compose)...")
    cmd = ["docker", "compose", "-p", "localai", "-f", "docker-compose.yml", "up", "-d", "neo4j"]
    env_override = {"DOCKER_SOCKET_LOCATION": os.environ.get("DOCKER_SOCKET_LOCATION", "/var/run/docker.sock")}
    try:
        run_command(cmd, env_override=env_override)
    except subprocess.CalledProcessError:
        print("Failed to start Neo4j via a dedicated service bring-up; falling back to full compose up")
        try:
            run_command(["docker", "compose", "-p", "localai", "-f", "docker-compose.yml", "up", "-d"], env_override=env_override)
        except subprocess.CalledProcessError as e:
            print(f"Error starting compose: {e}")


# http_get is defined once above and used by wait functions


def http_get(url, timeout=3):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.getcode()
    except Exception:
        return None


def wait_for_supabase(timeout=180):
    print("Waiting for Supabase (auth, rest) to become ready...")
    start = time.time()
    targets = {
        "auth": "http://localhost:9999/health",
        "rest": "http://localhost:8000/rest/v1/"
    }
    ready = set()
    while time.time() - start < timeout:
        for name, url in targets.items():
            if name in ready:
                continue
            code = http_get(url)
            if code and code < 600:
                print(f"  {name} up (HTTP {code})")
                ready.add(name)
        if len(ready) == len(targets):
            print("Supabase core endpoints responding.")
            return True
        time.sleep(3)
    print("Timeout waiting for Supabase; proceeding anyway.")
    return False


def wait_for_neo4j(timeout=120):
    """Wait for Neo4j HTTP endpoint (default port 7474) to become available."""
    print("Waiting for Neo4j to become ready (HTTP 7474)...")
    start = time.time()
    host_url = "http://localhost:7474/"

    def check_host():
        return http_get(host_url)

    def find_neo4j_container():
        try:
            out = subprocess.check_output(["docker", "ps", "--filter", "name=neo4j", "--format", "{{.Names}}"], text=True)
            names = [n.strip() for n in out.splitlines() if n.strip()]
            return names[0] if names else None
        except Exception:
            return None

    def check_inside_with_curl(cname):
        try:
            # Test whether curl exists in the container
            rc = subprocess.call(["docker", "exec", cname, "sh", "-c", "command -v curl >/dev/null 2>&1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if rc == 0:
                out = subprocess.check_output([
                    "docker", "exec", cname, "sh", "-c",
                    "curl -s -o /dev/null -w '%{http_code}' http://localhost:7474/ || true"
                ], text=True).strip()
                if out and out.isdigit() and int(out) != 0:
                    return int(out)
        except Exception:
            pass
        return None

    def check_inside_with_python(cname):
        try:
            # Some minimal images include python; try a tiny python HTTP check inside
            py_cmd = (
                "python3 -c \"import http.client,sys; c=http.client.HTTPConnection('localhost',7474,timeout=3); c.request('GET','/'); r=c.getresponse(); print(r.status)\""
            )
            out = subprocess.check_output(["docker", "exec", cname, "sh", "-c", py_cmd], text=True, stderr=subprocess.DEVNULL).strip()
            if out and out.isdigit():
                return int(out)
        except Exception:
            pass
        return None

    def logs_indicate_ready(cname):
        try:
            logs = subprocess.check_output(["docker", "logs", "--tail", "500", cname], text=True, stderr=subprocess.DEVNULL)
            markers = ["Bolt enabled", "Started", "Remote interface available", "Bolt connector enabled", "Started database", "Server started"]
            for m in markers:
                if m in logs:
                    return True
        except Exception:
            pass
        return False

    while time.time() - start < timeout:
        code = check_host()
        if code and code < 600:
            print(f"Neo4j up (HTTP {code})")
            return True

        cname = find_neo4j_container()
        if cname:
            inner = check_inside_with_curl(cname)
            if inner and inner < 600:
                print(f"Neo4j up inside container {cname} (HTTP {inner})")
                return True
            inner = check_inside_with_python(cname)
            if inner and inner < 600:
                print(f"Neo4j up inside container {cname} (HTTP {inner})")
                return True
            if logs_indicate_ready(cname):
                print(f"Neo4j logs indicate service started inside container {cname}")
                return True

        time.sleep(2)

    print("Timeout waiting for Neo4j; proceeding anyway.")
    return False

def start_local_ai(profile=None, environment=None):
    """Start the local AI services (using its compose file)."""
    print("Starting local AI services...")

    # Ensure any locally-built images required by compose are present.
    # A common failure mode is a service (e.g. `portal`) that expects a locally-built
    # image like `localai-portal:latest` which isn't available on registries. In CI
    # or developer machines the docker-buildx plugin may be missing which can make
    # `docker compose up` fail during builds. Try to detect and build the portal
    # image with plain `docker build` if needed.
    def ensure_local_images():
        portal_image = "localai-portal:latest"
        # Check if the image exists locally
        try:
            subprocess.run(["docker", "image", "inspect", portal_image], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"Local image {portal_image} already exists; skipping local build.")
            return
        except subprocess.CalledProcessError:
            # Image not found locally; attempt to build if portal/ Dockerfile exists
            portal_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "portal")
            dockerfile = os.path.join(portal_dir, "Dockerfile")
            if os.path.exists(dockerfile):
                print(f"Local image {portal_image} not found. Building from {portal_dir}...")
                try:
                    run_command(["docker", "build", "-t", portal_image, "."], cwd=portal_dir)
                    print(f"Built {portal_image} successfully.")
                except subprocess.CalledProcessError as e:
                    print(f"Failed to build {portal_image}: {e}")
                    print("You can try to install the docker buildx plugin or build the image manually:")
                    print(f"  docker build -t {portal_image} {portal_dir}")
            else:
                print(f"Portal Dockerfile not found at {dockerfile}; skipping local portal build.")

    ensure_local_images()

    # Detect host port conflicts for the private override and generate a temporary
    # override file that remaps conflicting host ports to available ports on localhost.
    def get_listening_ports():
        """Return a set of TCP listening ports on the host (integers)."""
        ports = set()
        try:
            out = subprocess.check_output(["ss", "-ltnp"], text=True)
            for line in out.splitlines():
                m = re.search(r":(\d+)\s", line)
                if m:
                    try:
                        ports.add(int(m.group(1)))
                    except Exception:
                        continue
        except Exception:
            # If ss isn't available fallback to lsof (best-effort) or return empty
            try:
                out = subprocess.check_output(["lsof", "-iTCP","-sTCP:LISTEN","-P","-n"], text=True)
                for line in out.splitlines():
                    m = re.search(r":(\d+)->|:(\d+) \(LISTEN\)|:(\d+)$", line)
                    if m:
                        for g in m.groups():
                            if g:
                                ports.add(int(g))
            except Exception:
                return ports
        return ports

    def parse_private_override_ports(path):
        """Parse the private override file for explicit host-to-container port mappings.

        Returns a dict of service -> list of (host_port, container_port) tuples.
        """
        svc_ports = {}
        if not os.path.exists(path):
            return svc_ports
        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    # match patterns like: - 127.0.0.1:3001:3001
                    m = re.match(r"-\s*127\.0\.0\.1:(\d+):(\d+)", line)
                    if m:
                        host_p = int(m.group(1))
                        cont_p = int(m.group(2))
                        # We don't know the service name here, so store under a special key
                        svc_ports.setdefault('__anonymous__', []).append((host_p, cont_p))
        except Exception:
            return svc_ports
        return svc_ports

    def find_next_free_port(start, used):
        p = start
        while p in used or p < 1024:
            p += 1
        return p

    # Only consider the private override mappings for remapping (these are the ones
    # that use 127.0.0.1:HOST:CONTAINER and are likely to conflict with host services).
    private_override = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docker-compose.override.private.yml')
    parsed = parse_private_override_ports(private_override)
    listening = get_listening_ports()
    temp_override_path = None
    remap = []
    if parsed and parsed.get('__anonymous__'):
        for host_p, cont_p in parsed['__anonymous__']:
            if host_p in listening:
                new_p = find_next_free_port(host_p + 1, listening)
                print(f"Port {host_p} is already in use on the host; remapping to {new_p} in a temporary override file.")
                remap.append((host_p, cont_p, new_p))
                listening.add(new_p)

    # If we have remaps to do, write a small temporary docker-compose override file
    # that publishes the new host ports for the services that need them. We apply
    # these remaps at the service-agnostic level by creating entries for the known
    # services that map to those container ports. This is a best-effort approach.
    if remap:
        # Map container ports to candidate services by scanning docker-compose.yml
        compose_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'docker-compose.yml')
        contport_to_service = {}
        try:
            with open(compose_path, 'r') as f:
                cur_service = None
                for line in f:
                    msvc = re.match(r'^(\s*)([a-zA-Z0-9_-]+):\s*$', line)
                    if msvc and line.startswith('  '):
                        # service line (top-level under services uses two spaces)
                        cur_service = line.strip().split(':')[0]
                    pm = re.search(r"-\s*(\d+)(?:/tcp)?\s*$", line.strip())
                    if pm and cur_service:
                        try:
                            cp = int(pm.group(1))
                            contport_to_service[cp] = cur_service
                        except Exception:
                            continue
        except Exception:
            pass

        # Build override YAML content, aggregating ports under each service to avoid
        # duplicate keys like 'ports' or 'expose' being written multiple times.
        svc_to_ports = {}
        for host_p, cont_p, new_p in remap:
            svc = contport_to_service.get(cont_p, None)
            srvname = svc if svc else f'unknown_{cont_p}'
            svc_to_ports.setdefault(srvname, []).append((new_p, cont_p))

        lines = ["version: '3'", "services:"]
        for srvname, ports in svc_to_ports.items():
            lines.append(f"  {srvname}:")
            lines.append("    ports:")
            for new_p, cont_p in ports:
                lines.append(f"      - '127.0.0.1:{new_p}:{cont_p}'")

        # Write to a temp file
        fd, temp_path = tempfile.mkstemp(prefix='docker-override-', suffix='.yml')
        with os.fdopen(fd, 'w') as tf:
            tf.write('\n'.join(lines) + '\n')
        temp_override_path = temp_path
        print(f"Wrote temporary compose override to {temp_override_path}")
    cmd = ["docker", "compose", "-p", "localai"]
    if profile and profile != "none":
        cmd.extend(["--profile", profile])
    cmd.extend(["-f", "docker-compose.yml"])
    if environment and environment == "private":
        cmd.extend(["-f", "docker-compose.override.private.yml"])
    if environment and environment == "public":
        cmd.extend(["-f", "docker-compose.override.public.yml"])
    # If we created a temp override, include it in the compose invocation so
    # the remapped host ports are used instead of the original conflicting ones.
    if temp_override_path:
        cmd.extend(["-f", temp_override_path])
    cmd.extend(["up", "-d"])
    env_override = {"DOCKER_SOCKET_LOCATION": os.environ.get("DOCKER_SOCKET_LOCATION", "/var/run/docker.sock")}
    try:
        run_command(cmd, env_override=env_override)
    except subprocess.CalledProcessError as e:
        print("docker compose up for local AI failed:", e)
        print("Suggested action: confirm .env is complete and docker has enough memory; try re-running with --preflight to validate environment first.")
        raise
    finally:
        # Cleanup temporary override file if we wrote one
        if temp_override_path and os.path.exists(temp_override_path):
            try:
                os.remove(temp_override_path)
                print(f"Removed temporary override file {temp_override_path}")
            except Exception:
                pass


def start_nextjs_dev():
    """Start Next.js dev server if a Next.js app is present (looks for package.json with next dependency)."""
    app_dirs = []
    # Common locations: ./web, ./portal, ./supabase/studio, ./app
    candidates = ["portal", "web", "frontend", "app", "supabase/studio"]
    for d in candidates:
        pkg = os.path.join(d, "package.json")
        if os.path.exists(pkg):
            try:
                with open(pkg, 'r') as f:
                    txt = f.read()
                    if '"next"' in txt or 'nextjs' in txt:
                        app_dirs.append(d)
            except Exception:
                continue

    if not app_dirs:
        print("No Next.js app detected in common locations; skipping Next.js dev start.")
        return

    # Start the first detected Next.js app in a background process via npm/yarn/pnpm
    app_dir = app_dirs[0]
    print(f"Detected Next.js app in '{app_dir}', attempting to start dev server...")
    # Prefer pnpm, then npm, then yarn
    if shutil.which("pnpm"):
        cmd = ["pnpm", "dev"]
    elif shutil.which("npm"):
        cmd = ["npm", "run", "dev"]
    elif shutil.which("yarn"):
        cmd = ["yarn", "dev"]
    else:
        print("No package manager found (pnpm/npm/yarn). Skipping Next.js dev start.")
        return

    # Launch in background using subprocess.Popen so script can continue
    try:
        print("Launching Next.js dev server in background (check logs in terminal)")
        subprocess.Popen(cmd, cwd=app_dir)
    except Exception as e:
        print(f"Failed to start Next.js dev server: {e}")

def generate_searxng_secret_key():
    """Generate a secret key for SearXNG based on the current platform."""
    print("Checking SearXNG settings...")
    
    # Define paths for SearXNG settings files
    settings_path = os.path.join("searxng", "settings.yml")
    settings_base_path = os.path.join("searxng", "settings-base.yml")
    
    # Check if settings-base.yml exists
    if not os.path.exists(settings_base_path):
        print(f"Warning: SearXNG base settings file not found at {settings_base_path}")
        return
    
    # Check if settings.yml exists, if not create it from settings-base.yml
    if not os.path.exists(settings_path):
        print(f"SearXNG settings.yml not found. Creating from {settings_base_path}...")
        try:
            shutil.copyfile(settings_base_path, settings_path)
            print(f"Created {settings_path} from {settings_base_path}")
        except Exception as e:
            print(f"Error creating settings.yml: {e}")
            return
    else:
        print(f"SearXNG settings.yml already exists at {settings_path}")
    
    print("Generating SearXNG secret key (Python-based, avoids sed)...")
    try:
        # Use Python's openssl subprocess to generate a random hex key
        random_key = subprocess.check_output(["openssl", "rand", "-hex", "32"]).decode('utf-8').strip()

        # Read the settings file and replace the placeholder token
        with open(settings_path, 'r') as f:
            content = f.read()

        if 'ultrasecretkey' not in content:
            print("No 'ultrasecretkey' placeholder found in searxng/settings.yml; no change required.")
            return

        new_content = content.replace('ultrasecretkey', random_key)

        # Attempt to write back safely. If permission denied, provide clear guidance.
        try:
            with open(settings_path, 'w') as f:
                f.write(new_content)
            print("SearXNG secret key written to searxng/settings.yml successfully.")
        except PermissionError:
            print("Permission denied when writing searxng/settings.yml. Attempting a best-effort fix...")
            try:
                # If running as root, try to chown the file to the current user
                if os.geteuid() == 0:
                    uid = int(os.environ.get('SUDO_UID', os.getuid()))
                    gid = int(os.environ.get('SUDO_GID', os.getgid()))
                    print(f"Running as root; attempting to chown {settings_path} to {uid}:{gid}")
                    os.chown(settings_path, uid, gid)
                    with open(settings_path, 'w') as f:
                        f.write(new_content)
                    print("SearXNG secret key written after chown.")
                else:
                    print(f"Please run: sudo chown $(id -u):$(id -g) {settings_path}")
                    print(f"Then run this script again or perform the replacement manually:\n  sed -i 's|ultrasecretkey|{random_key}|g' {settings_path}")
            except Exception as e:
                print(f"Failed to auto-fix permissions: {e}")
                print(f"Please run: sudo chown $(id -u):$(id -g) {settings_path} && sed -i 's|ultrasecretkey|{random_key}|g' {settings_path}")
    except Exception as e:
        print(f"Error generating SearXNG secret key: {e}")
        print("You can generate a key manually with: openssl rand -hex 32")

def check_and_fix_docker_compose_for_searxng():
    """Check and modify docker-compose.yml for SearXNG first run."""
    docker_compose_path = "docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        print(f"Warning: Docker Compose file not found at {docker_compose_path}")
        return
    
    try:
        # Read the docker-compose.yml file
        with open(docker_compose_path, 'r') as file:
            content = file.read()
        
        # Default to first run
        is_first_run = True
        
        # Check if Docker is running and if the SearXNG container exists
        try:
            # Check if the SearXNG container is running
            container_check = subprocess.run(
                ["docker", "ps", "--filter", "name=searxng", "--format", "{{.Names}}"],
                capture_output=True, text=True, check=True
            )
            searxng_containers = container_check.stdout.strip().split('\n')
            
            # If SearXNG container is running, check inside for uwsgi.ini
            if any(container for container in searxng_containers if container):
                container_name = next(container for container in searxng_containers if container)
                print(f"Found running SearXNG container: {container_name}")
                
                # Check if uwsgi.ini exists inside the container
                container_check = subprocess.run(
                    ["docker", "exec", container_name, "sh", "-c", "[ -f /etc/searxng/uwsgi.ini ] && echo 'found' || echo 'not_found'"],
                    capture_output=True, text=True, check=False
                )
                
                if "found" in container_check.stdout:
                    print("Found uwsgi.ini inside the SearXNG container - not first run")
                    is_first_run = False
                else:
                    print("uwsgi.ini not found inside the SearXNG container - first run")
                    is_first_run = True
            else:
                print("No running SearXNG container found - assuming first run")
        except Exception as e:
            print(f"Error checking Docker container: {e} - assuming first run")
        
        if is_first_run and "cap_drop: - ALL" in content:
            print("First run detected for SearXNG. Temporarily removing 'cap_drop: - ALL' directive...")
            # Temporarily comment out the cap_drop line
            modified_content = content.replace("cap_drop: - ALL", "# cap_drop: - ALL  # Temporarily commented out for first run")
            
            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)
                
            print("Note: After the first run completes successfully, you should re-add 'cap_drop: - ALL' to docker-compose.yml for security reasons.")
        elif not is_first_run and "# cap_drop: - ALL  # Temporarily commented out for first run" in content:
            print("SearXNG has been initialized. Re-enabling 'cap_drop: - ALL' directive for security...")
            # Uncomment the cap_drop line
            modified_content = content.replace("# cap_drop: - ALL  # Temporarily commented out for first run", "cap_drop: - ALL")
            
            # Write the modified content back
            with open(docker_compose_path, 'w') as file:
                file.write(modified_content)
    
    except Exception as e:
        print(f"Error checking/modifying docker-compose.yml for SearXNG: {e}")

def main():
    parser = argparse.ArgumentParser(description='Start the local AI and Supabase services.')
    parser.add_argument('--profile', choices=['cpu', 'gpu-nvidia', 'gpu-amd', 'none'], default='cpu',
                      help='Profile to use for Docker Compose (default: cpu)')
    parser.add_argument('--environment', choices=['private', 'public'], default='private',
                      help='Environment to use for Docker Compose (default: private)')
    parser.add_argument('--skip-neo4j', action='store_true', help='Do not start Neo4j')
    parser.add_argument('--start-nextjs', action='store_true', help='Attempt to start a Next.js dev server if detected')
    parser.add_argument('--preflight', action='store_true', help='Run environment checks and exit without starting containers')
    args = parser.parse_args()
    clone_supabase_repo()
    prepare_supabase_env()
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    if args.preflight:
        print("Preflight checks completed. Exiting without starting containers.")
        return

    stop_existing_containers(args.profile)

    if not getattr(args, 'skip_neo4j', False):
        start_neo4j()
        wait_for_neo4j()
    else:
        print("Skipping Neo4j startup as requested")

    if not getattr(args, 'environment', None) or args.environment:
        start_supabase(args.environment)
        wait_for_supabase()

    start_local_ai(args.profile, args.environment)

    if getattr(args, 'start_nextjs', False):
        start_nextjs_dev()

if __name__ == "__main__":
    main()
